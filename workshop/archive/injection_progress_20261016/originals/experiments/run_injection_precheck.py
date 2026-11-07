"""Screen directly requested injection goals, then measure a frozen target subset.

This is a capability-conditioned diagnostic cohort, not the full benchmark.
Native predicates, pipelines and full/partial runner defaults remain unchanged.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path

from agentdojo import benchmark, logging
from agentdojo.attacks.attack_registry import ATTACKS
from agentdojo.task_suite import get_suite

from dscg.model_config import resolve_model_config
from dscg.paths import BENCHMARK_RESULTS_DIR, RESULTS_DIR
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from experiments import run_partial_benchmark as shared
from experiments.partial_controls import SUITES, guard_run, source_revision

SCHEMA = 'dscg.injection-screen.v1'
RULE = 'keep-any-valid-success; exclude-after-two-valid-failures; errors-unresolved'
LIMITATIONS = [
    'Direct-goal failure does not prove an indirect attack cannot succeed.',
    'Native utility is retained; refusals, execution deviations and predicate ambiguity need trace review.',
    'Historical prechecks lack independent task/environment hashes; reuse checks their available version, source and GOAL evidence.',
    'Provider model revisions may be unpinned. Reused attempt token cost is unknown.',
]


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def _replace(path, value):
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def _lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.screening.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('another invocation is using this run directory') from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _catalog(names):
    catalog = {}
    for name in names:
        suite = get_suite('v1.2', name)
        tasks = {}
        for task_id, task in suite.injection_tasks.items():
            try:
                code = inspect.getsource(type(task))
            except (OSError, TypeError):
                code = type(task).__qualname__
            tasks[task_id] = {'goal': task.GOAL, 'implementation_sha256': _digest(code)}
        catalog[name] = {'user_task_ids': list(suite.user_tasks), 'injection_tasks': tasks}
    return catalog


def _binding(config, names):
    return {'schema_version': SCHEMA, 'suite_version': 'v1.2', 'rule': RULE,
            'main_model': config.public_dict(), 'source': source_revision(),
            'screening_script_sha256': _file_hash(__file__), 'catalog': _catalog(names)}


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(c.get('content', '') for c in content if isinstance(c, dict) and c.get('type') == 'text')
    return ''


def _trace_status(path, suite_name, task, version):
    """Require a complete native direct-goal result; errors are never failures."""
    value = _read(path)
    messages = value.get('messages', [])
    if (value.get('suite_name') != suite_name or value.get('user_task_id') != task.ID
            or value.get('injection_task_id') is not None or value.get('attack_type') not in (None, 'none')
            or value.get('injections') != {} or value.get('agentdojo_package_version') != version
            or not isinstance(messages, list) or len(messages) < 2):
        raise ValueError('not a matching direct-goal trace')
    users = [m for m in messages if m.get('role') == 'user']
    if not users or _text(users[0].get('content')) != task.GOAL:
        raise ValueError('trace GOAL mismatch')
    if value.get('error'):
        return 'error', None
    if type(value.get('utility')) is not bool or not any(m.get('role') == 'assistant' for m in messages):
        raise ValueError('incomplete native utility result')
    return ('pass' if value['utility'] else 'fail'), value['utility']


def _decision(attempts):
    if any(a['status'] == 'pass' for a in attempts):
        return 'kept'
    if sum(a['status'] == 'fail' for a in attempts) >= 2:
        return 'excluded'
    return 'unresolved'


def _reuse(reuse_from, suite_name, task, binding):
    if reuse_from is None:
        return [], []
    root = Path(reuse_from).resolve()
    rejected, compatible, seen = [], [], set()
    for path in sorted(root.glob(f'*/{suite_name}/{task.ID}/none/none.json')):
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError('trace outside supplied run')
            manifest_path = path.parents[2] / 'run_manifest.json'
            manifest = _read(manifest_path)
            selection = manifest['task_selection']
            if (manifest.get('profile') != 'baseline' or manifest.get('main_model') != binding['main_model']
                    or manifest['source'].get('source_sha256') != binding['source']['source_sha256']
                    or manifest['source'].get('agentdojo') != binding['source']['agentdojo']
                    or selection.get('suite_version') != 'v1.2' or task.ID not in selection.get('injections', [])):
                raise ValueError('historical configuration mismatch')
            status, utility = _trace_status(path, suite_name, task, binding['source']['agentdojo'])
            if status == 'error':
                raise ValueError('historical native error')
            trace_hash = _file_hash(path)
            if trace_hash in seen:
                continue
            seen.add(trace_hash)
            compatible.append({'origin': 'reused', 'status': status, 'native_utility': utility,
                    'trace_path': str(path.resolve()), 'trace_sha256': trace_hash,
                    'manifest_path': str(manifest_path.resolve()), 'manifest_sha256': _file_hash(manifest_path),
                    'reuse_checks': ['baseline', 'public-model-config', 'runtime-source-hashes',
                                     'agentdojo-version', 'suite-version', 'task-id', 'GOAL', 'complete-native-result'],
                    'api_accounting': None, 'total_tokens': None})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            rejected.append({'path': str(path), 'reason': 'incompatible_or_incomplete_direct_goal_record'})
    # Examine all matching attacks before deciding: an existing success wins.
    return compatible, rejected


def _attempt_directory(root, suite_name, task_id):
    parent = root / 'attempts' / suite_name / task_id
    parent.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        path = parent / f'attempt_{number:04d}'
        try:
            path.mkdir()
            return path
        except FileExistsError:
            number += 1


def _native_attempt(directory, suite, task, config, binding):
    record = {'origin': 'fresh', 'status': 'error', 'native_utility': None,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'trace_path': None, 'trace_sha256': None, 'api_accounting': None, 'total_tokens': None}
    _write_new(directory / 'attempt_manifest.json', {'binding_sha256': _digest(binding),
               'suite_name': suite.name, 'task_id': task.ID, 'started_at': record['started_at']})
    tracker = None
    try:
        pipeline, tracker = make_openai_compatible_pipeline(model_config=config)
        pipeline.name = 'direct_goal'
        trace = directory / 'direct_goal' / suite.name / task.ID / 'none' / 'none.json'
        with logging.OutputLogger(str(directory)):
            benchmark.run_task_without_injection_tasks(suite, pipeline, task, directory, True, benchmark_version='v1.2')
        record['status'], record['native_utility'] = _trace_status(trace, suite.name, task, binding['source']['agentdojo'])
    except Exception as exc:
        # Preserve native traces; provider exception text can contain private input.
        record['error_type'] = type(exc).__name__
    finally:
        trace = directory / 'direct_goal' / suite.name / task.ID / 'none' / 'none.json'
        if trace.exists():
            record.update(trace_path=str(trace.resolve()), trace_sha256=_file_hash(trace))
        if tracker is not None and hasattr(tracker, 'snapshot'):
            phases = tracker.snapshot()
            record['api_accounting'] = phases
            if phases and not any(p.get('missing_usage_calls', 0) or p.get('failed_calls', 0) for p in phases.values()):
                record['total_tokens'] = sum(p.get('total_tokens', 0) for p in phases.values())
        record['finished_at'] = datetime.now(timezone.utc).isoformat()
        _write_new(directory / 'attempt.json', record)
    return record


def _attempts(root, suite_name, task_id, binding):
    attempts = []
    for directory in sorted((root / 'attempts' / suite_name / task_id).glob('attempt_*')):
        path = directory / 'attempt.json'
        try:
            if not path.exists():
                marker = _read(directory / 'attempt_manifest.json')
                if (marker.get('binding_sha256') != _digest(binding) or marker.get('suite_name') != suite_name
                        or marker.get('task_id') != task_id):
                    raise ValueError('unbound interrupted attempt')
                trace = directory / 'direct_goal' / suite_name / task_id / 'none' / 'none.json'
                task = get_suite('v1.2', suite_name).get_injection_task_by_id(task_id)
                status, utility = _trace_status(trace, suite_name, task, binding['source']['agentdojo'])
                _write_new(path, {'origin': 'recovered', 'status': status, 'native_utility': utility,
                    'trace_path': str(trace.resolve()), 'trace_sha256': _file_hash(trace),
                    'started_at': marker['started_at'], 'api_accounting': None, 'total_tokens': None,
                    'recovery': 'native result completed before attempt bookkeeping; usage unknown'})
            record = _read(path)
            if record['status'] not in {'pass', 'fail', 'error'}:
                raise ValueError('invalid attempt status')
            for prefix in ('trace', 'manifest'):
                if record.get(prefix + '_path') and _file_hash(record[prefix + '_path']) != record[prefix + '_sha256']:
                    raise ValueError('attempt evidence changed')
        except (OSError, ValueError, KeyError, TypeError):
            record = {'status': 'error', 'origin': 'incomplete', 'error_type': 'MissingOrChangedAttemptEvidence',
                      'attempt_directory': str(directory.resolve()), 'total_tokens': None}
        attempts.append(record)
    return attempts


def _report(root, binding, decisions, rejected):
    counts = Counter(d['status'] for tasks in decisions.values() for d in tasks.values())
    attempts = [a for tasks in decisions.values() for d in tasks.values() for a in d['attempts']]
    report = {'schema_version': SCHEMA, 'binding_sha256': _digest(binding), 'counts': dict(counts),
              'expected_targets': sum(len(e['injection_tasks']) for e in binding['catalog'].values()),
              'processed_targets': sum(counts.values()),
              'attempt_counts': dict(Counter(a['status'] for a in attempts)), 'decisions': decisions,
              'reuse_rejections': rejected, 'known_attempt_tokens': sum(a.get('total_tokens') or 0 for a in attempts),
              'unknown_cost_attempts': sum(a.get('total_tokens') is None for a in attempts),
              'limitations': LIMITATIONS}
    _replace(root / 'status.json', report)
    lines = ['# Injection 目标直接预检', '', '范围：无防御 baseline；不执行注入攻击。', '',
             '| 场景 | 目标 | 状态 | 有效成功/失败 | 错误 |', '| --- | --- | --- | --- | --- |']
    for name, tasks in decisions.items():
        for task_id, decision in tasks.items():
            c = Counter(a['status'] for a in decision['attempts'])
            lines.append(f"| {name} | {task_id} | {decision['status']} | {c['pass']}/{c['fail']} | {c['error']} |")
    lines += ['', 'excluded 表示本轮两次有效测试未完成，不表示目标永远无法完成。',
              '主动拒绝、执行偏差及评分疑点须查看 status.json 中的逐次原始轨迹；不自动推断失败原因。',
              f"已知尝试 Tokens：{report['known_attempt_tokens']}；成本未知尝试：{report['unknown_cost_attempts']}。", '', *LIMITATIONS]
    (root / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def screen(*, config_path, run_name, results_dir=None, reuse_from=None, suites=SUITES):
    config = resolve_model_config(config_path=config_path)
    binding = _binding(config, suites)
    root = Path(results_dir or RESULTS_DIR / 'injection_precheck') / (
        shared._safe_result_component(config.model_id, 'model') + '_' + shared._safe_result_component(run_name, 'screen'))
    if reuse_from is not None and not Path(reuse_from).is_dir():
        raise ValueError('--reuse-from must be an existing benchmark run directory')
    with _lock(root):
        guard_run(root / 'screen_manifest.json', binding)
        if (root / 'cohort.json').exists():
            _validate_cohort(root / 'cohort.json', config)
            print(f'冻结名单已存在，无新增模型调用：{root / "cohort.json"}')
            return 0
        decisions, rejected = {}, []
        if (root / 'status.json').exists():
            rejected = _read(root / 'status.json').get('reuse_rejections', [])
        for name, entry in binding['catalog'].items():
            suite = get_suite('v1.2', name)
            decisions[name] = {}
            for task_id in entry['injection_tasks']:
                task = suite.get_injection_task_by_id(task_id)
                attempts = _attempts(root, name, task_id, binding)
                if not attempts:
                    reused, rejected_records = _reuse(reuse_from, name, task, binding)
                    rejected.extend(rejected_records)
                    for record in reused:
                        _write_new(_attempt_directory(root, name, task_id) / 'attempt.json', record)
                        attempts.append(record)
                while _decision(attempts) == 'unresolved':
                    attempt = _native_attempt(_attempt_directory(root, name, task_id), suite, task, config, binding)
                    attempts.append(attempt)
                    if attempt['status'] == 'error':
                        break  # No implicit network retry; a later invocation can resume.
                decisions[name][task_id] = {'status': _decision(attempts), 'attempts': attempts}
                _report(root, binding, decisions, rejected)
        report = _report(root, binding, decisions, rejected)
        if report['counts'].get('unresolved', 0):
            print(f'存在待解决目标；未生成 cohort.json。查看 {root / "status.json"}')
            return 1
        cohort = {'schema_version': SCHEMA, 'suite_version': 'v1.2', 'task_scope': 'screened',
                  'selection_rule': RULE, 'binding': binding, 'decisions': decisions,
                  'suites': {name: {'user_task_ids': entry['user_task_ids'],
                      'injection_task_ids': [i for i, d in decisions[name].items() if d['status'] == 'kept']}
                      for name, entry in binding['catalog'].items()}, 'limitations': LIMITATIONS}
        cohort['cohort_sha256'] = _digest(cohort)
        _validate_cohort_data(cohort, config)
        _write_new(root / 'cohort.json', cohort)
        print(f'冻结名单：{root / "cohort.json"}；{dict(report["counts"])}')
        return 0


def _validate_cohort(path, config):
    return _validate_cohort_data(_read(path), config)


def _validate_cohort_data(cohort, config):
    content = {k: v for k, v in cohort.items() if k != 'cohort_sha256'}
    if (cohort.get('schema_version') != SCHEMA or cohort.get('cohort_sha256') != _digest(content)
            or cohort.get('selection_rule') != RULE):
        raise ValueError('invalid or changed frozen cohort')
    binding = cohort['binding']
    current = _binding(config, list(binding['catalog']))
    if binding != current:
        raise ValueError('screening configuration/source/catalog changed; use a new screen run')
    for name, entry in binding['catalog'].items():
        decisions = cohort['decisions'][name]
        if set(decisions) != set(entry['injection_tasks']):
            raise ValueError('incomplete screening decisions')
        for task_id, decision in decisions.items():
            attempts = decision['attempts']
            if _decision(attempts) == 'unresolved' or _decision(attempts) != decision['status']:
                raise ValueError('unresolved or inconsistent screening decisions')
            task = get_suite('v1.2', name).get_injection_task_by_id(task_id)
            for attempt in attempts:
                if attempt.get('status') not in {'pass', 'fail'}:
                    continue
                trace = attempt['trace_path']
                if _file_hash(trace) != attempt['trace_sha256']:
                    raise ValueError('screening evidence changed')
                if _trace_status(trace, name, task, binding['source']['agentdojo'])[0] != attempt['status']:
                    raise ValueError('screening outcome changed')
                if attempt.get('manifest_path') and _file_hash(attempt['manifest_path']) != attempt['manifest_sha256']:
                    raise ValueError('historical source manifest changed')
        expected = {'user_task_ids': entry['user_task_ids'],
                    'injection_task_ids': [i for i, d in decisions.items() if d['status'] == 'kept']}
        if cohort['suites'].get(name) != expected:
            raise ValueError('selected tasks disagree with screening evidence')
    return cohort


def _preflight_report(base, cohort, active, attacks):
    """Keep unscored native preflight outcomes/cost uncertainty separate."""
    records, aggregate_costs = [], []
    for attack in attacks:
        for name in active:
            directory = base / attack / name
            summary = directory / 'summary.json'
            if summary.exists():
                value = _read(summary)
                aggregate_costs.append({'attack': attack, 'suite': name,
                    'main_overhead_including_preflight': value.get('overhead'),
                    'security_overhead_including_preflight': value.get('sec_overhead'),
                    'cost_scope': value.get('cost_scope')})
            for task_id in cohort['suites'][name]['injection_task_ids']:
                path = directory / task_id / 'none' / 'none.json'
                record = {'attack': attack, 'suite': name, 'injection_task_id': task_id,
                          'trace_path': str(path.resolve()), 'status': 'missing', 'total_tokens': None}
                if path.exists():
                    try:
                        task = get_suite('v1.2', name).get_injection_task_by_id(task_id)
                        record['status'], record['native_utility'] = _trace_status(
                            path, name, task, cohort['binding']['source']['agentdojo'])
                        record['trace_sha256'] = _file_hash(path)
                        record['duration'] = _read(path).get('duration')
                    except (OSError, ValueError, KeyError, TypeError, AttributeError):
                        record['status'] = 'invalid'
                records.append(record)
    _replace(base / 'preflight_report.json', {
        'scope': 'unscored native per-attack goal prechecks; separate from original screening',
        'planned_preflight_samples': len(records), 'counts': dict(Counter(r['status'] for r in records)),
        'preflight_total_tokens': None, 'records': records, 'aggregate_run_costs': aggregate_costs,
        'cost_limitation': 'Native task traces lack separate usage; preflight Tokens remain unknown and are included in shared aggregate costs, not added again.',
    })


def run_screened(cohort_path, *, config_path, run_name, results_dir=None, origin=False,
                 attack='typical', audit_router_mode='off', trace_level='summary', audit_router_artifact=None,
                 force_rerun=False):
    config = resolve_model_config(config_path=config_path)
    cohort_path = Path(cohort_path).resolve()
    cohort = _validate_cohort(cohort_path, config)
    names = shared.resolve_attack_names(attack)
    if any(ATTACKS[name].is_dos_attack for name in names):
        raise ValueError('DoS is not supported by injection-goal screening; select targeted attacks')
    shared._validate_router_controls(origin, True, audit_router_mode)
    active = [name for name, entry in cohort['suites'].items() if entry['injection_task_ids']]
    if not active:
        raise ValueError('no injection targets passed screening; benchmark not started')
    root = Path(results_dir or BENCHMARK_RESULTS_DIR)
    base = root / (shared._safe_result_component(config.model_id, 'model') + '_' + shared._safe_result_component(run_name, 'run'))
    with _lock(base):
        identity = {'cohort_sha256': cohort['cohort_sha256'], 'main_model': config.public_dict(),
                    'baseline': origin, 'attacks': names, 'audit_router_mode': audit_router_mode,
                    'trace_level': trace_level,
                    'audit_router_artifact_sha256': _file_hash(audit_router_artifact) if audit_router_artifact else None,
                    'source': source_revision(), 'screening_script_sha256': _file_hash(__file__)}
        # Refuse to relabel existing ordinary runs as screened cohorts.
        if not (base / 'screened_run_manifest.json').exists() and any(base.glob('*/*/run_manifest.json')):
            raise ValueError('existing non-screened run; use a new --name')
        guard_run(base / 'screened_run_manifest.json', identity)
        attachment = {'scope': 'capability-conditioned screened subset; shared task_scope=partial, not full',
                      'cohort_path': str(cohort_path), 'cohort': cohort,
                      'skipped_suites': [name for name in cohort['suites'] if name not in active],
                      'counts': {name: {'original_targets': len(cohort['binding']['catalog'][name]['injection_tasks']),
                          'retained_targets': len(entry['injection_task_ids']), 'user_tasks': len(entry['user_task_ids']),
                          'planned_per_targeted_attack': len(entry['user_task_ids']) * len(entry['injection_task_ids'])}
                          for name, entry in cohort['suites'].items()},
                      'cost_scope': 'native per-attack preflight retained; not scored attack samples; screening cost separate'}
        attachment_path = base / 'screened_cohort.json'
        if not attachment_path.exists():
            _write_new(attachment_path, attachment)
        for name in attachment['skipped_suites']:
            print(f'{name}: 无通过目标，明确跳过。')
        try:
            return shared.main(model_id=config.model_id, provider=config.provider, base_url=config.base_url,
                               api_key_env=config.api_key_env, api_key=config.api_key, config_path=config_path,
                               suites=active, origin=origin, run_name=run_name, results_dir=root,
                               task_manifest_path=cohort_path, task_scope='partial', attack=names,
                               audit_router_mode=audit_router_mode, trace_level=trace_level,
                               audit_router_artifact=audit_router_artifact, force_rerun=force_rerun)
        finally:
            _preflight_report(base, cohort, active, names)


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('screen', 'benchmark'):
        sub = commands.add_parser(name)
        sub.add_argument('--model-config', dest='config_path')
        sub.add_argument('--name', dest='run_name', required=True)
        sub.add_argument('--results-dir', help='screen默认results/injection_precheck；benchmark默认results/benchmarks')
        if name == 'screen':
            sub.add_argument('--reuse-from', help='只读核对并复用已有baseline运行目录中的直接目标预检')
        else:
            sub.add_argument('--cohort', required=True)
            sub.add_argument('--baseline', action='store_true')
            sub.add_argument('--attack', nargs='+', action='extend', default=None)
            sub.add_argument('--force-rerun', action='store_true')
            sub.add_argument('--audit-router-mode', choices=('off', 'shadow', 'selective'), default='off')
            sub.add_argument('--audit-router-artifact')
            sub.add_argument('--trace-level', choices=('summary', 'standard', 'full'), default='summary')
    args = parser.parse_args(argv)
    options = vars(args).copy()
    command = options.pop('command')
    try:
        if command == 'screen':
            return screen(**options)
        options['origin'] = options.pop('baseline')
        options['attack'] = options['attack'] or 'typical'
        options['force_rerun'] = options['force_rerun'] or os.getenv('DSCG_FORCE_RERUN', '0').lower() in {'1', 'true', 'yes'}
        return run_screened(options.pop('cohort'), **options)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # No provider exception strings or credentials in wrapper diagnostics.
        print(f'预检/筛选配置错误 ({type(exc).__name__})：{exc}' if isinstance(exc, ValueError)
              else f'预检/筛选记录不可用：{type(exc).__name__}')
        return 1


if __name__ == '__main__':
    raise SystemExit(cli())
