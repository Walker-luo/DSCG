"""CLI accounting and real spawn isolation; all model responses are local fixtures."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
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
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261021_tool_arguments_json/runner'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root);self.addCleanup(temp.cleanup);self.root=Path(temp.name)

    def base(self,name):return self.root/get_backend().id/('gpt-4o-2024-05-13_'+name)

    def test_progress_and_attack_parallel_keep_error_denominators_tokens_and_reuse(self):
        attacks=['ignore_previous','important_instructions'];suite=get_suites()[0]
        for origin in (True,False):
            comparisons=[]
            for progress,dispatch in [(False,inline),(True,spawned)]:
                name=f'{origin}_{progress}'
                options=dict(prompt_profile='legacy-v34',origin=origin,suites=[suite],attack=attacks,results_dir=self.root,run_name=name,progress=progress)
                with self.subTest(origin=origin,progress=progress),fixture.patched(), \
                     patch.object(runner,'iter_attack_results',side_effect=dispatch),redirect_stdout(StringIO()) as output:
                    self.assertEqual(runner.main(**options),1,output.getvalue())
                base=self.base(name)
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
                manifest=json.loads((base/'attack_manifest.json').read_text())
                self.assertEqual(manifest['execution']['status'],'error')
                self.assertTrue(all(g['task_errors']==1 for g in manifest['execution']['groups']))
                if progress:self.assertIn('任务 9/9',output.getvalue())
                # Native incomplete traces are snapshotted before explicit reuse fills them.
                paths=list(base.glob('*/*/user_task_*/*/*.json'))
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

    def test_goal_errors_are_separate_and_do_not_prune_attack_targets(self):
        def schedule(jobs,*,on_event):
            return iter_serial_results([{**job,'fixture_goal_error':True} for job in jobs],on_event=on_event,execute=fixture.execute)
        with fixture.patched(),patch.object(runner,'iter_attack_results',side_effect=schedule),redirect_stdout(StringIO()):
            self.assertEqual(runner.main(origin=True,suites=[get_suites()[0]],attack='ignore_previous',results_dir=self.root,run_name='goal'),1)
        base=self.base('goal');data=json.loads((base/'ignore_previous'/get_suites()[0]/'summary.json').read_text())
        self.assertEqual(data['task_counts']['total_tasks'],9)
        self.assertEqual(data['task_counts']['utility_valid'],9)
        self.assertEqual(data['task_counts']['goal_preflight_errors'],1)
        self.assertEqual(data['task_counts']['execution_errors'],0)
        cases=[json.loads(l) for l in (base/'failure_cases.jsonl').read_text().splitlines()]
        self.assertEqual(len([c for c in cases if c.get('phase')=='goal_preflight']),1)
        self.assertIn('GOAL预检错误=1',(base/'summary.md').read_text())

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

    def test_full_and_cohort_use_the_same_task_error_policy(self):
        from dscg.benchmark_catalog import get_suite,benchmark_identity
        from experiments.common import injection_cohort as cohort
        suite_name=get_suites()[0];suite=get_suite('v1.2',suite_name)
        frozen={'schema_version':cohort.SCHEMA,'suite_version':'v1.2','benchmark':benchmark_identity(),
                'selection_rule':cohort.RULE,'binding':{'benchmark':benchmark_identity(),'main_model':fixture.CONFIG.public_dict()},
                'suites':{suite_name:{'user_task_ids':list(suite.user_tasks),'injection_task_ids':list(suite.injection_tasks)[:1]+list(suite.injection_tasks)[3:4]}}}
        frozen['cohort_sha256']=cohort._digest(frozen)
        path=self.root/'frozen/cohort.json';path.parent.mkdir();path.write_text(json.dumps(frozen))
        cases=[(full.main,'full',None),(full.main,'full_cohort',path),(runner.main,'partial_cohort',path)]
        for entry,name,path in cases:
            with self.subTest(scope=name),fixture.patched(), \
                 patch.object(cohort,'resolve_model_config',return_value=fixture.CONFIG), \
                 patch.object(runner,'iter_attack_results',side_effect=inline),redirect_stdout(StringIO()) as output:
                self.assertEqual(entry(origin=True,suites=[suite_name],attack='ignore_previous',results_dir=self.root,run_name=name,cohort_path=path),1,output.getvalue())
            data=json.loads((self.base(name)/'ignore_previous'/suite_name/'summary.json').read_text())
            users=len(suite.user_tasks) if name.startswith('full') else 3
            targets=len(suite.injection_tasks) if name=='full' else 2 if name=='full_cohort' else 1
            self.assertEqual(data['task_counts']['total_tasks'],users*targets)
            self.assertEqual(data['task_counts']['utility_valid'],users*targets-1)
            self.assertEqual(data['task_counts']['execution_errors'],1)
