"""One durable, current-pipeline GOAL trajectory per selected injection target."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from agentdojo import logging
from dscg.benchmark_catalog import get_suite
from dscg.task_diagnostics import load_task_trace, task_log_context
from experiments.common import task_storage
from experiments.common.benchmark_tasks import _TaskPipelineProbe


_COUNTERS = {'api_calls', 'failed_calls', 'missing_usage_calls', 'prompt_tokens',
             'completion_tokens', 'total_tokens', 'latency_ms'}
_ERROR_CODES = {'RECORDED_API_FAILURE', 'MODEL_TOOL_ARGUMENTS_INVALID_JSON',
                'MODEL_API_ERROR', 'API_ERROR', 'API_TIMEOUT', 'CONTEXT_LENGTH_EXCEEDED'}


def _save(base, records):
    path = base / 'summary.json'
    summary = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    summary.setdefault('selection_report', {})['goal_checks'] = records
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=base,
                                prefix='.goal-summary-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _snapshots(pipeline):
    trackers = getattr(pipeline, '_goal_trackers', getattr(pipeline, 'trackers', ()))
    return [tracker.snapshot() for tracker in trackers if tracker is not None]


def _cost_delta(before, after):
    if not after:
        return None
    return {'models': [{phase: {key: value - previous.get(phase, {}).get(key, 0)
                               for key, value in counters.items()
                               if key in _COUNTERS and type(value) in (int, float)}
                        for phase, counters in current.items()}
                       for previous, current in zip(before, after)]}


def _failed_calls(cost):
    return any(phase.get('failed_calls', 0) > 0
               for model in (cost or {}).get('models', [])
               for phase in model.values() if isinstance(phase, dict))


def run_goal_checks(base, selections, pipeline_factory, *, reuse=False, progress=False):
    """Persist each start before execution; resume never retries a started GOAL.

    The caller validates and commits run bindings before calling this function.
    A factory receives the suite name and supplies the same configuration as its
    measurement pipeline. Costs are per trajectory; unknown usage remains null.
    """
    base = Path(base).resolve()
    base.mkdir(parents=True, exist_ok=True)
    summary_path = base / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
    records = summary.get('selection_report', {}).get('goal_checks', [])
    if records and not reuse:
        raise ValueError('GOAL checks already started; explicit reuse is required')
    indexed = {(record['suite'], record['injection_task_id']): record for record in records}
    selected = []
    for suite_name, selection in selections.items():
        pipeline = suite = None
        factory_error = False
        for task_id in dict.fromkeys(selection['injection_task_ids']):
            key = (suite_name, task_id)
            if key in indexed:
                record = indexed[key]
                if record['status'] == 'running':
                    record.update(status='error', error_code='GOAL_INTERRUPTED')
                    _save(base, records)
                selected.append(record)
                continue
            record = dict(suite=suite_name, injection_task_id=task_id, status='running',
                          path=f'goal/{suite_name}/{task_id}.json', cost=None)
            path = base / record['path']
            if not path.resolve().is_relative_to(base / 'goal'):
                raise ValueError('GOAL trace path is outside its run')
            # A leftover trace without a start record has no bound execution state.
            if path.exists():
                raise ValueError('GOAL trace exists without a start record')
            records.append(record)
            indexed[key] = record
            selected.append(record)
            _save(base, records)
            if progress:
                print(f'GOAL {suite_name}/{task_id}: running', flush=True)
            before = []
            probe = None
            interrupted = False
            try:
                if factory_error:
                    raise RuntimeError('GOAL pipeline initialization failed')
                if pipeline is None:
                    try:
                        suite = get_suite('v1.2', suite_name)
                        pipeline = pipeline_factory(suite_name)
                        pipeline.name = 'goal'
                    except Exception:
                        factory_error = True
                        raise
                before = _snapshots(pipeline)
                probe = _TaskPipelineProbe(pipeline)
                with logging.OutputLogger(str(base)), task_log_context(
                        suite=suite_name, stage='goal_preflight', user_task_id=None,
                        injection_task_id=task_id):
                    task_storage.run_task_without_injection_tasks(
                        suite, probe, suite.get_injection_task_by_id(task_id), base, True,
                        benchmark_version='v1.2', goal=True)
                trace = load_task_trace(path)
                cost = trace.get('dscg_cost')
                if cost is not None and not isinstance(cost, dict):
                    raise ValueError('invalid GOAL cost record')
                record['cost'] = cost
                failure = trace.get('dscg_infrastructure_failure')
                if failure or trace.get('error') or (
                        'dscg_diagnostics' in trace and trace.get('dscg_diagnostics_status') != 'complete'):
                    code = failure.get('reason_code') if isinstance(failure, dict) else None
                    record.update(status='error', error_code=code if code in _ERROR_CODES else 'GOAL_TRACE_ERROR')
                elif type(trace.get('utility')) is bool:
                    record['status'] = 'passed' if trace['utility'] else 'failed'
                else:
                    record.update(status='error', error_code='GOAL_INCOMPLETE_TRACE')
            except KeyboardInterrupt:
                interrupted = True
                record.update(status='error', error_code='GOAL_INTERRUPTED')
            except Exception as exc:
                # Never persist exception values, prompts or provider response bodies.
                code = ('MODEL_TOOL_ARGUMENTS_INVALID_JSON' if isinstance(exc, json.JSONDecodeError)
                        or (probe is not None and probe.error is not None) else 'GOAL_EXECUTION_ERROR')
                record.update(status='error', error_code=code)
            finally:
                if pipeline is not None:
                    fallback = _cost_delta(before, _snapshots(pipeline)) if before else None
                    if record['cost'] is None:
                        record['cost'] = fallback
                    if _failed_calls(record['cost']) and not interrupted:
                        record.update(status='error', error_code='RECORDED_API_FAILURE')
                _save(base, records)
            if progress:
                print(f'GOAL {suite_name}/{task_id}: {record["status"]}', flush=True)
            if interrupted:
                raise KeyboardInterrupt
    return selected
