
from artifact_support import ensure_artifacts
ensure_artifacts('test_task_alignment')
from tests.authorization_fixture import adapt_client
"""Opt-in compact candidate plumbing and strict boundaries; no model efficacy claims."""
import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from tests.test_partial_agentdyn import legacy_suite_dispatch
from unittest.mock import Mock, patch

from agentdojo.functions_runtime import FunctionCall, EmptyEnv
from baseintent.pipelines import defended as d
from baseintent import prompt_profiles as profiles
from experiments.diagnostics.utility_stages import synthetic_runtime, build_stage, compare_stage

PROFILE = 'task-alignment-v1'


def model(text):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=text, refusal=None), finish_reason='stop')])
    adapt_client(client)
    return SimpleNamespace(name='offline', client=client)


class TaskAlignmentTests(unittest.TestCase):
    def test_compact_candidate_preserves_catalog_and_single_authorization_request(self):
        runtime = synthetic_runtime('slack')
        request = d.TrustedTaskRequest('Read the page and send its summary to the team channel; do not edit the page.')
        catalogs, prompts = {}, {}
        for name in ('legacy-v34',PROFILE):
            llm=model('{"tools":["send_channel_message"]}')
            grant=d.ToolAuthorizationCompiler(llm,prompt_profile=name).compile(request,runtime)
            self.assertIn('send_channel_message',grant.allowed_tools)
            self.assertNotIn('post_webpage',grant.allowed_tools)
            self.assertNotIn('send_direct_message',grant.allowed_tools)
            llm.client.chat.completions.create.assert_called_once()
            kwargs=llm.client.chat.completions.create.call_args.kwargs
            catalogs[name]=json.loads(kwargs['messages'][1]['content'])
            prompts[name]=kwargs['messages'][0]['content']
        self.assertIsInstance(catalogs['legacy-v34']['available_tools']['send_channel_message'],dict)
        self.assertIsInstance(catalogs[PROFILE]['available_tools']['send_channel_message'],str)
        self.assertIn('parameters',catalogs['legacy-v34']['available_tools']['send_channel_message'])
        self.assertNotEqual(prompts['legacy-v34'],prompts[PROFILE])
        # The new default is shorter; this historical candidate keeps its own budget.
        self.assertLessEqual(len(prompts[PROFILE]),1084)
        self.assertFalse(profiles.semantic_catalog(PROFILE))

    def test_candidate_does_not_replace_bounded_authorization_contract(self):
        from baseintent.l2_authorization import ToolAuthorizationProfile
        policy=profiles.authorization_policy(d.ToolAuthorizationCompiler.PROFILE_POLICY,PROFILE,bounded=True)
        self.assertIn('prohibited_tools',policy)
        self.assertIn('literal evidence span',policy)
        self.assertNotEqual(policy,profiles.authorization_policy(d.ToolAuthorizationCompiler.SYSTEM_POLICY,PROFILE))
        request='Send Mira a message'
        host_profile=ToolAuthorizationProfile('fixture',(request,),frozenset({'send_direct_message'}))
        llm=model(json.dumps({'tools':['send_direct_message'],'prohibited_tools':[],
                             'evidence':[{'tool':'send_direct_message','kind':'direct','span':request}]}))
        grant=d.ToolAuthorizationCompiler(llm,authorization_profile=host_profile,prompt_profile=PROFILE).compile(
            d.TrustedTaskRequest(request),synthetic_runtime('slack'))
        self.assertEqual(grant.profile_status,'applied')
        self.assertEqual(llm.client.chat.completions.create.call_args.kwargs['messages'][0]['content'],policy)

    def test_audit_candidate_is_compact_and_schema_failures_still_block(self):
        for payload,expected in [
            ('{"decision":"allow","violations":[],"confidence":0.9,"reason_code":"ALIGNED"}','allow'),
            ('{"decision":"deny","violations":["OFF_TASK"],"confidence":1,"reason_code":"OFF_TASK"}','deny'),
            ('{"decision":"abstain","violations":["MISSING"],"confidence":0,"reason_code":"MISSING"}','deny'),
            ('{"decision":"allow","violations":[]}','deny'),
            ('{"decision":"allow","violations":[],"confidence":1,"reason_code":"bad code"}','deny')]:
            with self.subTest(payload=payload):
                llm=model(payload);runtime=synthetic_runtime('slack')
                sandbox=d.PermissionSandbox(['send_direct_message'])
                checker=d.ActionSecurityChecker(llm,sandbox=sandbox,prompt_profile=PROFILE)
                call=FunctionCall(function='send_direct_message',args={'recipient':'Mira','body':'Requested summary'},id='send')
                state=checker.query('Send Mira the summary',runtime,EmptyEnv(),[
                    {'role':'user','content':[{'type':'text','content':'Send Mira the summary'}]},
                    {'role':'assistant','content':[],'tool_calls':[call]}],{})
                state=d.ReferenceMonitor(sandbox,True).query(*state)
                record=state[-1]['baseintent_audit_decisions'][-1]
                self.assertEqual(record['final_policy_decision'],expected)
                llm.client.chat.completions.create.assert_called_once()
                self.assertLessEqual(len(checker.SYSTEM_POLICY),1919)
                self.assertNotIn(profiles.PROTOCOL_RULE,checker.SYSTEM_POLICY)

    def test_entrypoints_and_cache_identity_include_candidate(self):
        from experiments import run_benchmark as full, run_partial_benchmark as partial
        from experiments.common import injection_cohort
        from dashboard.evaluation import normalize_config
        from baseintent.benchmark_catalog import get_suites
        from experiments.common.benchmark_reuse import _compatible_binding
        for module in (full,partial):
            with patch.object(partial,'main',return_value=0) as run:
                self.assertEqual(module.cli(['--clean','--suites',get_suites()[0],'--prompt-profile',PROFILE]),0)
                self.assertEqual(run.call_args.kwargs['prompt_profile'],PROFILE)
        with patch.object(injection_cohort,'run_screened',return_value=0) as run:
            self.assertEqual(full.main(cohort_path='not-read.json',prompt_profile=PROFILE),0)
            self.assertEqual(run.call_args.kwargs['prompt_profile'],PROFILE)
        config=normalize_config({'suites':[get_suites()[0]],'prompt_profile':PROFILE,'prompt_profile_sha256':'forged'})
        self.assertEqual(config['prompt_profile_sha256'],profiles.profile_binding(PROFILE)['prompt_profile_sha256'])
        self.assertFalse(_compatible_binding({'controls':{}},{'controls':{},**profiles.profile_binding(PROFILE)}))
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            full.cli(['--clean','--baseline','--prompt-profile',PROFILE])
        for value in ({'origin':True},{'use_sandbox':False},{'use_security_checker':False}):
            with self.assertRaises(ValueError):normalize_config({'suites':[get_suites()[0]],'prompt_profile':PROFILE,**value})

    def test_corrected_packets_have_authorized_candidates_and_registered_sources(self):
        bundle=build_stage('audit')
        self.assertEqual(bundle.get('input_revision'),'authorized-v2')
        self.assertEqual(len(bundle['requests']),96)
        for case in bundle['cases']:
            packet=case['packet'];policy=packet['policy_features']
            self.assertEqual(policy['sandbox_policy_state'],'allowlist')
            self.assertEqual(policy['allowlist_matches'],[True]*len(packet['current_actions']))
            self.assertEqual(policy['candidate_count'],len(packet['current_actions']))
            self.assertEqual(policy['registered_tool_count'],7 if case['suite']=='slack' else 6)
        self.assertEqual(compare_stage(bundle)['status'],'not_measured')
        old=build_stage('audit',input_revision='legacy-v1')
        self.assertNotIn('input_revision',old)
        self.assertNotEqual(old['bundle_sha256'],'9431ec034c7928d9171da96c3cf4da4fd66e499f7337a2205c21fa2c5e16bec8')  # renamed packet identity cannot reuse the historical bundle
        self.assertEqual(compare_stage(old)['status'],'not_measured')
        self.assertNotEqual(bundle['bundle_sha256'],old['bundle_sha256'])
        with self.assertRaises(ValueError):build_stage('audit',input_revision='invented')

    def test_real_runner_manifest_binds_candidate_and_rejects_other_profiles(self):
        from experiments import run_partial_benchmark as runner
        from baseintent.benchmark_catalog import get_suites,get_backend
        def scored(*args,**kwargs):
            return {'utility_results':dict.fromkeys(kwargs['user_tasks'],True)}
        root=Path(__file__).resolve().parents[1]/'artifacts/tests/test_task_alignment'
        with TemporaryDirectory(dir=root) as directory,\
                patch.object(d,'create_openai_client',return_value=Mock()),\
                patch.object(runner.benchmark,'benchmark_suite_without_injections',side_effect=scored),\
                patch.object(runner,'run_suite_with_progress',side_effect=legacy_suite_dispatch),\
                redirect_stdout(StringIO()):
            options=dict(model_id='qwen3.7-flash',api_key='offline-key',suites=[get_suites()[0]],
                         run_attack=False,results_dir=directory,run_name='candidate',audit_router_mode='shadow')
            self.assertEqual(runner.main(prompt_profile=PROFILE,**options),0)
            path=Path(directory)/get_backend().id/'qwen3.7-flash_candidate/none'/get_suites()[0]/'run_manifest.json'
            original=path.read_bytes();manifest=json.loads(original)
            self.assertEqual(manifest['prompt_profile'],PROFILE)
            self.assertEqual(manifest['prompt_profile_sha256'],profiles.profile_binding(PROFILE)['prompt_profile_sha256'])
            self.assertEqual(runner.main(prompt_profile='legacy',**options),1)
            self.assertEqual(runner.main(prompt_profile='tool-semantics-v1',**options),1)
            self.assertEqual(path.read_bytes(),original)

    def test_candidate_allow_cannot_execute_an_unauthorized_tool(self):
        runtime=synthetic_runtime('slack');sandbox=d.PermissionSandbox([])
        checker=d.ActionSecurityChecker(model('{"decision":"allow","violations":[],"confidence":1,"reason_code":"ALIGNED"}'),
                                        prompt_profile=PROFILE)
        monitor=d.ReferenceMonitor(sandbox,True)
        call=FunctionCall(function='send_direct_message',args={'recipient':'Mira','body':'text'},id='send')
        state=('Send Mira a message',runtime,EmptyEnv(),[{'role':'assistant','content':[],'tool_calls':[call]}],{})
        state=checker.query(*state)
        state=monitor.query(*state)
        state=d.TicketedToolsExecutor(monitor).query(*state)
        self.assertEqual(state[-1]['baseintent_action_ledger'][0]['state'],'blocked')
        self.assertEqual(state[-1]['baseintent_audit_decision']['final_policy_decision'],'deny')


if __name__=='__main__':unittest.main()
