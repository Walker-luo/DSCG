"""Progress mode retains the native task order and result shape."""
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import warnings

from agentdojo import benchmark

from experiments.common.benchmark_progress import GroupProgress, run_suite_with_progress


class FakeSuite:
    name = "travel"

    def __init__(self):
        self.user_tasks = {name: SimpleNamespace(ID=name) for name in ("u0", "u1")}
        self.injection_tasks = {name: SimpleNamespace(ID=name) for name in ("i0", "i1")}

    def get_user_task_by_id(self, task_id):
        return self.user_tasks[task_id]

    def get_injection_task_by_id(self, task_id):
        return self.injection_tasks[task_id]


class ProgressAdapterTests(TestCase):
    def test_second_goal_failure_identifies_phase_without_changing_exception(self):
        suite = FakeSuite()
        calls = []
        def preflight(_suite, _pipeline, task, *_args):
            calls.append(task.ID)
            if task.ID == 'i1':
                raise TypeError('sensitive-prompt-text')
            return True, True

        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=preflight), \
             patch.object(benchmark, 'run_task_with_injection_tasks') as scored:
            with self.assertRaises(TypeError) as caught:
                run_suite_with_progress(None, suite, SimpleNamespace(is_dos_attack=False), None, False,
                    user_tasks=['u0'], injection_tasks=['i0', 'i1'], benchmark_version='v1.2',
                    on_step=lambda _phase: None)
        self.assertEqual(calls, ['i0', 'i1'])
        scored.assert_not_called()
        self.assertEqual(caught.exception._dscg_execution_stage, 'goal_preflight')
        self.assertEqual(caught.exception._dscg_task_id, 'i1')

    def test_readonly_native_exception_is_not_replaced_by_progress_annotation(self):
        class ReadonlyError(RuntimeError):
            def __setattr__(self, name, value):
                if name.startswith('_dscg_'):
                    raise TypeError('readonly')
                super().__setattr__(name, value)
        suite = FakeSuite()
        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=ReadonlyError('native')):
            with self.assertRaises(ReadonlyError):
                run_suite_with_progress(None, suite, SimpleNamespace(is_dos_attack=False), None, False,
                    user_tasks=['u0'], injection_tasks=['i0'], benchmark_version='v1.2',
                    on_step=lambda _phase: None)

    def test_targeted_reports_preflight_then_each_scored_pair(self):
        suite = FakeSuite()
        attack = SimpleNamespace(is_dos_attack=False)
        calls = []
        events = []

        def preflight(_suite, _pipeline, task, *_args):
            calls.append(("goal", task.ID))
            return task.ID == "i0", True

        def scored(_suite, _pipeline, task, _attack, _logdir, _force, injection_tasks, _version):
            self.assertEqual(len(injection_tasks), 1)
            target = injection_tasks[0]
            calls.append(("score", task.ID, target))
            return {(task.ID, target): True}, {(task.ID, target): False}

        with patch.object(benchmark, "run_task_without_injection_tasks", side_effect=preflight), patch.object(
            benchmark, "run_task_with_injection_tasks", side_effect=scored
        ), warnings.catch_warnings(record=True) as notices:
            result = run_suite_with_progress(None, suite, attack, None, False,
                user_tasks=["u0", "u1"], injection_tasks=["i0", "i1"],
                benchmark_version="v1.2", on_step=lambda phase: events.append(phase))

        self.assertEqual(calls, [
            ("goal", "i0"), ("goal", "i1"),
            ("score", "u0", "i0"), ("score", "u0", "i1"),
            ("score", "u1", "i0"), ("score", "u1", "i1"),
        ])
        self.assertEqual(events, ["goal", "goal", "score", "score", "score", "score"])
        self.assertEqual(result["injection_tasks_utility_results"], {"i0": True, "i1": False})
        self.assertEqual(len(result["utility_results"]), 4)
        self.assertEqual(len(notices), 1)

    def test_clean_counts_users_and_dos_skips_goal_preflight(self):
        suite = FakeSuite()
        events = []
        with patch.object(benchmark, "run_task_without_injection_tasks", return_value=(False, True)) as native:
            clean = run_suite_with_progress(None, suite, None, None, False,
                user_tasks=["u0", "u1"], injection_tasks=[], benchmark_version="v1.2",
                on_step=lambda phase: events.append(phase))
        self.assertEqual(native.call_count, 2)
        self.assertEqual(events, ["score", "score"])
        self.assertEqual(clean["utility_results"], {("u0", ""): False, ("u1", ""): False})

        events.clear()
        with patch.object(benchmark, "run_task_without_injection_tasks") as native, patch.object(
            benchmark, "run_task_with_injection_tasks",
            side_effect=lambda _s, _p, user, _a, _l, _f, ids, _v: (
                {(user.ID, ids[0]): True}, {(user.ID, ids[0]): False})) as attacked:
            result = run_suite_with_progress(None, suite, SimpleNamespace(is_dos_attack=True), None, False,
                user_tasks=["u0", "u1"], injection_tasks=["i0"], benchmark_version="v1.2",
                on_step=lambda phase: events.append(phase))
        native.assert_not_called()
        self.assertEqual(attacked.call_count, 2)
        self.assertEqual(events, ["score", "score"])
        self.assertEqual(len(result["utility_results"]), 2)


class ProgressDisplayTests(TestCase):
    def test_redirected_log_uses_plain_bounded_milestones(self):
        stream = StringIO()
        with GroupProgress("important_instructions/travel", goal_total=2, score_total=100,
                           stream=stream, is_tty=False) as progress:
            progress.advance("goal")
            progress.advance("goal")
            for _ in range(100):
                progress.advance("score")
        output = stream.getvalue()
        self.assertIn("GOAL 2/2", output)
        self.assertIn("任务 100/100", output)
        self.assertNotIn("\x1b[", output)
        self.assertLessEqual(len(output.splitlines()), 26)

    def test_error_keeps_partial_count(self):
        stream = StringIO()
        with self.assertRaisesRegex(RuntimeError, "offline"):
            with GroupProgress("none/slack", goal_total=0, score_total=3,
                               stream=stream, is_tty=False) as progress:
                progress.advance("score")
                raise RuntimeError("offline")
        self.assertIn("任务 1/3", stream.getvalue())
        self.assertIn("error", stream.getvalue())


class InstalledNativeProgressParityTests(TestCase):
    def test_real_suite_offline_response_matches_native_order_and_cache(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from agentdojo import attacks, logging
        from agentdojo.types import ChatAssistantMessage, text_content_block_from_string
        from dscg.benchmark_catalog import get_backend, get_suite
        from experiments.common.native_cache_compat import ensure_native_cache_model_ready

        ensure_native_cache_model_ready()
        suite_name = get_backend().suites[0]
        suite = get_suite('v1.2', suite_name)
        users = list(suite.user_tasks)[:1]
        targets = list(suite.injection_tasks)[:2]
        artifact_root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261020_deepseek_agentdyn_typeerror/test_runs'
        artifact_root.mkdir(parents=True, exist_ok=True)

        def run(root, with_progress):
            calls = []
            class ScriptedPipeline:
                name = 'offline-native-progress'
                def query(self, query, runtime, env, messages=None, extra_args=None):
                    calls.append('query')
                    answer = ChatAssistantMessage(role='assistant',
                        content=[text_content_block_from_string('offline response')], tool_calls=None)
                    output = [{'role': 'user', 'content': [text_content_block_from_string(query)]}, answer]
                    logging.Logger.get().log(output)
                    return query, runtime, env, output, extra_args or {}
            pipeline = ScriptedPipeline()
            attack = attacks.load_attack('ignore_previous', suite, pipeline)
            with logging.OutputLogger(str(root)):
                if with_progress:
                    events = []
                    result = run_suite_with_progress(pipeline, suite, attack, root, False,
                        user_tasks=users, injection_tasks=targets, benchmark_version='v1.2',
                        on_step=events.append)
                else:
                    result = benchmark.benchmark_suite_with_injections(pipeline, suite, attack, root,
                        force_rerun=False, user_tasks=users, injection_tasks=targets,
                        verbose=False, benchmark_version='v1.2')
                    events = None
            return result, calls, events

        with TemporaryDirectory(dir=artifact_root) as root:
            native_dir, progress_dir = Path(root) / 'native', Path(root) / 'progress'
            native, native_calls, _ = run(native_dir, False)
            shown, shown_calls, events = run(progress_dir, True)
            for field in ('utility_results', 'security_results', 'injection_tasks_utility_results'):
                self.assertEqual(native[field], shown[field])
            self.assertEqual(native_calls, shown_calls)
            self.assertEqual(events, ['goal'] * len(targets) + ['score'] * len(targets))
            cached, cached_calls, cached_events = run(progress_dir, True)
            self.assertEqual(cached_calls, [])
            self.assertEqual(cached_events, events)
            self.assertEqual(cached['utility_results'], shown['utility_results'])

