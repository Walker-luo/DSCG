"""Flat native traces without modifying the installed backend or its globals."""
from functools import partial
import json
from pathlib import Path
from types import FunctionType
import warnings

from agentdojo import benchmark as native
from agentdojo.logging import TraceLogger
from pydantic import BaseModel


from experiments.common.task_paths import trace_path


class FlatTraceLogger(TraceLogger):
    """Keep the native payload and logger lifecycle, changing only output paths."""
    def __init__(self, delegate, *, goal=False, **contextargs):
        self.goal = goal
        super().__init__(delegate, **contextargs)

    def group_directory(self):
        return Path(self.dirpath) / str(self.context['pipeline_name']).replace('/', '_') / str(self.context['suite_name'])

    def task_directory(self):
        group = self.group_directory()
        return group if self.goal else group / str(self.context['user_task_id'])

    def task_stem(self):
        return str(self.context['user_task_id'] if self.goal else self.context.get('injection_task_id') or 'none')

    def save(self):
        if self.context.get('attack_type') is None or self.context.get('pipeline_name') is None:
            warnings.warn('Cannot log executed benchmark without attack_type and pipeline_name.')
            return
        # These are the native save fields; no scoring or interaction transformation.
        fields = ('suite_name', 'pipeline_name', 'user_task_id', 'injection_task_id', 'attack_type', 'injections')
        payload = {key: self.context.get(key) for key in fields}
        payload['pipeline_name'] = str(payload['pipeline_name']).replace('/', '_')
        payload['attack_type'] = payload['attack_type'] if payload['attack_type'] != 'none' else None
        payload['injections'] = self.context.get('injections', {})
        payload.update(messages=self.messages, error=self.error)
        payload.update({key: value for key, value in self.context.items() if key not in fields})
        directory = self.task_directory()
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / (self.task_stem()+'.json')).open('w') as stream:
            json.dump(payload, stream, indent=4,
                default=lambda obj: obj.model_dump() if isinstance(obj, BaseModel) else obj)


def load_task_results(pipeline_name, suite_name, user_task, attack_name, injection_task, logdir, *, goal=False):
    # Execution caches are layout-specific. Legacy fallback belongs only to
    # read-only report paths; it must not silently reuse a legacy scored cache.
    suite_dir = Path(logdir)/pipeline_name/suite_name
    path = suite_dir / (f'{user_task}.json' if goal else f'{user_task}/{injection_task or "none"}.json')
    with path.open() as stream:
        result = json.load(stream)
    if 'agentdojo_package_version' not in result:
        result['messages'] = native.convert_old_messages_format(result['messages'])
    return native.TaskResults(**result)


def _bound_native(function, goal):
    # Private globals retain backend-specific exception/scoring behavior verbatim.
    bindings = dict(function.__globals__, TraceLogger=partial(FlatTraceLogger, goal=goal),
        load_task_results=partial(load_task_results, goal=goal))
    return FunctionType(function.__code__, bindings, function.__name__, function.__defaults__, function.__closure__)


def run_task_with_injection_tasks(suite, agent_pipeline, user_task, attack, logdir, force_rerun,
                                  injection_tasks=None, benchmark_version=None, *, goal=False):
    return _bound_native(native.run_task_with_injection_tasks, goal)(suite, agent_pipeline, user_task,
        attack, logdir, force_rerun, injection_tasks, benchmark_version)


def run_task_without_injection_tasks(suite, agent_pipeline, task, logdir, force_rerun,
                                     benchmark_version=None, *, goal=False):
    return _bound_native(native.run_task_without_injection_tasks, goal)(suite, agent_pipeline, task,
        logdir, force_rerun, benchmark_version)
