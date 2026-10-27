"""Native task calls with narrowly scoped model-tool-JSON error isolation."""
from contextlib import contextmanager
import json
from pathlib import Path
from uuid import uuid4
import warnings

from agentdojo import benchmark
from agentdojo.agent_pipeline.llms.openai_llm import _openai_to_tool_call
from experiments.common.error_diagnostics import execution_error_diagnostics
from dscg.task_diagnostics import task_log_context


class _TaskToolJSONAbort(Exception):
    """Task control signal outside the native chat request retry decorator."""


class _ResponseObserver:
    def __init__(self, target, observe, kind='client'):
        self.target, self.observe, self.kind = target, observe, kind

    def __getattr__(self, name):
        if (self.kind, name) in {('client', 'chat'), ('chat', 'completions')}:
            return _ResponseObserver(getattr(self.target, name), self.observe,
                                     'chat' if name == 'chat' else 'completions')
        return getattr(self.target, name)

    def create(self, *args, **kwargs):
        response = self.target.create(*args, **kwargs)
        self.observe(response)
        return response


class _TaskPipelineProbe:
    """Observe errors before a backend catches them; never alter its response."""
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.error = None

    def __getattr__(self, name):
        return getattr(self.pipeline, name)

    def record(self, exc, response=None):
        choices = getattr(response, 'choices', None) or []
        finish = getattr(choices[0], 'finish_reason', None) if choices else None
        tokens = getattr(getattr(response, 'usage', None), 'completion_tokens', None)
        self.error = {'reason_code': 'MODEL_TOOL_ARGUMENTS_INVALID_JSON',
                      'arguments_length': len(exc.doc), 'position': exc.pos,
                      'line': exc.lineno, 'column': exc.colno,
                      'json_error_kind': 'empty_arguments' if not exc.doc.strip() else 'json_syntax',
                      'response_finish_reason': finish if finish in {
                          'stop', 'length', 'tool_calls', 'content_filter', 'function_call'} else None,
                      'response_completion_tokens': tokens if type(tokens) is int and tokens >= 0 else None,
                      'execution_error': execution_error_diagnostics(exc)}

    def observe(self, response):
        choices = getattr(response, 'choices', None)
        if not choices:
            return
        for call in getattr(choices[0].message, 'tool_calls', None) or ():
            try:
                _openai_to_tool_call(call)
            except json.JSONDecodeError as exc:
                self.record(exc, response)
                break
            except (TypeError, ValueError, AttributeError):
                # Preserve the native handling of errors outside JSON syntax.
                continue

    @contextmanager
    def observe_main_models(self):
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
        seen, restored = set(), []
        def visit(node):
            if id(node) in seen:
                return
            seen.add(id(node))
            if isinstance(node, OpenAILLM):
                previous = node.__dict__.get('query')
                bound = node.query
                def query(*args, **kwargs):
                    client = node.client
                    node.client = _ResponseObserver(client, self.observe)
                    try:
                        result = bound(*args, **kwargs)
                    except json.JSONDecodeError:
                        if self.error is None:
                            raise
                        raise _TaskToolJSONAbort('MODEL_TOOL_ARGUMENTS_INVALID_JSON') from None
                    finally:
                        node.client = client
                    if self.error is not None:
                        raise _TaskToolJSONAbort('MODEL_TOOL_ARGUMENTS_INVALID_JSON')
                    return result
                node.query = query
                restored.append((node, previous))
                return
            for element in getattr(node, 'elements', ()):
                visit(element)
            # Baseline contains native LLM elements; DSCG's executor exposes llm.
            # Do not traverse audit small_llm or arbitrary model/client state.
            llm = getattr(node, 'llm', None)
            if llm is not None:
                visit(llm)
        try:
            visit(self.pipeline)
            yield
        finally:
            for node, previous in reversed(restored):
                if previous is None:
                    del node.query
                else:
                    node.query = previous

    def query(self, *args, **kwargs):
        try:
            with self.observe_main_models():
                return self.pipeline.query(*args, **kwargs)
        except json.JSONDecodeError as exc:
            tb = exc.__traceback__
            while tb is not None:
                if tb.tb_frame.f_code is _openai_to_tool_call.__code__:
                    self.record(exc)
                    break
                tb = tb.tb_next
            raise


def run_native_suite(pipeline, suite, attack, logdir, force_rerun, *,
                     user_tasks, injection_tasks, benchmark_version, on_step=None):
    """Call native single-task functions; only malformed model JSON is isolated."""
    users = [suite.get_user_task_by_id(task_id) for task_id in user_tasks]
    probe = _TaskPipelineProbe(pipeline)
    errors = []
    invocation = uuid4().hex

    def completed(stage, user_id, target_id, native, phase):
        probe.error = None
        task_id = f'{user_id}/{target_id}' if target_id is not None else user_id
        with task_log_context(suite=suite.name, stage=stage,
                user_task_id=None if stage == 'goal_preflight' else user_id,
                injection_task_id=user_id if stage == 'goal_preflight' else target_id):
            try:
                result = native()
            except Exception as exc:
                if probe.error is None:
                    try:
                        exc._dscg_execution_stage = stage
                        exc._dscg_task_id = task_id
                    except (AttributeError, TypeError):
                        pass
                    raise
        if probe.error is not None:
            record = {'schema_version': 'dscg.task-error.v1', 'invocation_id': invocation,
                      'suite': suite.name, 'attack': attack.name if attack is not None else 'none',
                      'stage': stage, 'user_task_id': user_id, 'injection_task_id': target_id,
                      **probe.error}
            record['execution_error'].update(stage=stage, task_id=task_id)
            if logdir is not None:
                root = Path(logdir).resolve()
                directory = root / pipeline.name / suite.name
                if not directory.resolve().is_relative_to(root):
                    raise ValueError('task error directory is outside the run')
                directory.mkdir(parents=True, exist_ok=True)
                with (directory / 'task_errors.jsonl').open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            errors.append(record)
            print(f'{suite.name}/{task_id}: {record["reason_code"]} ({stage}); 记为任务错误，继续。', flush=True)
            result = (({(user_id, target_id): None}, {(user_id, target_id): None})
                      if stage == 'scored_task' else (None, None))
        if on_step is not None:
            on_step(phase)
        return result

    utility_results, security_results, goal_results = {}, {}, {}
    if attack is None:
        for user in users:
            utility, security = completed('clean_task', user.ID, None,
                lambda: benchmark.run_task_without_injection_tasks(
                    suite, probe, user, logdir, force_rerun, benchmark_version), 'score')
            utility_results[(user.ID, '')] = utility
            security_results[(user.ID, '')] = security
    else:
        target_tasks = (suite.injection_tasks if injection_tasks is None else {
            task_id: suite.get_injection_task_by_id(task_id) for task_id in injection_tasks})
        targets = [next(iter(suite.injection_tasks))] if attack.is_dos_attack else list(target_tasks)
        if not attack.is_dos_attack:
            for task_id, task in target_tasks.items():
                goal_results[task_id], _ = completed('goal_preflight', task_id, None,
                    lambda: benchmark.run_task_without_injection_tasks(
                        suite, probe, task, logdir, force_rerun, benchmark_version), 'goal')
            for task_id, success in goal_results.items():
                label = (f'suite={suite.name} stage=goal_preflight '
                         f'user_task_id=none injection_task_id={task_id}')
                if success is False:
                    warnings.warn(f'[{label}] Injection GOAL was not solved as a user task.')
                elif success is None:
                    warnings.warn(f'[{label}] GOAL preflight tool-JSON errors are unresolved, not capability failures.')
        for user in users:
            for task_id in targets:
                utility, security = completed('scored_task', user.ID, task_id,
                    lambda: benchmark.run_task_with_injection_tasks(
                        suite, probe, user, attack, logdir, force_rerun, [task_id], benchmark_version), 'score')
                utility_results.update(utility)
                security_results.update(security)
    result = {'utility_results': utility_results, 'security_results': security_results,
              'injection_tasks_utility_results': goal_results}
    if errors:
        result['task_errors'] = errors
    return result
