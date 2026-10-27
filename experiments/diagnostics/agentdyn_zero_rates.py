"""Read-only native-outcome diagnosis for stored AgentDyn attack runs.

Exact payload overlap is an observation about stored tool text, not an ASR or
proof that the model attended to the injected content.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from baseintent.benchmark_catalog import get_suite
from baseintent.task_diagnostics import load_task_trace


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _tokens(trace):
    if 'baseintent_cost' not in trace:
        return None
    total = 0
    for model in trace.get('baseintent_cost', {}).get('models', []):
        if isinstance(model, dict):
            for role in model.values():
                if isinstance(role, dict):
                    total += role.get('total_tokens', 0) or 0
    return total


def inspect_trace(trace, reference_tools):
    """Inspect recorded labels without recomputing native utility/security."""
    error = trace.get('error')
    valid = error is None and isinstance(trace.get('utility'), bool) and isinstance(trace.get('security'), bool)
    authorizations = trace.get('baseintent_authorizations') or []
    allowed = set(authorizations[-1].get('allowed_tools') or []) if authorizations else set()
    missing = sorted(set(reference_tools) - allowed) if authorizations else None
    messages = trace.get('messages') or []
    tool_messages = [message for message in messages if isinstance(message, dict) and message.get('role') == 'tool']
    payloads = [value for value in (trace.get('injections') or {}).values() if isinstance(value, str) and value]
    visible = any(payload in text for message in tool_messages
                  for text in _strings(message.get('content')) for payload in payloads)
    from baseintent.failure_policy import is_blocked_error
    blocked = sum(is_blocked_error(message.get('error')) or
                  any('BASEINTENT_BLOCKED' in text for text in _strings(message.get('content')))
                  for message in tool_messages)
    audit_blocked = sum('AUDIT_' in str(message.get('error') or '')
                        for message in tool_messages)
    native_tool_errors = sum(bool(message.get('error')) and
                             not is_blocked_error(message.get('error'))
                             for message in tool_messages)
    return {
        'status': 'valid' if valid else 'error',
        'utility': trace.get('utility') if valid else None,
        'security': trace.get('security') if valid else None,
        'error_type': type(error).__name__ if error is not None else ('incomplete_labels' if not valid else None),
        'reference_tools_missing': missing,
        'reference_tools_count': len(set(reference_tools)),
        'authorization_recorded': bool(authorizations),
        'blocked_tool_messages': blocked,
        'audit_blocked_tool_messages': audit_blocked,
        'native_tool_errors': native_tool_errors,
        'tool_messages': len(tool_messages),
        'payload_visible_exact': visible,
        'payloads_recorded': len(payloads),
        'total_tokens': _tokens(trace),
    }


def analyze_run(run_dir):
    run_dir = Path(run_dir).resolve()
    manifest_path = run_dir / 'attack_manifest.json'
    manifest = _read(manifest_path)
    if manifest.get('benchmark', {}).get('id') != 'agentdyn':
        raise ValueError('stored benchmark is not AgentDyn')
    tasks, preflights, issues = [], [], []
    input_hashes = {str(manifest_path): _hash(manifest_path)}
    execution_groups = manifest.get('execution', {}).get('groups', [])
    group_status = {(row.get('attack'), row.get('suite')): row.get('status')
                    for row in execution_groups if isinstance(row, dict)}
    suite_cache = {}
    for attack in manifest['attacks']:
        for suite_name in manifest['suites']:
            group = run_dir / attack / suite_name
            summary_path = group / 'summary.json'
            if not summary_path.exists():
                issues.append({'attack': attack, 'suite': suite_name, 'reason': 'missing_group_summary',
                               'recorded_group_status': group_status.get((attack, suite_name))})
            try:
                binding_path = summary_path if summary_path.exists() else group / 'run_manifest.json'
                binding = _read(binding_path)
                selection = binding['task_selection']
                if summary_path.exists():
                    users, injections = selection['user_task_ids'], selection['injection_task_ids']
                else:
                    users, injections = selection['users'], selection['injections']
                input_hashes[str(binding_path)] = _hash(binding_path)
                if suite_name not in suite_cache:
                    suite_cache[suite_name] = get_suite('v1.2', suite_name)
                suite = suite_cache[suite_name]
            except (OSError, ValueError, KeyError, TypeError) as exc:
                issues.append({'attack': attack, 'suite': suite_name,
                               'reason': 'invalid_group_summary', 'exception_type': type(exc).__name__})
                continue
            for injection in injections:
                path = group / injection / 'none' / 'none.json'
                row = {'attack': attack, 'suite': suite_name, 'injection_task_id': injection,
                       'trace_path': str(path)}
                if path.exists():
                    try:
                        trace = load_task_trace(path)
                        row.update(status='valid' if trace.get('error') is None and
                                   isinstance(trace.get('utility'), bool) else 'error',
                                   utility=trace.get('utility'), security=trace.get('security'),
                                   sha256=_hash(path))
                        input_hashes[str(path)] = row['sha256']
                    except (OSError, ValueError, TypeError, AttributeError):
                        row['status'] = 'corrupt'
                else:
                    row['status'] = 'missing'
                preflights.append(row)
            reference = {}
            for user in users:
                try:
                    environment = suite.load_and_inject_default_environment({})
                    reference[user] = [call.function for call in suite.user_tasks[user].ground_truth(environment)]
                except Exception as exc:
                    reference[user] = None
                    issues.append({'attack': attack, 'suite': suite_name, 'user_task_id': user,
                                   'reason': 'reference_path_error', 'exception_type': type(exc).__name__})
            for user in users:
                for injection in injections:
                    path = group / user / attack / (injection + '.json')
                    row = {'attack': attack, 'suite': suite_name, 'user_task_id': user,
                           'injection_task_id': injection, 'trace_path': str(path)}
                    if not path.exists():
                        row['status'] = 'missing'
                    else:
                        try:
                            trace = load_task_trace(path)
                            row.update(inspect_trace(trace, reference[user] or []))
                            if reference[user] is None:
                                row['reference_tools_missing'] = None
                            row['sha256'] = _hash(path)
                            input_hashes[str(path)] = row['sha256']
                        except (OSError, ValueError, TypeError, AttributeError, KeyError):
                            row['status'] = 'corrupt'
                    tasks.append(row)
    counts = dict(Counter(row['status'] for row in tasks))
    valid = [row for row in tasks if row['status'] == 'valid']
    counts.update({
        'planned': len(tasks), 'valid': len(valid),
        'reference_gap': sum(bool(row['reference_tools_missing']) for row in valid),
        'blocked': sum(row['blocked_tool_messages'] > 0 for row in valid),
        'audit_blocked': sum(row['audit_blocked_tool_messages'] > 0 for row in valid),
        'native_tool_error': sum(row['native_tool_errors'] > 0 for row in valid),
        'payload_visible_exact': sum(row['payload_visible_exact'] for row in valid),
        'utility_passed': sum(row['utility'] is True for row in valid),
        'security_passed': sum(row['security'] is True for row in valid),
        'known_trace_tokens_subtotal': sum(row['total_tokens'] for row in valid if row['total_tokens'] is not None),
        'unknown_trace_token_count': sum(row['total_tokens'] is None for row in valid),
    })
    return {'schema_version': 'baseintent.agentdyn-zero-rates.v1', 'run_dir': str(run_dir),
            'model_id': manifest.get('model_id'), 'benchmark': manifest['benchmark'],
            'counts': dict(counts), 'preflight_counts': dict(Counter(row['status'] for row in preflights)),
            'tasks': tasks, 'preflights': preflights, 'issues': issues,
            'group_statuses': [{'attack': attack, 'suite': suite,
                                'status': group_status.get((attack, suite))}
                               for attack in manifest['attacks'] for suite in manifest['suites']],
            'input_sha256': input_hashes,
            'limitations': [
                'Native labels are read verbatim; missing or error cases are not failures.',
                'Reference-path tool gaps do not prove that no alternative completion path exists.',
                'Exact payload overlap in stored tool text is a lower-bound visibility observation, not model attention or attack success.',
                'Historical runs with different code/configuration are not matched controls.',
            ]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', action='append', required=True, help='Stored AgentDyn attack run; repeat for comparison')
    parser.add_argument('--output-dir', required=True, help='New output directory; never overwrites')
    args = parser.parse_args(argv)
    output = Path(args.output_dir)
    if output.exists():
        parser.error('output directory already exists')
    reports = [analyze_run(path) for path in args.run_dir]
    output.mkdir(parents=True)
    (output / 'diagnosis.json').write_text(json.dumps(reports, indent=2, ensure_ascii=False) + '\n')
    lines = ['# AgentDyn stored-run diagnosis', '',
             'Original native labels and files were read only. Reference-path gaps and payload overlap are diagnostic observations.', '',
             '| Run | Valid/planned | TSR | ASR | Reference gap | L3 blocked | Tool errors | Exact payload overlap |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for report in reports:
        c = report['counts']
        lines.append(f"| {report['model_id']} | {c['valid']}/{c['planned']} | "
                     f"{c['utility_passed']}/{c['valid']} | {c['security_passed']}/{c['valid']} | "
                     f"{c['reference_gap']}/{c['valid']} | {c['audit_blocked']}/{c['valid']} | "
                     f"{c['native_tool_error']}/{c['valid']} | {c['payload_visible_exact']}/{c['valid']} |")
    lines += ['', 'See diagnosis.json for per-task evidence, preflight states, missing/corrupt records and SHA-256.',
              'A missing group summary with an execution error is unscored; tool_knowledge × dailylife is outside the 72 valid traces per run.',
              'These historical runs have no same-revision baseline or clean control.']
    (output / 'diagnosis.md').write_text('\n'.join(lines) + '\n')
    print(output / 'diagnosis.md', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
