"""Shared frozen-cohort evidence and measurement; no independent model loop."""
import fcntl
import hashlib
import inspect
import json
import os
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from agentdojo.attacks.attack_registry import ATTACKS
from agentdojo.task_suite import get_suite
from dscg.model_config import resolve_model_config
from dscg.paths import BENCHMARK_RESULTS_DIR, RESULTS_DIR
from experiments import run_partial_benchmark as shared
from experiments.partial_controls import source_revision, guard_run, validate_controls, select_tasks

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
            'screening_script_sha256': _file_hash(Path(__file__).with_name('run_injection_precheck.py')),
            'catalog': _catalog(names)}


def _legacy_mapping():
    """An explicit, byte-bound equivalent transition, not a source-hash bypass."""
    mapping = _read(Path(__file__).with_name('injection_cohort_compatibility.json'))
    if mapping.get('schema_version') != 'dscg.injection-compatibility.v1':
        raise ValueError('unknown compatibility mapping')
    root = Path(__file__).resolve().parents[1]
    return mapping if all(_file_hash(root / p) == h for p, h in mapping['current_harness_sha256'].items()) else None


def _source_compatible(recorded, current, *, check_python=True):
    if recorded.get('agentdojo') != current.get('agentdojo'):
        return False
    if check_python and recorded.get('python') != current.get('python'):
        return False
    old_hashes, new_hashes = recorded.get('source_sha256'), current.get('source_sha256')
    if old_hashes == new_hashes and old_hashes:
        return True  # A Git commit change alone is provenance, not behavior.
    mapping = _legacy_mapping()
    if not mapping or old_hashes not in [mapping['legacy_source']['source_sha256'],
                                        *mapping.get('equivalent_source_sha256', [])]:
        return False
    if set(new_hashes) != set(mapping['current_source_paths']):
        return False
    changed_paths = set(mapping['current_harness_sha256']) | {'experiments/injection_cohort_compatibility.json'}
    return all(new_hashes.get(p) == h for p, h in old_hashes.items() if p not in changed_paths)


def _bindings_compatible(recorded, current):
    keys = set(recorded) | set(current)
    if any(recorded.get(k) != current.get(k) for k in keys - {'source', 'screening_script_sha256'}):
        return False
    if not _source_compatible(recorded.get('source', {}), current['source']):
        return False
    if recorded.get('screening_script_sha256') == current['screening_script_sha256']:
        return True
    mapping = _legacy_mapping()
    return bool(mapping and recorded.get('screening_script_sha256') == mapping['legacy_screening_script_sha256']
                and recorded.get('source', {}).get('source_sha256') == mapping['legacy_source']['source_sha256'])


def _record_compatibility(root, recorded, current):
    if recorded == current:
        return
    record = {'reason': 'verified byte-bound harness transition or identical-source revision',
              'original_binding': recorded, 'current_binding': current}
    path = root / 'compatibility' / (_digest(current) + '.json')
    if path.exists():
        if _read(path) != record:
            raise ValueError('compatibility provenance changed')
    else:
        _write_new(path, record)


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


def _validate_cohort(path, config):
    return _validate_cohort_data(_read(path), config)


def _validate_cohort_data(cohort, config):
    content = {k: v for k, v in cohort.items() if k != 'cohort_sha256'}
    if (cohort.get('schema_version') != SCHEMA or cohort.get('cohort_sha256') != _digest(content)
            or cohort.get('selection_rule') != RULE):
        raise ValueError('invalid or changed frozen cohort')
    binding = cohort['binding']
    current = _binding(config, list(binding['catalog']))
    if not _bindings_compatible(binding, current):
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


def _preflight_report(base, cohort, active, attacks, selected_tasks=None):
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
            for task_id in (selected_tasks if selected_tasks is not None else cohort['suites'])[name]['injection_task_ids']:
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


def run_screened(cohort_path, *, config_path=None, run_name=None, results_dir=None, origin=False,
                 attack='typical', audit_router_mode='off', trace_level='summary', audit_router_artifact=None,
                 force_rerun=False, model_id=None, sec_model_id=None, defense=None, suites=None,
                 task_scope='screened', **controls):
    if task_scope not in {'screened', 'partial_screened'}:
        raise ValueError('unknown screened task scope')
    partial = task_scope == 'partial_screened'
    if not run_name:
        raise ValueError('screened measurements require a new --name')
    config = resolve_model_config(model_id, config_path=config_path,
        **{k: controls.pop(k) for k in ('api_key', 'base_url', 'provider', 'api_key_env') if k in controls})
    cohort_path = Path(cohort_path).resolve()
    cohort = _validate_cohort(cohort_path, config)
    names = shared.resolve_attack_names(attack)
    if any(ATTACKS[name].is_dos_attack for name in names):
        raise ValueError('DoS is not supported by injection-goal screening; select targeted attacks')
    use_checker = controls.get('use_security_checker', True)
    use_sandbox = controls.get('use_sandbox', True)
    shared._validate_router_controls(origin, use_checker, audit_router_mode, use_sandbox)
    validate_controls(origin=origin, use_security_checker=use_checker,
                      audit_retries=controls.get('audit_retries', 0), completion_prompt=controls.get('completion_prompt', False))
    security_model = None
    if not origin and use_checker:
        security_model = resolve_model_config(sec_model_id, config_path=config_path, prefix='DSCG_SEC', fallback=config,
            **{k: controls['sec_' + k] for k in ('api_key', 'base_url', 'provider', 'api_key_env') if 'sec_' + k in controls}).public_dict()
    requested = list(suites) if suites is not None else list(cohort['suites'])
    if not requested or len(set(requested)) != len(requested) or (partial and not set(requested) <= set(cohort['suites'])):
        raise ValueError('frozen cohort lacks requested suites or selection is empty/duplicated')
    selected = {}
    for name, entry in cohort['suites'].items():
        if partial and name not in requested:
            continue
        if partial and entry['injection_task_ids']:
            catalog = cohort['binding']['catalog'][name]
            users, injections = select_tasks(cohort, name, catalog['user_task_ids'],
                list(catalog['injection_tasks']), True, False, task_scope=task_scope)
            selected[name] = {'user_task_ids': users, 'injection_task_ids': injections}
        else:
            selected[name] = {'user_task_ids': entry['user_task_ids'][:3] if partial else entry['user_task_ids'],
                              'injection_task_ids': entry['injection_task_ids']}
    active = [name for name, entry in selected.items() if entry['injection_task_ids']]
    if not active:
        raise ValueError('no injection targets remain in the requested task scope; benchmark not started')
    if not partial and suites is not None and not set(active).issubset(set(suites)):
        raise ValueError('suite selection cannot omit active suites in the frozen cohort; no measurement started')
    root = Path(results_dir or (RESULTS_DIR / 'partial_benchmark' if partial else BENCHMARK_RESULTS_DIR))
    base = root / (shared._safe_result_component(config.model_id, 'model') + '_' + shared._safe_result_component(run_name, 'run'))
    with _lock(base):
        effective = {k: controls.get(k, default) for k, default in {
            'use_sandbox': True, 'use_security_checker': True, 'planning_tool_view': True,
            'delegated_tasks': True, 'l1_projection_mode': 'projected', 'audit_retries': 0,
            'completion_prompt': False}.items()}
        identity = {'task_scope': task_scope, 'requested_suites': requested, 'selected_tasks': selected,
                    'cohort_sha256': cohort['cohort_sha256'], 'main_model': config.public_dict(), 'security_model': security_model,
                    'baseline': origin, 'attacks': names, 'audit_router_mode': audit_router_mode,
                    'trace_level': trace_level, 'controls': effective, 'defense': defense,
                    'tool_metadata_sha256': _file_hash(controls['tool_metadata_path']) if controls.get('tool_metadata_path') else None,
                    'audit_router_artifact_sha256': _file_hash(audit_router_artifact) if audit_router_artifact else None,
                    'source': source_revision(), 'screening_script_sha256': _file_hash(__file__)}
        # Refuse to relabel existing ordinary runs as screened cohorts.
        if not (base / 'screened_run_manifest.json').exists() and any(base.glob('*/*/run_manifest.json')):
            raise ValueError('existing non-screened run; use a new --name')
        guard_run(base / 'screened_run_manifest.json', identity)
        _record_compatibility(base, cohort['binding'], _binding(config, list(cohort['binding']['catalog'])))
        attachment = {'scope': 'capability-conditioned screened subset', 'task_scope': task_scope,
                      'cohort_path': str(cohort_path), 'cohort': cohort,
                      'selected_tasks': selected, 'requested_suites': requested,
                      'omitted_suites': [name for name in cohort['suites'] if name not in requested],
                      'skipped_suites': [name for name in selected if name not in active],
                      'counts': {name: {'original_targets': len(cohort['binding']['catalog'][name]['injection_tasks']),
                          'retained_targets': len(cohort['suites'][name]['injection_task_ids']),
                          'prefix_targets': min(3, len(cohort['binding']['catalog'][name]['injection_tasks'])) if partial else len(cohort['binding']['catalog'][name]['injection_tasks']),
                          'selected_targets': len(entry['injection_task_ids']), 'user_tasks': len(entry['user_task_ids']),
                          'planned_per_targeted_attack': len(entry['user_task_ids']) * len(entry['injection_task_ids'])}
                          for name, entry in selected.items()},
                      'cost_scope': 'native per-attack preflight retained; not scored attack samples; screening cost separate'}
        attachment_path = base / 'screened_cohort.json'
        if not attachment_path.exists():
            _write_new(attachment_path, attachment)
        for name in attachment['skipped_suites']:
            print(f'{name}: {"原前3个注入目标中" if partial else ""}无通过目标，明确跳过。')
        try:
            return shared.main(model_id=config.model_id, sec_model_id=sec_model_id, defense=defense,
                               provider=config.provider, base_url=config.base_url,
                               api_key_env=config.api_key_env, api_key=config.api_key, config_path=config_path,
                               suites=active, origin=origin, run_name=run_name, results_dir=root,
                               task_manifest_path=cohort_path, task_scope=task_scope, attack=names,
                               cohort_sha256=cohort['cohort_sha256'],
                               audit_router_mode=audit_router_mode, trace_level=trace_level,
                               audit_router_artifact=audit_router_artifact, force_rerun=force_rerun, **controls)
        finally:
            _preflight_report(base, cohort, active, names, selected)
