"""CLI accounting and real spawn isolation; all model responses are local fixtures."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dscg.benchmark_catalog import get_backend,get_suites
from experiments import run_partial_benchmark as runner,run_benchmark as full
from experiments.common.attack_execution import iter_attack_results,iter_serial_results
import tool_arguments_fixture as fixture


def spawned(jobs,*,on_event):return iter_attack_results(jobs,on_event=on_event,execute=fixture.execute)
def inline(jobs,*,on_event):return iter_serial_results(jobs,on_event=on_event,execute=fixture.execute)


class ToolArgumentsRunnerTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261030_fliter_goal_impl/tool_arguments_runner'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root);self.addCleanup(temp.cleanup);self.root=Path(temp.name)

    def base(self,name):return self.root/get_backend().id/('gpt-4o-2024-05-13_'+name)

    def test_progress_and_attack_parallel_keep_error_denominators_tokens_and_reuse(self):
        attacks=['ignore_previous','important_instructions'];suite=get_suites()[0]
        for origin in (True,False):
            comparisons=[]
            for progress,dispatch in [(False,inline),(True,spawned)]:
                name=f'{origin}_{progress}'
                options=dict(origin=origin,suites=[suite],attack=attacks,results_dir=self.root,run_name=name,progress=progress)
                with self.subTest(origin=origin,progress=progress),fixture.patched(), \
                     patch.object(runner,'iter_attack_results',side_effect=dispatch),redirect_stdout(StringIO()) as output:
                    self.assertEqual(runner.main(**options),1,output.getvalue())
                base=self.base(name)
                self.assertTrue(all((base/a/suite/'summary.json').exists() for a in attacks),output.getvalue())
                summaries=[json.loads((base/a/suite/'summary.json').read_text()) for a in attacks]
                for data in summaries:
                    self.assertEqual(data['task_counts']['total_tasks'],9)
                    self.assertEqual(data['task_counts']['execution_errors'],1)
                    self.assertEqual(data['task_counts']['utility_valid'],8)
                    self.assertEqual(data['task_counts']['attacked_tasks'],8)
                    self.assertEqual(data['task_error_diagnostics'][0]['stage'],'scored_task')
                comparisons.append([{k:d[k] for k in ['metrics','task_counts','overhead','api_accounting']} for d in summaries])
                cases=[json.loads(l) for l in (base/'failure_cases.jsonl').read_text().splitlines()]
                errors=[c for c in cases if 'tool_arguments_error' in c]
                self.assertEqual(len(errors),2)
                for error in errors:
                    self.assertIsNone(error['utility_success']);self.assertIsNone(error['attack_success'])
                    self.assertNotIn('tsr_failure',error['failure_types'])
                self.assertNotIn('private-json-probe',(base/'summary.md').read_text())
                manifest=json.loads((base/'run_manifest.json').read_text())
                self.assertEqual(manifest['task_layout'],'flat-v1')
                self.assertFalse((base/'attack_manifest.json').exists())
                execution=json.loads(next((base/'execution').glob('*/execution.json')).read_text())
                self.assertEqual(execution['status'],'error')
                self.assertTrue(all(g['task_errors']==1 for g in execution['groups']))
                if progress:self.assertIn('任务 9/9',output.getvalue())
                # Native incomplete traces are snapshotted before explicit reuse fills them.
                paths=list(base.glob('*/*/user_task_*/*.json'))
                incomplete={p:p.read_bytes() for p in paths if 'utility' not in json.loads(p.read_text())}
                before={p:p.read_bytes() for p in base.glob('*/*/task_errors.jsonl')}
                with fixture.patched(),patch.object(runner,'iter_attack_results',side_effect=dispatch),redirect_stdout(StringIO()):
                    self.assertEqual(runner.main(**options,reuse=True),0)
                for p,data in before.items():self.assertEqual(p.read_bytes(),data)
                for p,data in incomplete.items():
                    archived=list((base/'reuse').glob('*/snapshot/'+str(p.relative_to(base))))
                    self.assertTrue(any(p.read_bytes()==data for p in archived))
                for data in [json.loads((base/a/suite/'summary.json').read_text()) for a in attacks]:
                    self.assertEqual(data['task_counts']['execution_errors'],0)
            # Latency is deliberately excluded from API-accounting comparisons.
            for a,b in zip(*comparisons):
                self.assertEqual(a['metrics'],b['metrics']);self.assertEqual(a['task_counts'],b['task_counts'])
                self.assertEqual(a['overhead'],b['overhead'])

    def test_explicit_goal_errors_and_failures_are_separate_and_prune_targets(self):
        suite=get_suites()[0]
        bad_token=fixture._BAD_AT.set(1)
        try:
            with fixture.patched(),patch.object(runner,'iter_attack_results',side_effect=inline),redirect_stdout(StringIO()):
                self.assertEqual(runner.main(origin=True,suites=[suite],attack='ignore_previous',
                    results_dir=self.root,run_name='goal',goal=True),1)
        finally:
            fixture._BAD_AT.reset(bad_token)
        base=self.base('goal')
        root=json.loads((base/'summary.json').read_text())
        checks=root['selection_report']['goal_checks']
        self.assertEqual(len(checks),3)
        self.assertEqual(checks[0]['status'],'error')
        self.assertEqual(checks[0]['error_code'],'MODEL_TOOL_ARGUMENTS_INVALID_JSON')
        self.assertTrue(all(check['status'] in {'failed','error'} for check in checks))
        self.assertEqual(root['selection_report']['targets_retained'],0)
        data=json.loads((base/'ignore_previous'/suite/'summary.json').read_text())
        self.assertEqual(data['task_counts']['total_tasks'],0)
        self.assertEqual(data['task_counts']['utility_valid'],0)
        self.assertEqual(data['task_counts']['execution_errors'],0)
        self.assertIsNone(data['metrics']['utility_rate'])
        self.assertIsNone(data['metrics']['attack_success_rate'])
        self.assertNotIn('private-json-probe',(base/'summary.md').read_text())

    def test_spawn_preserves_fliter_and_goal_retained_subset(self):
        from agentdojo import logging
        from dscg.benchmark_catalog import get_suite
        from experiments.common.injection_filter import SCHEMA, benchmark_header
        suite_name=get_suites()[0];suite=get_suite('v1.2',suite_name)
        targets=list(suite.injection_tasks)[:3]
        path=self.root/'spawn_fliter.json'
        path.write_text(json.dumps({'schema_version':SCHEMA,'benchmark':benchmark_header(),
                                    'excluded':{suite_name:[targets[2]]}}))
        goal_calls=[]
        def native_goal(pipeline,task,**kwargs):
            goal_calls.append(task.ID)
            logging.Logger.get().log([{'role':'assistant','content':[{'type':'text','text':'offline GOAL fixture'}]}])
            return task.ID==targets[0],True
        goal_suite=SimpleNamespace(name=suite_name,get_injection_task_by_id=suite.get_injection_task_by_id,
                                   run_task_with_pipeline=native_goal)
        attacks=['ignore_previous','important_instructions']
        with fixture.patched(),patch('experiments.common.goal_stage.get_suite',return_value=goal_suite), \
             patch.object(runner,'iter_attack_results',side_effect=spawned),redirect_stdout(StringIO()) as output:
            status=runner.main(origin=True,suites=[suite_name],attack=attacks,results_dir=self.root,
                run_name='spawn_subset',fliter_path=path,goal=True)
        self.assertEqual(status,1,output.getvalue())  # One authored malformed scored response per attack.
        self.assertEqual(goal_calls,targets[:2])
        base=self.base('spawn_subset')
        for attack in attacks:
            data=json.loads((base/attack/suite_name/'summary.json').read_text())
            self.assertEqual(data['task_selection']['injection_task_ids'],targets[:1])
            self.assertEqual(data['task_counts']['total_tasks'],3)
            self.assertEqual(data['task_counts']['utility_valid'],2)
            self.assertEqual(data['task_counts']['execution_errors'],1)
            traces=list((base/attack/suite_name).glob('user_task_*/*.json'))
            self.assertEqual(len(traces),3)
            self.assertTrue(all(trace.name==targets[0]+'.json' for trace in traces))
        root=json.loads((base/'summary.json').read_text())
        self.assertEqual([check['status'] for check in root['selection_report']['goal_checks']],['passed','failed'])

    def test_clean_and_dos_errors_have_null_labels_and_correct_denominators(self):
        from agentdojo.attacks.attack_registry import ATTACKS
        dos=next(name for name,attack in ATTACKS.items() if attack.is_dos_attack)
        suite=get_suites()[0]
        for attack,run_attack,name in [('ignore_previous',False,'clean'),(dos,True,'dos')]:
            with self.subTest(mode=name),fixture.patched(),patch.object(runner,'iter_attack_results',side_effect=inline),redirect_stdout(StringIO()):
                self.assertEqual(runner.main(origin=True,suites=[suite],attack=attack,run_attack=run_attack,results_dir=self.root,run_name=name),1)
            data=json.loads((self.base(name)/(attack if run_attack else 'none')/suite/'summary.json').read_text())
            self.assertEqual(data['task_counts']['total_tasks'],3)
            self.assertEqual(data['task_counts']['execution_errors'],1)
            self.assertEqual(data['task_counts']['utility_valid'],2)
            self.assertEqual(data['task_counts']['attacked_tasks'],2 if run_attack else 0)
            self.assertEqual(data['task_error_diagnostics'][0]['stage'],'scored_task' if run_attack else 'clean_task')

    def test_full_and_fliter_use_the_same_task_error_policy(self):
        from dscg.benchmark_catalog import get_suite
        from experiments.common.injection_filter import SCHEMA, benchmark_header
        suite_name=get_suites()[0];suite=get_suite('v1.2',suite_name)
        targets=list(suite.injection_tasks)
        exclusions=targets[1:3]
        path=self.root/'fliter.json'
        path.write_text(json.dumps({'schema_version':SCHEMA,'benchmark':benchmark_header(),
                                    'excluded':{suite_name:exclusions}}))
        cases=[(full.main,'full',None),(full.main,'full_fliter',path),(runner.main,'partial_fliter',path)]
        for entry,name,path in cases:
            with self.subTest(scope=name),fixture.patched(), \
                 patch.object(runner,'iter_attack_results',side_effect=inline),redirect_stdout(StringIO()) as output:
                status=entry(origin=True,suites=[suite_name],attack='ignore_previous',results_dir=self.root,
                             run_name=name,fliter_path=path)
            self.assertEqual(status,1,output.getvalue())
            data=json.loads((self.base(name)/'ignore_previous'/suite_name/'summary.json').read_text())
            users=len(suite.user_tasks) if name.startswith('full') else 3
            target_count=len(targets) if name=='full' else len(targets)-len(exclusions) if name=='full_fliter' else 1
            self.assertEqual(data['task_counts']['total_tasks'],users*target_count)
            self.assertEqual(data['task_counts']['utility_valid'],users*target_count-1)
            self.assertEqual(data['task_counts']['execution_errors'],1)
            errors=data['task_error_diagnostics']
            self.assertEqual(errors[0]['stage'],'scored_task')
            root=json.loads((self.base(name)/'summary.json').read_text())
            self.assertEqual(root['selection_report']['goal_checks'],[])
            self.assertFalse((self.base(name)/'goal').exists())
