"""Standalone single-attempt baseline GOAL screening producing minimal fliter.json."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import time

from agentdojo import logging
from experiments.common import task_storage
from experiments.common.injection_filter import SCHEMA as FLITER_SCHEMA, benchmark_header, load_fliter
from dscg.benchmark_catalog import get_suite, benchmark_identity, get_backend, same_backend
from dscg.model_config import resolve_model_config
from dscg.paths import RESULTS_DIR
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from experiments.common.partial_controls import source_revision, guard_run
from experiments.common.result_paths import resolve_run_path
from experiments.common.run_bindings import load_run_bindings
from dscg.task_diagnostics import load_task_trace
from experiments.common.injection_cohort import (
    RULE, _digest, _file_hash, _read, _write_new, _replace,
    _lock, _binding, _trace_status, _decision,
    _bindings_compatible, _binding_error, _source_compatible,
)

SCREEN_SCHEMA = 'dscg.fliter-screen.v1'


class Progress:
    """Compact, flushed output; waiting notices do not touch model execution."""

    def __init__(self):
        self.started = time.monotonic()
        self._output_lock = threading.Lock()

    def emit(self, message):
        with self._output_lock:
            print(f'[预检 {time.monotonic() - self.started:.1f}s] {message}', flush=True)

    @contextmanager
    def waiting(self, label, interval=15):
        stopped = threading.Event()
        started = time.monotonic()
        def notices():
            while not stopped.wait(interval):
                self.emit(f'{label} 等待中，已执行 {time.monotonic() - started:.0f}s')
        worker = threading.Thread(target=notices, daemon=True, name='injection-precheck-progress')
        worker.start()
        try:
            yield
        finally:
            stopped.set()
            worker.join()

def _flat_reuse_binding(root, suite_name, task):
    manifest_path = root / 'run_manifest.json'
    screen_path = root / 'screen_manifest.json'
    if manifest_path.exists():
        manifest = _read(manifest_path)
    elif screen_path.exists():
        manifest_path = screen_path
        manifest = _read(manifest_path)
    else:
        raise ValueError('source run has no manifest')
    if manifest.get('schema_version') == SCREEN_SCHEMA:
        if manifest.get('profile', 'baseline') != 'baseline' or manifest.get('agentdojo_defense'):
            raise ValueError('source screen is not native baseline')
        catalog = manifest['catalog'][suite_name]['injection_tasks']
        if catalog[task.ID]['goal'] != task.GOAL:
            raise ValueError('source screen GOAL mismatch')
        return manifest_path, {**manifest, 'profile': 'baseline',
                             'task_selection': {'suite_version': manifest['suite_version'],
                                                'injections': list(catalog)}}
    manifest_path = root / 'run_manifest.json'
    groups = [value for key, value in load_run_bindings(root).items()
              if len(Path(key).parts) == 3 and Path(key).parts[1:] == (suite_name, 'run_manifest.json')]
    if not groups or any(group.get('profile') != 'baseline' or group.get('agentdojo_defense')
                         or group.get('selection_options', {}).get('goal') is not True for group in groups):
        raise ValueError('source GOAL was not measured with an unmodified native baseline')
    reference = {key: value for key, value in groups[0].items() if key != 'attack'}
    if any({key: value for key, value in group.items() if key != 'attack'} != reference
           for group in groups[1:]):
        raise ValueError('source GOAL has ambiguous group bindings')
    return manifest_path, groups[0]


def _reuse(reuse_from, suite_name, task, binding):
    if reuse_from is None:
        return [], []
    root = Path(reuse_from).resolve()
    rejected, compatible = [], []
    flat = root / 'goal' / suite_name / f'{task.ID}.json'
    candidates = ([flat] if flat.exists() else []) + sorted(root.glob(f'*/{suite_name}/{task.ID}/none/none.json'))
    for path in candidates:
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError('trace outside supplied run')
            if path == flat:
                manifest_path, manifest = _flat_reuse_binding(root, suite_name, task)
            else:
                manifest_path = path.parents[2] / 'run_manifest.json'
                manifest = _read(manifest_path)
            if not manifest_path.resolve().is_relative_to(root):
                raise ValueError('manifest outside supplied run')
            selection = manifest['task_selection']
            if (not same_backend(manifest.get('benchmark'), benchmark_identity()) or manifest.get('profile') != 'baseline'
                    or manifest.get('agentdojo_defense') or manifest.get('main_model') != binding['main_model']
                    or not _source_compatible(manifest['source'], binding['source'], check_python=False)
                    or selection.get('suite_version') != 'v1.2' or task.ID not in selection.get('injections', [])):
                raise ValueError('historical configuration mismatch')
            status, utility = _trace_status(path, suite_name, task, binding['source']['agentdojo'])
            projected = load_task_trace(path)
            if projected.get('dscg_infrastructure_failure') or ('dscg_diagnostics' in projected
                    and projected.get('dscg_diagnostics_status') != 'complete'):
                status, utility = 'error', None
            source_status = {}
            if path == flat and manifest.get('schema_version') == SCREEN_SCHEMA:
                source_attempts = sorted((root / 'attempts' / suite_name / task.ID).glob('attempt_*/attempt.json'))
                if source_attempts:
                    attempt_path = source_attempts[0]
                    attempt = _read(attempt_path)
                    if (Path(attempt.get('trace_path', '')).resolve() != path.resolve()
                            or attempt.get('trace_sha256') != _file_hash(path)):
                        raise ValueError('source screening attempt does not bind this trace')
                    if attempt.get('status') == 'error' or any(phase.get('failed_calls', 0) > 0
                            for phase in (attempt.get('api_accounting') or {}).values()):
                        status, utility = 'error', None
                    elif attempt.get('status') != status:
                        raise ValueError('source screening attempt status is inconsistent')
                    source_status = {'goal_status_path': str(attempt_path.resolve()),
                                     'goal_status_sha256': _file_hash(attempt_path)}
            summary_path = root / 'summary.json'
            if path == flat and summary_path.exists():
                records = _read(summary_path).get('selection_report', {}).get('goal_checks', [])
                matched = [record for record in records if record.get('suite') == suite_name
                           and record.get('injection_task_id') == task.ID]
                if len(matched) != 1 or matched[0].get('path') != f'goal/{suite_name}/{task.ID}.json':
                    raise ValueError('source GOAL summary does not bind this trace')
                if matched[0].get('status') in {'error', 'running'}:
                    status, utility = 'error', None
                elif matched[0].get('status') != {'pass': 'passed', 'fail': 'failed', 'error': 'error'}[status]:
                    raise ValueError('source GOAL summary is incomplete or inconsistent')
                source_status = {'goal_status_path': str(summary_path.resolve()),
                                 'goal_status_sha256': _file_hash(summary_path)}
            compatible.append({'origin': 'reused', 'status': status, 'native_utility': utility,
                    'trace_path': str(path.resolve()), 'trace_sha256': _file_hash(path),
                    'manifest_path': str(manifest_path.resolve()), 'manifest_sha256': _file_hash(manifest_path),
                    'reuse_checks': ['baseline', 'public-model-config', 'backend-metadata',
                                     'agentdojo-version', 'suite-version', 'task-id', 'GOAL', 'complete-native-result'],
                    'api_accounting': None, 'total_tokens': None, **source_status})
            break  # First compatible record only; do not search for a second-chance success.
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            rejected.append({'path': str(path), 'reason': 'incompatible_or_incomplete_direct_goal_record'})
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
    root = directory.parents[3]  # attempts/<suite>/<task>/attempt_0001
    record = {'origin': 'fresh', 'status': 'error', 'native_utility': None,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'trace_path': None, 'trace_sha256': None, 'api_accounting': None, 'total_tokens': None}
    _write_new(directory / 'attempt_manifest.json', {'benchmark': benchmark_identity(), 'binding_sha256': _digest(binding),
               'suite_name': suite.name, 'task_id': task.ID, 'started_at': record['started_at']})
    tracker = None
    try:
        pipeline, tracker = make_openai_compatible_pipeline(model_config=config)
        pipeline.name = 'goal'
        trace = root / 'goal' / suite.name / f'{task.ID}.json'
        with logging.OutputLogger(str(root)):
            task_storage.run_task_without_injection_tasks(suite, pipeline, task, root, True, benchmark_version='v1.2', goal=True)
        record['status'], record['native_utility'] = _trace_status(trace, suite.name, task, binding['source']['agentdojo'])
    except Exception as exc:
        # Preserve native traces; provider exception text can contain private input.
        record['error_type'] = type(exc).__name__
        from dscg.request_compatibility import api_error_diagnostics
        diagnostic = api_error_diagnostics(exc)
        if diagnostic is not None:
            record['api_error'] = diagnostic
    finally:
        trace = root / 'goal' / suite.name / f'{task.ID}.json'
        if trace.exists():
            record.update(trace_path=str(trace.resolve()), trace_sha256=_file_hash(trace))
        if tracker is not None and hasattr(tracker, 'snapshot'):
            phases = tracker.snapshot()
            record['api_accounting'] = phases
            if any(p.get('failed_calls', 0) > 0 for p in phases.values()):
                record.update(status='error', native_utility=None, error_type='RecordedApiFailure',
                              error_code='RECORDED_API_FAILURE')
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
                trace = root / 'goal' / suite_name / f'{task_id}.json'
                task = get_suite('v1.2', suite_name).get_injection_task_by_id(task_id)
                status, utility = _trace_status(trace, suite_name, task, binding['source']['agentdojo'])
                _write_new(path, {'origin': 'recovered', 'status': status, 'native_utility': utility,
                    'trace_path': str(trace.resolve()), 'trace_sha256': _file_hash(trace),
                    'started_at': marker['started_at'], 'api_accounting': None, 'total_tokens': None,
                    'recovery': 'native result completed before attempt bookkeeping; usage unknown'})
            record = _read(path)
            if record['status'] not in {'pass', 'fail', 'error'}:
                raise ValueError('invalid attempt status')
            for prefix in ('trace', 'manifest', 'goal_status'):
                if record.get(prefix + '_path') and _file_hash(record[prefix + '_path']) != record[prefix + '_sha256']:
                    raise ValueError('attempt evidence changed')
        except (OSError, ValueError, KeyError, TypeError) as exc:
            if isinstance(exc, ValueError) and str(exc) == 'attempt evidence changed':
                raise
            record = {'status': 'error', 'origin': 'incomplete', 'error_type': 'MissingOrChangedAttemptEvidence',
                      'attempt_directory': str(directory.resolve()), 'total_tokens': None}
        attempts.append(record)
    return attempts


def _report(root, binding, decisions, rejected):
    counts = Counter(d['status'] for tasks in decisions.values() for d in tasks.values())
    attempts = [a for tasks in decisions.values() for d in tasks.values() for a in d['attempts']]
    report = {'schema_version': SCREEN_SCHEMA, 'binding_sha256': _digest(binding), 'counts': dict(counts),
              'expected_targets': sum(len(e['injection_tasks']) for e in binding['catalog'].values()),
              'processed_targets': sum(counts.values()),
              'selection_rule': RULE, 'attempt_counts': dict(Counter(a['status'] for a in attempts)),
              'reuse_rejection_counts': dict(rejected), 'known_attempt_tokens': sum(a.get('total_tokens') or 0 for a in attempts),
              'unknown_cost_attempts': sum(a.get('total_tokens') is None for a in attempts)}
    checks = []
    for name, tasks in decisions.items():
        for task_id, decision in tasks.items():
            attempt = decision['attempts'][0]
            accounting = attempt.get('api_accounting')
            check = dict(suite=name, injection_task_id=task_id,
                         status={'kept': 'passed', 'excluded': 'failed', 'error': 'error'}[decision['status']],
                         path=f'goal/{name}/{task_id}.json',
                         cost={'models': [accounting]} if accounting else None)
            if attempt.get('error_code'):
                check['error_code'] = attempt['error_code']
            checks.append(check)
    report['selection_report'] = {'goal_checks': checks}
    _replace(root / 'summary.json', report)
    lines = ['# Injection 目标直接预检', '', '范围：无防御 baseline；不执行注入攻击。', '',
             '每目标一次，成功保留，失败或错误跳过；错误不计作有效失败。', '',
             '| 场景 | 已处理/目标 | 保留 | 排除 | 错误跳过 |', '| --- | --- | --- | --- | --- |']
    for name, tasks in decisions.items():
        c = Counter(d['status'] for d in tasks.values())
        lines.append(f"| {name} | {len(tasks)}/{len(binding['catalog'][name]['injection_tasks'])} | {c['kept']} | {c['excluded']} | {c['error']} |")
    lines += ['', f"已知尝试 Tokens：{report['known_attempt_tokens']}；成本未知尝试：{report['unknown_cost_attempts']}。", '',
              '详情见[排除名单](fliter.json)与[原始尝试](attempts/)。直接失败不证明间接攻击不能成功。']
    lines += ['', '| 场景 | 排除目标 | 原因 |', '| --- | --- | --- |']
    for name, tasks in decisions.items():
        for task_id, decision in tasks.items():
            if decision['status'] != 'kept':
                lines.append(f"| {name} | {task_id} | {'有效失败' if decision['status'] == 'excluded' else '错误跳过（不计有效失败）'} |")
    (root / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def screen(*, config_path, run_name, results_dir=None, reuse_from=None, suites=None):
    backend = get_backend()
    suites = list(backend.suites) if suites is None else list(suites)
    if not suites or len(set(suites)) != len(suites) or not set(suites) <= set(backend.suites):
        raise ValueError(f'suites must select from {", ".join(backend.suites)}')
    progress = Progress()
    progress.emit('启动，正在读取配置与任务目录。')
    config = resolve_model_config(config_path=config_path)
    if config.model_id != 'qwen3.7-flash' or config.provider != 'dashscope':
        raise ValueError('Online screening requires qwen3.7-flash via dashscope; no fallback is allowed')
    current_binding = {**_binding(config, suites), 'schema_version': SCREEN_SCHEMA}
    root = resolve_run_path(results_dir or RESULTS_DIR / 'injection_precheck', backend.id,
                            config.model_id, run_name, allow_legacy=True)
    if root.exists() and (any((root / name).exists() for name in ('cohort.json', 'screen_manifest.json', 'status.json'))
                          or not (root / 'run_manifest.json').is_file()):
        raise ValueError('existing screen directory lacks a complete binding; use a new screen name')
    if reuse_from is not None and not Path(reuse_from).is_dir():
        raise ValueError('--reuse-from must be an existing benchmark run directory')
    with _lock(root):
        manifest_path = root / 'run_manifest.json'
        resumed = manifest_path.exists()
        binding = _read(manifest_path) if resumed else current_binding
        compatible = (binding.get('schema_version') == current_binding['schema_version']
                      and _bindings_compatible(binding, current_binding))
        if not compatible:
            raise ValueError(_binding_error(binding, current_binding))
        guard_run(manifest_path, binding)
        total = sum(len(e['injection_tasks']) for e in binding['catalog'].values())
        progress.emit(f'模型={config.model_id}；目标={total}；模式={"续跑" if resumed else "首次运行"}；输出={root}')
        progress.emit(f'复用来源={reuse_from or "未指定"}；每目标只测一次：成功保留，失败/错误跳过。')
        prior_attempts = {(name, task_id): _attempts(root, name, task_id, binding)
                          for name, entry in binding['catalog'].items() for task_id in entry['injection_tasks']}
        decisions, rejected = {}, Counter()
        ordinal = 0
        if (root / 'summary.json').exists():
            previous = _read(root / 'summary.json')
            rejected.update(previous.get('reuse_rejection_counts', {}))
            rejected.update(r['reason'] for r in previous.get('reuse_rejections', []))
        for name, entry in binding['catalog'].items():
            suite = get_suite('v1.2', name)
            decisions[name] = {}
            for task_id in entry['injection_tasks']:
                ordinal += 1
                label = f'[{ordinal}/{total}] {name}/{task_id}'
                task = suite.get_injection_task_by_id(task_id)
                attempts = prior_attempts[name, task_id]
                if not attempts:
                    reused, rejected_records = _reuse(reuse_from, name, task, binding)
                    rejected.update(r['reason'] for r in rejected_records)
                    for record in reused:
                        _write_new(_attempt_directory(root, name, task_id) / 'attempt.json', record)
                        attempts.append(record)
                if not attempts:
                    directory = _attempt_directory(root, name, task_id)
                    progress.emit(f'{label} 开始尝试（仅一次）。')
                    started = time.monotonic()
                    with progress.waiting(label):
                        attempt = _native_attempt(directory, suite, task, config, binding)
                    attempts.append(attempt)
                    tokens = attempt.get('total_tokens')
                    progress.emit(f'{label} 结果={attempt["status"]}；耗时={time.monotonic() - started:.1f}s；'
                                  f'Tokens={tokens if tokens is not None else "未知"}'
                                  + (f'；错误类型={attempt.get("error_type", "NativeTraceError")}' if attempt['status'] == 'error' else ''))
                decisions[name][task_id] = {'status': _decision(attempts), 'attempts': attempts}
                report = _report(root, binding, decisions, rejected)
                counts = report['counts']
                progress.emit(f'{label} 判定={decisions[name][task_id]["status"]}；累计：'
                              f'保留={counts.get("kept", 0)} 排除={counts.get("excluded", 0)} 错误跳过={counts.get("error", 0)}。')
        report = _report(root, binding, decisions, rejected)
        if report['counts'].get('unresolved', 0):
            progress.emit(f'存在待解决目标，未生成名单；以同一条 screen 命令续跑。报告：{root / "summary.md"}；明细：{root / "summary.json"}')
            return 1
        filtered = {'schema_version': FLITER_SCHEMA, 'benchmark': benchmark_header(),
                    'excluded': {name: [task_id for task_id, d in tasks.items() if d['status'] != 'kept']
                                 for name, tasks in decisions.items()}}
        path = root / 'fliter.json'
        if path.exists():
            if load_fliter(path) != {**filtered, 'excluded': {name: sorted(ids) for name, ids in filtered['excluded'].items()}}:
                raise ValueError('existing fliter differs from recorded screening outcomes')
        else:
            _write_new(path, filtered)
        progress.emit(f'完成：{dict(report["counts"])}；排除名单：{path}')
        return int(bool(report['counts'].get('error', 0)))


def cli(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('screen', help='直接预检 injection GOAL 并生成排除名单')
    sub.add_argument('--suites', nargs='+', metavar='SUITE', help='选择当前环境支持的场景；默认全部场景')
    sub.add_argument('--model-config', dest='config_path')
    sub.add_argument('--name', dest='run_name', required=True)
    sub.add_argument('--results-dir', help='默认 results/injection_precheck')
    sub.add_argument('--reuse-from', help='只读复用兼容 baseline 预检记录')
    options = vars(parser.parse_args(argv))
    options.pop('command')
    try:
        return screen(**options)
    except KeyboardInterrupt:
        print('预检已中断，已有记录保留；更新完成后以同一条 screen 命令续跑。', flush=True)
        return 130
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'预检配置错误：{exc}' if isinstance(exc, ValueError)
              else f'预检记录不可用：{type(exc).__name__}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(cli())
