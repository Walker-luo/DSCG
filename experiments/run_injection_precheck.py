"""Direct injection-goal screening with live progress and immutable evidence."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sys
import threading
import time

from agentdojo import benchmark, logging
from agentdojo.task_suite import get_suite
from dscg.model_config import resolve_model_config
from dscg.paths import RESULTS_DIR
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from experiments import run_partial_benchmark as shared
from experiments.common.partial_controls import SUITES, source_revision, guard_run
from experiments.common.injection_cohort import (
    SCHEMA, RULE, LIMITATIONS, _digest, _file_hash, _read, _write_new, _replace,
    _lock, _binding, _trace_status, _decision, _validate_cohort, _validate_cohort_data,
    _bindings_compatible, _binding_error, _source_compatible, _record_compatibility, run_screened,
)

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
                    or not _source_compatible(manifest['source'], binding['source'], check_python=False)
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
    progress = Progress()
    progress.emit('启动，正在读取配置与任务目录。')
    config = resolve_model_config(config_path=config_path)
    current_binding = _binding(config, suites)
    root = Path(results_dir or RESULTS_DIR / 'injection_precheck') / (
        shared._safe_result_component(config.model_id, 'model') + '_' + shared._safe_result_component(run_name, 'screen'))
    if reuse_from is not None and not Path(reuse_from).is_dir():
        raise ValueError('--reuse-from must be an existing benchmark run directory')
    with _lock(root):
        manifest_path = root / 'screen_manifest.json'
        resumed = manifest_path.exists()
        binding = _read(manifest_path) if resumed else current_binding
        if not _bindings_compatible(binding, current_binding):
            raise ValueError(_binding_error(binding, current_binding))
        guard_run(manifest_path, binding)
        _record_compatibility(root, binding, current_binding)
        total = sum(len(e['injection_tasks']) for e in binding['catalog'].values())
        progress.emit(f'模型={config.model_id}；目标={total}；模式={"续跑" if resumed else "首次运行"}；输出={root}')
        progress.emit(f'复用来源={reuse_from or "未指定"}；规则：任一次成功保留，两次有效失败排除，错误待解决。')
        if (root / 'cohort.json').exists():
            _validate_cohort(root / 'cohort.json', config)
            progress.emit(f'冻结名单已存在，核验通过，无新增模型调用：{root / "cohort.json"}')
            return 0
        decisions, rejected = {}, []
        ordinal = 0
        if (root / 'status.json').exists():
            rejected = _read(root / 'status.json').get('reuse_rejections', [])
        for name, entry in binding['catalog'].items():
            suite = get_suite('v1.2', name)
            decisions[name] = {}
            for task_id in entry['injection_tasks']:
                ordinal += 1
                label = f'[{ordinal}/{total}] {name}/{task_id}'
                progress.emit(f'{label} 检查已有尝试与复用记录。')
                task = suite.get_injection_task_by_id(task_id)
                attempts = _attempts(root, name, task_id, binding)
                if attempts:
                    progress.emit(f'{label} 恢复已有尝试={len(attempts)}，状态={_decision(attempts)}。')
                if not attempts:
                    reused, rejected_records = _reuse(reuse_from, name, task, binding)
                    rejected.extend(rejected_records)
                    for record in reused:
                        _write_new(_attempt_directory(root, name, task_id) / 'attempt.json', record)
                        attempts.append(record)
                    if reused:
                        progress.emit(f'{label} 复用历史尝试={len(reused)}，状态={_decision(attempts)}。')
                    if rejected_records:
                        progress.emit(f'{label} 不兼容或不完整记录={len(rejected_records)}，继续补测。')
                while _decision(attempts) == 'unresolved':
                    directory = _attempt_directory(root, name, task_id)
                    retest = any(a['status'] == 'fail' for a in attempts)
                    progress.emit(f'{label} 开始尝试 {directory.name}（{"失败复测" if retest else "新尝试"}）。')
                    started = time.monotonic()
                    with progress.waiting(label):
                        attempt = _native_attempt(directory, suite, task, config, binding)
                    attempts.append(attempt)
                    tokens = attempt.get('total_tokens')
                    progress.emit(f'{label} 结果={attempt["status"]}；耗时={time.monotonic() - started:.1f}s；'
                                  f'Tokens={tokens if tokens is not None else "未知"}'
                                  + (f'；错误类型={attempt.get("error_type", "NativeTraceError")}' if attempt['status'] == 'error' else ''))
                    if attempt['status'] == 'error':
                        break  # No implicit network retry; a later invocation can resume.
                decisions[name][task_id] = {'status': _decision(attempts), 'attempts': attempts}
                report = _report(root, binding, decisions, rejected)
                counts = report['counts']
                progress.emit(f'{label} 判定={decisions[name][task_id]["status"]}；累计：'
                              f'保留={counts.get("kept", 0)} 排除={counts.get("excluded", 0)} 未决={counts.get("unresolved", 0)}。')
        report = _report(root, binding, decisions, rejected)
        if report['counts'].get('unresolved', 0):
            progress.emit(f'存在待解决目标，未生成名单；以同一条 screen 命令续跑。报告：{root / "summary.md"}；明细：{root / "status.json"}')
            return 1
        cohort = {'schema_version': SCHEMA, 'suite_version': 'v1.2', 'task_scope': 'screened',
                  'selection_rule': RULE, 'binding': current_binding, 'decisions': decisions,
                  'suites': {name: {'user_task_ids': entry['user_task_ids'],
                      'injection_task_ids': [i for i, d in decisions[name].items() if d['status'] == 'kept']}
                      for name, entry in binding['catalog'].items()}, 'limitations': LIMITATIONS}
        cohort['cohort_sha256'] = _digest(cohort)
        _validate_cohort_data(cohort, config)
        _write_new(root / 'cohort.json', cohort)
        progress.emit(f'完成：{dict(report["counts"])}；报告：{root / "summary.md"}；名单：{root / "cohort.json"}')
        return 0


def cli(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'benchmark':
        from experiments.run_benchmark import cli as benchmark_cli
        print('兼容入口：请改用 python -m experiments.run_benchmark --cohort ...', flush=True)
        return benchmark_cli(argv[1:], require_cohort=True)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    sub = commands.add_parser('screen', help='直接预检 injection GOAL 并冻结筛选名单')
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
