"""Explicit resume preserves native caching and immutable run evidence."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.task_suite import get_suite
from experiments import run_benchmark as full, run_partial_benchmark as runner
from test_partial_attacks import fake_pipeline


OLD_ATTACKS = ['ignore_previous', 'injecagent', 'important_instructions', 'tool_knowledge']


class ReuseCliTests(unittest.TestCase):
    def test_both_cli_reuse_overrides_environment_and_preserves_omission(self):
        for cli in (runner.cli, full.cli):
            with self.subTest(cli=cli), patch.object(runner, 'main', return_value=0) as run, patch.dict(
                os.environ, {'DSCG_FORCE_RERUN': '1'}, clear=True
            ):
                self.assertEqual(cli(['--reuse', '--name', 'old', '--baseline']), 0)
                self.assertTrue(run.call_args.kwargs['reuse'])
                self.assertFalse(run.call_args.kwargs['force_rerun'])
                self.assertIsNone(run.call_args.kwargs['attack'])
                self.assertIsNone(run.call_args.kwargs['suites'])

    def test_reuse_requires_name_and_rejects_explicit_force_or_export(self):
        for cli in (runner.cli, full.cli):
            for flags in (['--reuse'], ['--reuse', '--name', 'old', '--force-rerun'],
                          ['--reuse', '--name', 'old', '--write-task-manifest', 'out.json']):
                with self.subTest(flags=flags), patch.object(runner, 'main') as run, redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        cli(flags)
                    self.assertEqual(error.exception.code, 2)
                    run.assert_not_called()


class ReuseIntegrationTests(unittest.TestCase):
    def setUp(self):
        artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261017_benchmark_reuse/test_runs'
        artifacts.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=artifacts); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.executed = []
        def execute(_suite, pipeline, task, injection_task=None, injections=None):
            self.executed.append((task.ID, getattr(injection_task, 'ID', None)))
            runner.logging.Logger.get().log([
                {'role': 'user', 'content': [{'type': 'text', 'content': 'offline fixture'}]},
                {'role': 'assistant', 'content': [{'type': 'text', 'content': 'done'}], 'tool_calls': None},
            ])
            return task.ID != 'user_task_0', False
        suite = get_suite('v1.2', 'workspace')
        for p in [patch.object(runner, 'make_openai_compatible_pipeline', side_effect=fake_pipeline),
                  patch.object(runner, 'resolve_model_config', create=True,
                               return_value=SimpleNamespace(model_id='offline-model')),
                  patch.object(runner.attacks, 'load_attack', side_effect=lambda name, *_: SimpleNamespace(
                      name=name, is_dos_attack=False, attack=lambda *_: {})),
                  patch.object(type(suite), 'run_task_with_pipeline', autospec=True, side_effect=execute)]:
            p.start(); self.addCleanup(p.stop)

    @property
    def base(self):
        return self.root / 'offline-model_old'

    def run_benchmark(self, entry=runner.main, **overrides):
        options = dict(origin=True, suites=['workspace'], results_dir=self.root, run_name='old',
                       attack='tool_knowledge')
        options.update(overrides)
        with redirect_stdout(StringIO()):
            return entry(**options)

    def files(self):
        return {p.relative_to(self.base): p.read_bytes() for p in self.base.rglob('*') if p.is_file()}

    def test_resume_only_missing_native_task_and_keeps_completed_failure(self):
        for entry in (runner.main, full.main):
            with self.subTest(entry=entry):
                self.assertEqual(self.run_benchmark(entry), 0)
                paths = sorted(self.base.glob('tool_knowledge/workspace/user_task_*/tool_knowledge/*.json'))
                removed = paths[-1]; original = {p: p.read_bytes() for p in paths[:-1]}
                removed.unlink(); calls = len(self.executed)
                self.assertEqual(self.run_benchmark(entry, reuse=True), 0)
                self.assertEqual(len(self.executed), calls + 1)
                for p, data in original.items(): self.assertEqual(p.read_bytes(), data)
                failure = json.loads(paths[0].read_text()); self.assertFalse(failure['utility'])
                # A new name isolates the next scope, as full cannot reuse partial.
                if entry == runner.main:
                    self.root = self.root / 'full'; self.root.mkdir()

    def test_reuse_restores_four_attacks_and_rejects_new_typical_without_writes(self):
        self.assertEqual(self.run_benchmark(attack=OLD_ATTACKS), 0)
        previous = self.files(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True, attack=None, suites=None), 0)
        self.assertEqual(len(self.executed), calls)
        manifest = json.loads((self.base / 'attack_manifest.json').read_text())
        self.assertEqual(manifest['attacks'], OLD_ATTACKS)
        self.assertTrue(list((self.base / 'reuse').glob('*/snapshot/attack_manifest.json')))
        current = self.files()
        self.assertEqual(self.run_benchmark(reuse=True, attack='typical'), 1)
        self.assertEqual(self.files(), current)
        for path, data in previous.items():
            if path.name == 'run_manifest.json': self.assertEqual((self.base / path).read_bytes(), data)

    def test_later_suite_configuration_conflict_precedes_all_task_calls_and_writes(self):
        self.assertEqual(self.run_benchmark(suites=['workspace', 'travel']), 0)
        path = self.base / 'tool_knowledge/travel/run_manifest.json'
        value = json.loads(path.read_text()); value['profile'] = 'no-checker'
        path.write_text(json.dumps(value)); before = self.files(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True, suites=['workspace', 'travel']), 1)
        self.assertEqual(len(self.executed), calls)
        self.assertEqual(self.files(), before)

    def test_missing_root_plan_requires_explicit_attack_and_suites(self):
        self.assertEqual(self.run_benchmark(), 0)
        for name in ('benchmark_plan.json', 'attack_manifest.json', 'suite_manifest.json'):
            path = self.base / name
            if path.exists(): path.unlink()
        before = self.files(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True, attack=None, suites=None), 1)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.run_benchmark(reuse=True), 0)
        self.assertEqual(len(self.executed), calls)
        self.assertTrue((self.base / 'benchmark_plan.json').exists())

    def test_known_previous_source_is_accepted_without_changing_manifest(self):
        self.assertEqual(self.run_benchmark(), 0)
        fixture = json.loads((Path(__file__).with_name('fixtures') / 'benchmark_reuse_source_20261017.json').read_text())
        path = self.base / 'tool_knowledge/workspace/run_manifest.json'
        binding = json.loads(path.read_text()); binding['source'] = fixture
        path.write_text(json.dumps(binding)); original = path.read_bytes(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True), 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(self.executed), calls)
        binding['source']['source_sha256']['dscg/pipelines/defended.py'] = '0' * 64
        path.write_text(json.dumps(binding)); before = self.files()
        self.assertEqual(self.run_benchmark(reuse=True), 1)
        self.assertEqual(self.files(), before)

    def test_clean_reuse_rebuilds_missing_user_only(self):
        self.assertEqual(self.run_benchmark(run_attack=False), 0)
        path = sorted(self.base.glob('none/workspace/user_task_*/none/none.json'))[-1]
        path.unlink(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True, run_attack=False, attack=None), 0)
        self.assertEqual(len(self.executed), calls + 1)

    def test_native_accepted_error_cache_is_not_automatically_retried(self):
        self.assertEqual(self.run_benchmark(), 0)
        path = next(self.base.glob('tool_knowledge/workspace/user_task_*/tool_knowledge/*.json'))
        value = json.loads(path.read_text()); value['error'] = 'offline provider error'
        path.write_text(json.dumps(value)); before = path.read_bytes(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True), 0)
        self.assertEqual(len(self.executed), calls)
        self.assertEqual(path.read_bytes(), before)

    def test_native_incomplete_cache_is_preserved_before_task_reruns(self):
        self.assertEqual(self.run_benchmark(), 0)
        path = next(self.base.glob('tool_knowledge/workspace/user_task_*/tool_knowledge/*.json'))
        value = json.loads(path.read_text()); del value['utility']
        path.write_text(json.dumps(value)); before = path.read_bytes(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True), 0)
        self.assertEqual(len(self.executed), calls + 1)
        snapshot = next((self.base / 'reuse').glob('*/snapshot/' + path.relative_to(self.base).as_posix()))
        self.assertEqual(snapshot.read_bytes(), before)

    def test_corrupt_native_json_is_reported_without_retrying_or_replacing_it(self):
        self.assertEqual(self.run_benchmark(), 0)
        path = next(self.base.glob('tool_knowledge/workspace/user_task_*/tool_knowledge/*.json'))
        path.write_text('{'); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True), 1)
        self.assertEqual(path.read_text(), '{')
        self.assertEqual(len(self.executed), calls)

    def test_reuse_missing_directory_and_api_force_conflict_do_not_start_tasks(self):
        self.assertEqual(self.run_benchmark(reuse=True), 1)
        self.assertEqual(self.executed, [])
        self.assertFalse(self.base.exists())
        with self.assertRaises(ValueError): self.run_benchmark(reuse=True, force_rerun=True)

    def test_native_defense_change_is_rejected_before_cache_or_task_execution(self):
        self.assertEqual(self.run_benchmark(), 0)
        before = self.files(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True, defense='spotlighting_with_delimiting'), 1)
        self.assertEqual(self.executed.__len__(), calls)
        self.assertEqual(self.files(), before)

    def test_legacy_missing_defense_requires_explicit_existing_evidence(self):
        self.assertEqual(self.run_benchmark(), 0)
        path = self.base / 'tool_knowledge/workspace/run_manifest.json'
        binding = json.loads(path.read_text()); binding.pop('agentdojo_defense', None)
        binding['source'] = json.loads((Path(__file__).with_name('fixtures') / 'benchmark_reuse_source_20261017.json').read_text())
        path.write_text(json.dumps(binding)); summary_path = path.with_name('summary.json')
        summary = json.loads(summary_path.read_text()); summary['run_manifest'] = binding
        summary_path.write_text(json.dumps(summary)); original = path.read_bytes()
        self.assertEqual(self.run_benchmark(reuse=True), 0)
        self.assertEqual(path.read_bytes(), original)
        summary_path.unlink(); before = self.files(); calls = len(self.executed)
        self.assertEqual(self.run_benchmark(reuse=True), 1)
        self.assertEqual(len(self.executed), calls)
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
