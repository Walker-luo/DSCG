"""Native cache and evidence remain in place across the backend-folder change."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_result_layout_integration')
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from baseintent.benchmark_catalog import get_backend, get_suites, get_suite
from experiments import run_partial_benchmark as partial, run_benchmark as full, run_injection_precheck as screen
from experiments.common import injection_cohort as cohort
import serial_fixture as fixture


class ResultLayoutIntegrationTests(unittest.TestCase):
    def temporary(self):
        root=Path(__file__).resolve().parents[1]/'artifacts/tests/test_result_layout_integration'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root);self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def files(self, base):
        return {p.relative_to(base):p.read_bytes() for p in base.rglob('*') if p.is_file()}

    def test_legacy_measurement_resumes_in_place_and_only_runs_missing_task(self):
        for entry in (partial.main,full.main):
            for clean in (True,False):
                with self.subTest(entry=entry,clean=clean), fixture.patched(), redirect_stdout(StringIO()) as output:
                    root=self.temporary();backend=get_backend().id;suite=get_suites()[0]
                    old=root/f'offline-model_{backend}_legacy'
                    options=dict(origin=True,suites=[suite],run_attack=not clean,attack='tool_knowledge',
                                 results_dir=root,run_name='legacy')
                    with patch.object(partial,'resolve_run_path',return_value=old):
                        self.assertEqual(entry(**options),0)
                    manifests={p:p.read_bytes() for p in old.glob('*/*/run_manifest.json')}
                    if not clean:
                        target=next(iter(get_suite('v1.2',suite).injection_tasks.values()))
                        attempts,rejected=screen._reuse(old,suite,target,cohort._binding(fixture.MAIN,[suite]))
                        self.assertEqual(len(attempts),1,rejected)
                        self.assertEqual(attempts[0]['origin'],'reused')
                    attack='none' if clean else 'tool_knowledge'
                    missing=next(old.glob(f'{attack}/{suite}/user_task_*/*/*.json'));missing.unlink()
                    calls=[]
                    def execute(*args,**kwargs):
                        calls.append(args[2].ID)
                        return fixture.execute(*args,**kwargs)
                    with patch.object(type(get_suite('v1.2',suite)),'run_task_with_pipeline',new=execute):
                        self.assertEqual(entry(**options,reuse=True),0,output.getvalue())
                    self.assertEqual(len(calls),1)
                    self.assertTrue(missing.is_file())
                    self.assertFalse((root/backend/'offline-model_legacy').exists())
                    for path,data in manifests.items():self.assertEqual(path.read_bytes(),data)
                    self.assertEqual(json.loads((old/'attack_manifest.json').read_text())['result_layout'],
                                     'model_run/attack/suite')

    def test_incomplete_or_conflicting_new_run_does_not_fall_back_to_legacy(self):
        root=self.temporary();backend=get_backend().id;suite=get_suites()[0]
        old=root/f'offline-model_{backend}_same';new=root/backend/'offline-model_same'
        options=dict(origin=True,suites=[suite],run_attack=False,run_name='same',results_dir=root)
        with fixture.patched(),redirect_stdout(StringIO()):
            with patch.object(partial,'resolve_run_path',return_value=old):
                self.assertEqual(partial.main(**options),0)
            original=self.files(old);new.mkdir(parents=True)
            with patch.object(partial,'make_openai_compatible_pipeline') as factory:
                self.assertEqual(partial.main(**options,reuse=True),1)
                factory.assert_not_called()
            self.assertEqual(self.files(old),original)
            self.assertEqual(partial.main(**options),0)  # A fresh default run uses the new location.
            path=next(new.glob('*/*/run_manifest.json'));value=json.loads(path.read_text())
            value['profile']='changed';path.write_text(json.dumps(value))
            before=self.files(new)
            with patch.object(partial,'make_openai_compatible_pipeline') as factory:
                self.assertEqual(partial.main(**options,reuse=True),1)
                factory.assert_not_called()
            self.assertEqual(self.files(new),before)
            self.assertEqual(self.files(old),original)

    def test_new_complete_run_is_preferred_and_default_name_has_no_backend_suffix(self):
        root=self.temporary();backend=get_backend().id;suite=get_suites()[0]
        old=root/f'offline-model_{backend}_same'
        options=dict(origin=True,suites=[suite],run_attack=False,run_name='same',results_dir=root)
        with fixture.patched(),redirect_stdout(StringIO()):
            with patch.object(partial,'resolve_run_path',return_value=old):
                self.assertEqual(partial.main(**options),0)
            original=self.files(old)
            self.assertEqual(partial.main(**options),0)
            new=root/backend/'offline-model_same'
            missing=next(new.glob('none/*/user_task_*/none/none.json'));missing.unlink()
            self.assertEqual(partial.main(**options,reuse=True),0)
            self.assertTrue(missing.exists());self.assertEqual(self.files(old),original)
            options.pop('run_name')
            self.assertEqual(partial.main(**options),0)
            self.assertTrue((root/backend/'offline-model/attack_manifest.json').exists())

    def test_legacy_screen_and_cohort_keep_absolute_evidence_and_resume_in_place(self):
        root=self.temporary();backend=get_backend().id;name=get_suites()[0]
        old=root/f'offline-model_{backend}_screen'
        with fixture.patched(),redirect_stdout(StringIO()),\
             patch.object(screen,'resolve_model_config',return_value=fixture.MAIN),\
             patch.object(screen,'make_openai_compatible_pipeline',side_effect=fixture.baseline),\
             patch.object(cohort,'resolve_model_config',side_effect=fixture.resolve):
            with patch.object(screen,'resolve_run_path',return_value=old):
                self.assertEqual(screen.screen(config_path=None,run_name='screen',suites=[name],results_dir=root),0)
            evidence={p:p.read_bytes() for p in [old/'cohort.json',old/'screen_manifest.json',*old.rglob('attempt.json')]}
            with patch.object(screen,'make_openai_compatible_pipeline',side_effect=AssertionError('goal repeated')):
                self.assertEqual(screen.screen(config_path=None,run_name='screen',suites=[name],results_dir=root),0)
            self.assertFalse((root/backend/'offline-model_screen').exists())
            # Legacy cohort can drive a new measurement layout without rewriting any evidence.
            options=dict(cohort_path=old/'cohort.json',origin=True,suites=[name],attack='tool_knowledge',
                         results_dir=root,run_name='screened')
            for entry in (partial.main,full.main):
                options['run_name']='partial_screened' if entry is partial.main else 'full_screened'
                self.assertEqual(entry(**options),0)
                self.assertTrue((root/backend/f"offline-model_{options['run_name']}"/'screened_cohort.json').exists())
            # Existing legacy screened measurements also resume in their own directory.
            legacy_measure=root/f'offline-model_{backend}_legacy_screened'
            options['run_name']='legacy_screened'
            with patch.object(cohort,'resolve_run_path',return_value=legacy_measure),\
                 patch.object(partial,'resolve_run_path',return_value=legacy_measure):
                self.assertEqual(partial.main(**options),0)
            bindings={p:p.read_bytes() for p in legacy_measure.glob('*/*/run_manifest.json')}
            self.assertEqual(partial.main(**options,reuse=True),0)
            self.assertFalse((root/backend/'offline-model_legacy_screened').exists())
            for path,data in bindings.items():self.assertEqual(path.read_bytes(),data)
            for path,data in evidence.items():self.assertEqual(path.read_bytes(),data)
            # An incomplete new screen blocks fallback to the valid old screen.
            new=root/backend/'offline-model_screen';new.mkdir()
            with self.assertRaisesRegex(ValueError,'binding'):
                screen.screen(config_path=None,run_name='screen',suites=[name],results_dir=root)
            for path,data in evidence.items():self.assertEqual(path.read_bytes(),data)
