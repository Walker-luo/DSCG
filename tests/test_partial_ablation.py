import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch
from experiments import run_partial_benchmark as runner
from experiments.common.partial_controls import make_task_manifest, select_tasks, validate_controls, guard_run

class PartialAblationTests(unittest.TestCase):
    def test_cli_controls_forwarded_and_clean_has_no_attack(self):
        with patch.object(runner,'main',return_value=0) as run,patch.dict(os.environ,{},clear=True):
            self.assertEqual(runner.cli(['--no-checker','--completion-prompt','--clean','--task-manifest','frozen.json']),0)
        self.assertFalse(run.call_args.kwargs['use_security_checker'])
        self.assertTrue(run.call_args.kwargs['completion_prompt'])
        self.assertFalse(run.call_args.kwargs['run_attack'])
        self.assertEqual(run.call_args.kwargs['task_manifest_path'],'frozen.json')
    def test_baseline_and_no_checker_reject_incompatible_controls(self):
        for flags in [dict(origin=True,audit_retries=1),dict(origin=True,completion_prompt=True),dict(origin=True,use_security_checker=False),dict(use_security_checker=False,audit_retries=1)]:
            with self.subTest(flags=flags),self.assertRaises(ValueError):validate_controls(**flags)
    def test_frozen_ids_are_used_or_error_never_silently_replaced(self):
        manifest={'suite_version':'v1.2','suites':{'s':{'user_task_ids':['u2'],'injection_task_ids':['i2']}}}
        self.assertEqual(select_tasks(manifest,'s',['u1','u2'],['i1','i2'],True,False),(['u2'],['i2']))
        self.assertEqual(select_tasks(manifest,'s',['u1','u2'],['i1','i2'],False,False),(['u2'],[]))
        for users,injections in [(['u1'],['i2']),(['u2'],['i1'])]:
            with self.assertRaises(ValueError):select_tasks(manifest,'s',users,injections,True,False)
        with self.assertRaises(ValueError):select_tasks(manifest,'s',['u2'],['i1','i2'],True,True)
    def test_manifest_export_is_offline_and_refuses_overwrite(self):
        with TemporaryDirectory() as directory,patch.object(runner,'main') as run,redirect_stdout(StringIO()):
            path=Path(directory)/'tasks.json'
            self.assertEqual(runner.cli(['--write-task-manifest',str(path)]),0)
            run.assert_not_called()
            manifest=json.loads(path.read_text());self.assertEqual(len(manifest['suites']),4)
            with self.assertRaises(SystemExit):runner.cli(['--write-task-manifest',str(path)])
    def test_cache_binding_rejects_other_configuration_even_force_rerun(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'manifest.json'
            guard_run(path,{'profile':'full'})
            guard_run(path,{'profile':'full'})
            with self.assertRaises(ValueError):guard_run(path,{'profile':'no-checker'})

class CachedCostTests(unittest.TestCase):
    def test_cached_invocation_preserves_cost_and_mixed_usage_is_explicit(self):
        from experiments.common.partial_controls import preserve_cached_cost
        with TemporaryDirectory() as directory:
            path=Path(directory)/'summary.json'
            old={'overhead':{'total_tokens':12},'api_accounting':{'main':{'generation':{'api_calls':1}}}}
            path.write_text(json.dumps(old))
            current={'overhead':{'total_tokens':0},'api_accounting':{'main':{}}}
            preserve_cached_cost(current,path,False)
            self.assertEqual(current['overhead']['total_tokens'],12)
            self.assertEqual(current['invocation_cost']['overhead']['total_tokens'],0)
            self.assertEqual(current['cost_scope'],'retained_previous_invocation')
            current={'overhead':{'total_tokens':3},'api_accounting':{'main':{'generation':{'api_calls':1}}}}
            preserve_cached_cost(current,path,False)
            self.assertEqual(current['overhead']['total_tokens'],3)
            self.assertEqual(current['cost_scope'],'new_api_calls_this_invocation')

class CleanDenominatorTests(unittest.TestCase):
    def test_no_attack_summary_has_no_security_denominator(self):
        from types import SimpleNamespace
        tracker=SimpleNamespace(total_prompt_tokens=0,total_completion_tokens=0,get_total_tokens=lambda:0)
        pipeline=SimpleNamespace(name='fixture',dscg_model_config={'model_id':'fixture'})
        results={'utility_results':{('user_task_0','none'):True},'security_results':{('user_task_0','none'):True}}
        with TemporaryDirectory() as directory,redirect_stdout(StringIO()),patch.object(runner,'make_openai_compatible_pipeline',return_value=(pipeline,tracker)),patch.object(runner.benchmark,'benchmark_suite_without_injections',return_value=results):
            runner.main(origin=True,run_attack=False,suites=['workspace'],run_name='clean',results_dir=directory)
            path=next(Path(directory).rglob('summary.json'))
            summary=json.loads(path.read_text())
            self.assertEqual(summary['task_counts']['attacked_tasks'],0)
            self.assertIsNone(summary['metrics']['attack_success_rate'])
            self.assertIsNone(summary['metrics']['defense_success_rate'])

class MissingSecuritySummaryTests(unittest.TestCase):
    def test_all_missing_security_never_prints_zero_asr_or_perfect_defense(self):
        from types import SimpleNamespace
        tracker=SimpleNamespace(total_prompt_tokens=0,total_completion_tokens=0,get_total_tokens=lambda:0)
        pipeline=SimpleNamespace(name='fixture',dscg_model_config={'model_id':'fixture'})
        results={'utility_results':{('user_task_0','injection_task_0'):True},'security_results':{}}
        with TemporaryDirectory() as directory,redirect_stdout(StringIO()),patch.object(runner,'make_openai_compatible_pipeline',return_value=(pipeline,tracker)),patch.object(runner.attacks,'load_attack',return_value=SimpleNamespace(is_dos_attack=False)),patch.object(runner.benchmark,'benchmark_suite_with_injections',return_value=results):
            runner.main(origin=True,suites=['workspace'],run_name='missing',results_dir=directory)
            summary=json.loads(next(Path(directory).rglob('summary.json')).read_text())
            report=next(Path(directory).rglob('report.txt')).read_text()
            self.assertIsNone(summary['metrics']['attack_success_rate'])
            self.assertNotIn('ASR): 0.00%',report)
            self.assertNotIn('Defense Rate): 100.00%',report)
