"""Offline end-to-end runner selection tests; factories never create API clients."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo import logging
from experiments import run_partial_benchmark as runner
from experiments.common.attack_execution import iter_serial_results
from experiments.common.injection_filter import SCHEMA, benchmark_header


class Tracker:
    total_prompt_tokens = total_completion_tokens = 0
    def snapshot(self): return {}
    def get_total_tokens(self): return 0


class FliterRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        available = runner.get_backend().suites
        self.suite_name = 'banking' if 'banking' in available else available[0]
        self.goals, self.scored, self.configurations = [], [], []
        self.fail_goals = set()
        self.goal_errors = {}
        self.interrupt_goal = None
        self.users = {f'user_task_{n}': SimpleNamespace(ID=f'user_task_{n}', PROMPT='fixture') for n in range(5)}
        self.targets = {f'injection_task_{n}': SimpleNamespace(ID=f'injection_task_{n}', GOAL='fixture') for n in range(5)}
        self.suite = SimpleNamespace(name=self.suite_name, user_tasks=self.users, injection_tasks=self.targets,
            get_injection_task_by_id=lambda key: self.targets[key], run_task_with_pipeline=self.native_goal)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.stack.enter_context(redirect_stderr(io.StringIO()))
        patches = {
            'get_suite': lambda *args: self.suite,
            '_describe_pipeline': lambda *args, **kwargs: self.pipeline(),
            '_configured_pipeline': self.configure,
            'check_attack_compatibility': lambda *args: None,
            'ensure_native_cache_model_ready': lambda: None,
            'run_suite_with_progress': self.score,
            'iter_attack_results': lambda jobs, on_event: iter_serial_results(jobs, on_event=on_event),
            'resolve_model_config': lambda *args, **kwargs: SimpleNamespace(model_id='qwen3.7-flash'),
        }
        for name, value in patches.items():
            self.stack.enter_context(patch.object(runner, name, value))
        self.stack.enter_context(patch('experiments.common.goal_stage.get_suite', return_value=self.suite))
        self.stack.enter_context(patch.object(runner.attacks, 'load_attack',
            side_effect=lambda name, suite, pipeline: SimpleNamespace(name=name, is_dos_attack=False)))

    def pipeline(self):
        return SimpleNamespace(name='qwen3.7-flash', dscg_model_config={'model_id':'qwen3.7-flash'},
            dscg_security_model_config={}, dscg_optimization_config={})

    def configure(self, options, metadata):
        self.configurations.append((dict(options), metadata))
        return self.pipeline(), Tracker(), None

    def native_goal(self, pipeline, task, **kwargs):
        self.goals.append(task.ID)
        logging.Logger.get().log([{'role':'assistant','content':[{'type':'text','text':'fixture'}]}])
        if task.ID == self.interrupt_goal:
            self.interrupt_goal = None
            raise KeyboardInterrupt()
        if task.ID in self.goal_errors:
            raise self.goal_errors[task.ID]
        return task.ID not in self.fail_goals, True

    def score(self, pipeline, suite, attack, logdir, force_rerun, **kwargs):
        self.scored.append((list(kwargs['user_tasks']), list(kwargs['injection_tasks'])))
        keys = [(user, target) for user in kwargs['user_tasks'] for target in kwargs['injection_tasks']]
        return {'utility_results':dict.fromkeys(keys, True), 'security_results':dict.fromkeys(keys, False)}

    def fliter(self, targets):
        path = self.root/'fliter.json'
        path.write_text(json.dumps({'schema_version':SCHEMA,'benchmark':benchmark_header(),
                                    'excluded':{self.suite_name:targets}}))
        return path

    def execute(self, **options):
        return runner.main(model_id='qwen3.7-flash', suites=[self.suite_name], origin=True,
            results_dir=self.root/'results', run_name='fixture', attack='important_instructions', **options)

    def test_four_combinations_and_no_backfill(self):
        for filtered, goal in ((False,False),(True,False),(False,True),(True,True)):
            with self.subTest(filtered=filtered, goal=goal):
                self.goals.clear(); self.scored.clear()
                name = f'combo_{filtered}_{goal}'
                status = runner.main(model_id='qwen3.7-flash', suites=[self.suite_name], origin=True,
                    results_dir=self.root/'results', run_name=name, attack='important_instructions',
                    fliter_path=self.fliter(['injection_task_0']) if filtered else None, goal=goal)
                expected = ['injection_task_1','injection_task_2'] if filtered else ['injection_task_0','injection_task_1','injection_task_2']
                self.assertEqual(status, 0)
                self.assertEqual(self.goals, expected if goal else [])
                self.assertEqual(self.scored, [(['user_task_0','user_task_1','user_task_2'],expected)])

    def test_failed_goals_removed_from_every_attack_without_backfill(self):
        self.fail_goals.add('injection_task_1')
        status = runner.main(model_id='qwen3.7-flash', suites=[self.suite_name], origin=True,
            results_dir=self.root/'results', run_name='fixture', attack=['important_instructions','ignore_previous'], goal=True)
        self.assertEqual(status, 0)
        self.assertEqual(self.goals, ['injection_task_0','injection_task_1','injection_task_2'])
        self.assertEqual([targets for _,targets in self.scored], [['injection_task_0','injection_task_2']]*2)

    def test_all_excluded_runs_no_goal_or_scored_cases(self):
        self.execute(fliter_path=self.fliter(['injection_task_0','injection_task_1','injection_task_2']), goal=True)
        self.assertEqual(self.goals, [])
        self.assertTrue(all(not targets for _,targets in self.scored))
        summaries = list((self.root/'results').glob('*/*/summary.json'))
        self.assertEqual(json.loads(summaries[0].read_text())['selection_report']['targets_retained'],0)

    def test_checkpoint_resume_does_not_retry_interrupted_goal(self):
        self.interrupt_goal = 'injection_task_1'
        self.assertEqual(self.execute(goal=True),130)
        self.assertEqual(self.goals,['injection_task_0','injection_task_1'])
        self.assertEqual(self.scored,[])
        self.assertEqual(self.execute(goal=True,reuse=True),1)
        self.assertEqual(self.goals,['injection_task_0','injection_task_1','injection_task_2'])
        self.assertEqual(self.scored[0][1],['injection_task_0','injection_task_2'])

    def test_goal_and_measurement_receive_same_configuration(self):
        self.assertEqual(self.execute(goal=True,trace_level='full',l1_projection_mode='shadow'),0)
        goal, measurement = self.configurations
        keys = ('model_id','sec_model_id','origin','defense','trace_level','use_sandbox',
                'use_security_checker','audit_retries','completion_prompt','audit_router_mode',
                'planning_tool_view','delegated_tasks','l1_projection_mode','prompt_profile')
        self.assertEqual({key:goal[0][key] for key in keys},{key:measurement[0][key] for key in keys})
        self.assertEqual(goal[1],measurement[1])

    def test_defended_goal_and_measurement_share_metadata_and_options(self):
        metadata = {'fixture': {'effect': 'read'}}
        selection = SimpleNamespace(path=self.root/'metadata.toml', public_dict=lambda: {'path':'fixture','source':'fixture'})
        with patch.object(runner,'resolve_tool_metadata',return_value=selection), \
             patch.object(runner,'validate_benchmark_tool_metadata'), \
             patch.object(runner,'load_tool_metadata',return_value=metadata):
            status = runner.main(model_id='qwen3.7-flash',sec_model_id='qwen3.7-flash',suites=[self.suite_name],
                results_dir=self.root/'results',run_name='defended',attack='important_instructions',
                goal=True,prompt_profile='static-task-v354',audit_router_mode='off',
                planning_tool_view=False,delegated_tasks=False,l1_projection_mode='shadow')
        self.assertEqual(status,0)
        goal, measurement = self.configurations
        keys = ('model_id','sec_model_id','origin','defense','trace_level','use_sandbox',
                'use_security_checker','audit_retries','completion_prompt','audit_router_mode',
                'planning_tool_view','delegated_tasks','l1_projection_mode','prompt_profile')
        self.assertEqual({key:goal[0][key] for key in keys},{key:measurement[0][key] for key in keys})
        self.assertIs(goal[1],metadata)
        self.assertIs(measurement[1],metadata)

    def test_reuse_with_changed_goal_option_rejects_before_factory(self):
        self.assertEqual(self.execute(),0)
        self.configurations.clear(); self.scored.clear()
        self.assertEqual(self.execute(goal=True,reuse=True),1)
        self.assertEqual(self.configurations,[])
        self.assertEqual(self.goals,[])
        self.assertEqual(self.scored,[])

    def test_compatibility_recomputed_after_goal_removes_unsupported_target(self):
        self.fail_goals.add('injection_task_1')
        def compatibility(suite, attack, users, targets):
            if attack == 'tool_knowledge' and 'injection_task_1' in targets:
                return {'reason_code':'missing_placeholder_args','injection_task_ids':['injection_task_1'],
                        'planned_pairs':len(users)*len(targets)}
        with patch.object(runner,'check_attack_compatibility',side_effect=compatibility):
            status = runner.main(model_id='qwen3.7-flash',suites=[self.suite_name],origin=True,
                results_dir=self.root/'results',run_name='compatibility',attack='tool_knowledge',goal=True)
        self.assertEqual(status,0)
        self.assertEqual([targets for _,targets in self.scored],[['injection_task_0','injection_task_2']])

    def test_malformed_goal_arguments_are_errors_and_never_scored(self):
        self.goal_errors['injection_task_1'] = json.JSONDecodeError('fixture','{',1)
        self.assertEqual(self.execute(goal=True),1)
        self.assertEqual(self.scored[0][1],['injection_task_0','injection_task_2'])
        summary_path = next((self.root/'results').glob('*/*/summary.json'))
        summary = json.loads(summary_path.read_text())
        checks = summary['selection_report']['goal_checks']
        failed = next(c for c in checks if c['injection_task_id']=='injection_task_1')
        self.assertEqual(failed['status'],'error')
        # AgentDyn catches JSONDecodeError itself; both paths stay infrastructure errors.
        self.assertIn(failed['error_code'],('MODEL_TOOL_ARGUMENTS_INVALID_JSON','GOAL_TRACE_ERROR'))
        self.assertEqual(summary['suite_reports'][0]['summary']['task_counts']['total_tasks'],6)
        self.assertEqual(summary['suite_reports'][0]['summary']['task_counts']['utility_valid'],6)
        self.assertFalse(any((self.root/'results').rglob('*.dscg.responses.jsonl')))

    def test_clean_and_dos_reject_selection_flags_before_factory(self):
        for options in ({'run_attack':False,'goal':True},{'run_attack':False,'fliter_path':self.fliter([])}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.execute(**options)
        dos = next(name for name, cls in runner.ATTACKS.items() if cls.is_dos_attack)
        with self.assertRaises(ValueError):
            runner.main(model_id='qwen3.7-flash', suites=[self.suite_name], origin=True,
                results_dir=self.root/'results',run_name='dos',attack=dos,goal=True)
        self.assertEqual(self.configurations,[])

    def test_old_flags_rejected_at_cli(self):
        for flag in ('--cohort','--screened','--screen-reuse'):
            with self.subTest(flag=flag), self.assertRaises(SystemExit) as exc:
                runner.cli([flag,'old.json'])
            self.assertEqual(exc.exception.code,2)


if __name__ == '__main__': unittest.main()
