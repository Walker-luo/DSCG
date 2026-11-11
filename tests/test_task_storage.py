"""Offline checks of repo-local storage around the installed native executor."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from agentdojo import benchmark, logging
from experiments.common import task_storage as storage
from experiments.common.native_cache_compat import ensure_native_cache_model_ready
from dscg.task_diagnostics import DiagnosticSession, load_task_trace, diagnostic_dependencies


class TaskStorageTests(unittest.TestCase):
    def setUp(self):
        ensure_native_cache_model_ready()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = 0
        self.task = SimpleNamespace(ID='user_task_0')
        self.injection = SimpleNamespace(ID='injection_task_0')
        self.pipeline = SimpleNamespace(name='important_instructions')
        self.suite = SimpleNamespace(name='banking', injection_tasks={self.injection.ID: self.injection},
            get_injection_task_by_id=lambda key: self.injection, run_task_with_pipeline=self.run_task)
        self.attack = SimpleNamespace(name='important_instructions', is_dos_attack=False,
            attack=lambda user, injection: {'file': 'fixture'})

    def run_task(self, *args, **kwargs):
        self.calls += 1
        logger = logging.Logger.get()
        with DiagnosticSession(logger, str(self.calls), {'framework': {'version': 'fixture'}}) as session:
            session.save_response('audit', {'response_id': str(self.calls), 'content': 'fixture'})
            session.finish({})
        logger.log([{'role': 'user', 'content': [{'type': 'text', 'content': 'hello'}]},
                    {'role': 'assistant', 'tool_calls': None, 'content': [{'type': 'text', 'content': 'done'}]}])
        return True, False

    def execute(self, *, goal=False, clean=False, force=False):
        with logging.OutputLogger(self.root):
            if clean or goal:
                return storage.run_task_without_injection_tasks(self.suite, self.pipeline, self.task,
                    self.root, force, goal=goal)
            return storage.run_task_with_injection_tasks(self.suite, self.pipeline, self.task,
                self.attack, self.root, force)

    def test_attack_native_cache_and_append_offsets(self):
        native_logger = benchmark.TraceLogger
        native_loader = benchmark.load_task_results
        self.assertEqual(self.execute(), ({('user_task_0', 'injection_task_0'): True},
                                          {('user_task_0', 'injection_task_0'): False}))
        path = self.root/'important_instructions/banking/user_task_0/injection_task_0.json'
        self.assertTrue(path.is_file())
        raw = json.loads(path.read_text())
        self.assertEqual(raw['attack_type'], self.attack.name)
        self.assertEqual(load_task_trace(path)['dscg_diagnostics_status'], 'complete')
        side = path.with_suffix('.dscg.jsonl')
        prefix = side.read_bytes()
        start = json.loads(prefix.splitlines()[0])
        self.assertTrue(start['record']['config_ref'].startswith('../dscg_config.'))
        self.assertEqual(len(diagnostic_dependencies(path)), 3)
        self.execute()
        self.assertEqual(self.calls, 1)
        self.assertEqual(prefix, side.read_bytes())
        self.execute(force=True)
        self.assertEqual(self.calls, 2)
        self.assertTrue(side.read_bytes().startswith(prefix))
        self.assertEqual(json.loads(path.read_text())['dscg_diagnostics']['offset'], len(prefix))
        self.assertEqual(load_task_trace(path)['dscg_diagnostics_status'], 'complete')
        self.assertIs(benchmark.TraceLogger, native_logger)
        self.assertIs(benchmark.load_task_results, native_loader)

    def test_clean_and_goal_paths_and_cache(self):
        for goal in (False, True):
            self.pipeline.name = 'goal' if goal else 'none'
            if goal: self.task = self.injection
            self.execute(goal=goal, clean=True)
            suite = self.root/self.pipeline.name/'banking'
            expected = suite/(self.task.ID+'.json') if goal else suite/self.task.ID/'none.json'
            self.assertTrue(expected.is_file())
            rows = expected.with_suffix('.dscg.jsonl').read_text().splitlines()
            ref = json.loads(rows[0])['record']['config_ref']
            self.assertEqual(ref.count('../'), 0 if goal else 1)
            self.assertEqual(load_task_trace(expected)['dscg_diagnostics_status'], 'complete')
            before = self.calls
            self.execute(goal=goal, clean=True)
            self.assertEqual(self.calls, before)

    def test_legacy_reader_fallback_does_not_mix_execution_caches(self):
        self.execute()
        suite = self.root/self.pipeline.name/'banking'
        flat = suite/self.task.ID/(self.injection.ID+'.json')
        legacy = flat.parent/self.attack.name/flat.name
        legacy.parent.mkdir()
        legacy.write_bytes(flat.read_bytes())
        flat.unlink()
        self.assertEqual(storage.trace_path(suite, self.task.ID, self.attack.name, self.injection.ID), legacy)
        original = legacy.read_bytes()
        self.execute()
        self.assertEqual(self.calls, 2)
        self.assertEqual(legacy.read_bytes(), original)
        self.assertTrue(flat.is_file())
        self.assertEqual(storage.trace_path(suite, self.task.ID, self.attack.name, self.injection.ID), flat)

    def test_native_dos_scoring_and_injection_selection_are_preserved(self):
        self.attack.is_dos_attack = True
        self.suite.injection_tasks['injection_task_1'] = SimpleNamespace(ID='injection_task_1')
        with logging.OutputLogger(self.root):
            utility, security = storage.run_task_with_injection_tasks(self.suite, self.pipeline, self.task,
                self.attack, self.root, False, injection_tasks=['injection_task_1'])
        self.assertEqual(self.calls, 1)
        self.assertEqual(utility, {('user_task_0', 'injection_task_0'): True})
        self.assertEqual(security, {('user_task_0', 'injection_task_0'): False})

    def test_exception_leaves_native_error_trace_and_restores_logger(self):
        def fail(*args, **kwargs):
            raise RuntimeError('fixture failure')
        self.suite.run_task_with_pipeline = fail
        with logging.OutputLogger(self.root) as outer:
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                storage.run_task_without_injection_tasks(self.suite, self.pipeline, self.task,
                    self.root, False)
            self.assertIs(logging.Logger.get(), outer)
        path = self.root/self.pipeline.name/'banking/user_task_0/none.json'
        self.assertTrue(path.is_file())
        self.assertNotIn('utility', json.loads(path.read_text()))

    def test_full_trace_and_goal_legacy_paths(self):
        from dscg.pipelines.defended import _trace_artifact_path
        with logging.OutputLogger(self.root) as outer:
            for goal in (False, True):
                logger = storage.FlatTraceLogger(outer, goal=goal, pipeline_name='goal' if goal else 'none',
                    suite_name='banking', user_task_id='injection_task_0' if goal else 'user_task_0',
                    attack_type='none', injection_task_id=None)
                directory = self.root/('goal/banking' if goal else 'none/banking/user_task_0')
                stem = 'injection_task_0' if goal else 'none'
                self.assertEqual(_trace_artifact_path(logger), directory/(stem+'.dscg_trace.jsonl.gz'))
        suite = self.root/'goal/banking'
        legacy = suite/'injection_task_0/none/none.json'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{}')
        self.assertEqual(storage.trace_path(suite, 'injection_task_0', 'none', 'none', goal=True), legacy)

    def test_native_save_payload_is_identical(self):
        context = dict(pipeline_name='attack/name', suite_name='banking', user_task_id='user_task_0',
            attack_type='important_instructions', injection_task_id='injection_task_0',
            injections={'file': 'fixture'}, utility=True, security=False, duration=1.0,
            dscg_diagnostics={'path': 'injection_task_0.dscg.jsonl', 'offset': 3, 'attempt_id': 'fixture'})
        native_logger = logging.TraceLogger(logging.OutputLogger(self.root/'native'), **context)
        flat_logger = storage.FlatTraceLogger(logging.OutputLogger(self.root/'flat'), **context)
        flat_logger.context = dict(native_logger.context)
        native_logger.save()
        flat_logger.save()
        legacy = self.root/'native/attack_name/banking/user_task_0/important_instructions/injection_task_0.json'
        flat = self.root/'flat/attack_name/banking/user_task_0/injection_task_0.json'
        self.assertEqual(legacy.read_bytes(), flat.read_bytes())


if __name__ == '__main__':
    unittest.main()
