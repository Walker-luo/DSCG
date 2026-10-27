"""Deterministic state/evidence contracts; these do not test model judgment quality."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_intent_host_fsm')
import json
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from baseintent import intent_flow as f


def read(owner='intent_1', **changes):
    return dict(successful=True, effect='read', intent_id=owner, **changes)


def effect(owner='intent_1'):
    return dict(successful=True, effect='external_send', intent_id=owner)


def answer(owner='intent_1'):
    return dict(successful=False, final_answer=True, intent_id=owner)


class HostProgressTests(unittest.TestCase):
    def flow(self, kind='effect', *, second=True):
        return f.IntentFlow(('Current goal', 'Next goal') if second else ('Current goal',),
            'Complete the requested work without extra actions.',
            goal_kinds=(kind, 'effect') if second else (kind,))

    def apply(self, flow, result='satisfied', evidence=None, refs=None, final=False):
        evidence = evidence if evidence is not None else {'call:one': effect()}
        return flow.apply(dict(satisfaction=result,
            evidence_ids=list(evidence) if refs is None else refs), evidence, final=final)

    def test_semantic_satisfaction_needs_current_executed_effect(self):
        for row, want in [(effect(), 'intent_2'),
                          (dict(successful=False, effect='write', intent_id='intent_1'), 'intent_1'),
                          (read(), 'intent_1'), (effect('intent_0'), 'intent_1'),
                          (dict(successful=True, effect='write'), 'intent_1')]:
            with self.subTest(row=row):
                flow=self.flow(); self.apply(flow,evidence={'call:one':row})
                self.assertEqual(flow.current['intent_id'],want)

    def test_successful_effect_is_not_semantic_completion(self):
        flow=self.flow(); self.apply(flow,'not_yet')
        self.assertEqual(flow.current['intent_id'],'intent_1')
        self.assertTrue(flow.steps[0]['host_facts']['effect_observed'])
        self.assertFalse(flow.steps[0]['host_facts']['semantic_satisfied'])

    def test_query_cannot_complete_answer_before_delivery(self):
        flow=self.flow('answer'); self.apply(flow,evidence={'call:r':read()})
        self.assertEqual(flow.current['intent_id'],'intent_1')
        self.assertTrue(flow.current['host_facts']['facts_observed'])
        self.assertFalse(flow.current['host_facts']['answer_emitted'])
        self.apply(flow,evidence={'message:2':answer()},final=True)
        self.assertEqual(flow.current['intent_id'],'intent_2')

    def test_main_claim_cannot_replace_effect(self):
        flow=self.flow(); self.apply(flow,evidence={'message:2':answer()},final=True)
        self.assertEqual(flow.current['intent_id'],'intent_1')

    def test_completion_uses_referenced_evidence_not_other_available_rows(self):
        flow=self.flow(); self.apply(flow,evidence={'call:w':effect(),'call:r':read()},refs=['call:r'])
        self.assertEqual(flow.current['intent_id'],'intent_1')

    def test_host_advances_only_one_goal_and_does_not_reuse_prior_effect(self):
        flow=self.flow(); self.apply(flow)
        self.assertEqual(flow.current['intent_id'],'intent_2')
        self.apply(flow)
        self.assertEqual(flow.current['intent_id'],'intent_2')
        self.assertEqual(flow.steps[0]['state'],'completed')
        self.assertEqual(flow.observations[0]['completion_kind'],'effect')

    def test_unknown_duplicate_and_injected_control_fields_rejected_atomically(self):
        for change in ({'evidence_ids':['missing']},{'evidence_ids':['call:one','call:one']},
                       {'next_intent_id':'intent_99'},{'status':'completed'},
                       {'reason':'x'*5000},{'satisfaction':'unfulfillable'},
                       {'satisfaction':True},{'evidence_ids':'call:one'}):
            flow=self.flow(); payload=dict(satisfaction='satisfied',evidence_ids=['call:one']);payload.update(change)
            before=flow.binding()
            with self.assertRaises(f.IntentFlowError):flow.apply(payload,{'call:one':effect()})
            self.assertEqual(flow.binding(),before)

    def test_ambiguous_is_only_a_proposal_without_delivered_clarification(self):
        flow=self.flow(); self.apply(flow,'ambiguous',evidence={'call:r':read()})
        self.assertEqual(flow.current['state'],'active')
        self.apply(flow,'ambiguous',evidence={'call:r':read(),'message:q':answer()},refs=['call:r'],final=True)
        self.assertEqual(flow.current['state'],'active')
        self.apply(flow,'ambiguous',evidence={'message:q':answer()},final=True)
        self.assertIsNone(flow.current)
        self.assertEqual(flow.steps[0]['state'],'awaiting_user')
        self.assertEqual(flow.steps[1]['state'],'pending')

    def test_condition_false_is_not_unknown_and_requires_read_evidence(self):
        flow=self.flow('conditional_effect')
        self.apply(flow,'not_yet',evidence={'call:r':read()})
        self.assertEqual(flow.current['intent_id'],'intent_1')
        self.apply(flow,'condition_false',evidence={'call:r':read()})
        self.assertEqual(flow.current['intent_id'],'intent_2')
        self.assertEqual(flow.observations[-1]['completion_kind'],'condition')
        for kind, row in [('effect',read()),('conditional_effect',dict(successful=False,effect='read'))]:
            flow=self.flow(kind)
            if kind=='effect':
                with self.assertRaises(f.IntentFlowError):self.apply(flow,'condition_false',evidence={'call:r':row})
            else:
                self.apply(flow,'condition_false',evidence={'call:r':row})
                self.assertEqual(flow.current['intent_id'],'intent_1')

    def test_false_condition_cannot_certify_an_already_executed_conditional_effect(self):
        flow=self.flow('conditional_effect')
        self.apply(flow,'condition_false',evidence={'call:r':read(),'call:w':effect()},refs=['call:r'])
        self.assertEqual(flow.current['intent_id'],'intent_1')

    def test_condition_conflict_survives_effect_leaving_the_evidence_window(self):
        flow=self.flow('conditional_effect')
        self.apply(flow,'not_yet',evidence={'call:w':effect()})
        self.apply(flow,'condition_false',evidence={'call:r':read()})
        self.assertEqual(flow.current['intent_id'],'intent_1')
        self.assertTrue(flow.current['host_facts']['effect_observed'])
        self.assertEqual(flow.observations[-1]['reason_code'],'CONDITION_EFFECT_CONFLICT')

    def test_facts_and_conditions_can_use_successful_prior_reads(self):
        for kind in ('facts','condition'):
            flow=self.flow(kind);self.apply(flow,evidence={'call:r':read('intent_0')})
            self.assertEqual(flow.current['intent_id'],'intent_2')

    def test_host_rejects_missing_or_unknown_goal_types(self):
        for kinds in (None,(),('arbitrary',),('effect','answer')):
            with self.subTest(kinds=kinds),self.assertRaises(f.IntentFlowError):
                f.IntentFlow(('One',),'One',goal_kinds=kinds)


class ProgressEvidenceTests(unittest.TestCase):
    def observe(self, *, bad_hash=False, blocked=False, result='satisfied', exhausted=False):
        args={'body':'Hello'}
        messages=[dict(role='tool',tool_call_id='one',tool_call=dict(function='send',args=args),
                       content=[],error='L3_BLOCKED:AUDIT_DENY' if blocked else None)]
        ledger=[dict(state='executed',call_id='one',tool_name='send',arguments_sha256=sha256(
                     json.dumps(args,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest(),
                     effect='external_send',intent_id='intent_1')]
        if bad_hash:ledger[0]['arguments_sha256']='wrong'
        client=Mock();client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(dict(satisfaction=result,evidence_ids=['call:one'])),
                                    refusal=None),finish_reason='stop')])
        flow=f.IntentFlow(('Send greeting',),'Send greeting',goal_kinds=('effect',))
        flow.observe(SimpleNamespace(client=client,name='offline'),messages,ledger,exhausted=exhausted)
        packet=json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        return flow,packet

    def test_real_none_return_matches_exact_call_and_arguments(self):
        flow,packet=self.observe()
        self.assertIsNone(flow.current)
        self.assertTrue(flow.steps[0]['host_facts']['effect_observed'])
        self.assertTrue(packet['host_observation']['effect_observed'])

    def test_changed_arguments_and_blocked_returns_cannot_supply_effect(self):
        for flags in ({'bad_hash':True},{'blocked':True}):
            flow,packet=self.observe(**flags)
            self.assertEqual(flow.current['intent_id'],'intent_1')
            self.assertFalse(packet['host_observation']['effect_observed'])

    def test_exhaustion_does_not_invent_completion_or_skip(self):
        with self.assertRaises(f.IntentFlowError) as caught:self.observe(result='not_yet',exhausted=True)
        self.assertEqual(caught.exception.reason_code,'INTENT_NO_PROGRESS')


class GoalContractTests(unittest.TestCase):
    def test_goal_types_are_frozen_without_changing_global_grants(self):
        def reply(payload):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(payload),refusal=None),finish_reason='stop')])
        client=Mock();client.chat.completions.create.side_effect=[
            reply({'authorization_steps':[{'intent':'Tell me the balance','goal_kind':'answer'}]}),
            reply({'tools':[], 'step_tool_expectations':{'intent_1':dict(prepare_tools=[],completion_groups=[])}})]
        intents,kinds,grants,links=f.compile_authorization(SimpleNamespace(name='offline',client=client),
            'Tell me the balance',{},set())
        self.assertEqual(intents,('Tell me the balance',))
        self.assertEqual(kinds,('answer',));self.assertEqual(grants,frozenset())
        self.assertEqual(client.chat.completions.create.call_count,2)
        a=f.IntentFlow(intents,'Task',goal_kinds=('answer',))
        b=f.IntentFlow(intents,'Task',goal_kinds=('facts',))
        self.assertNotEqual(a.binding(),b.binding())

    def test_invalid_goal_type_is_not_guessed_or_repaired(self):
        for step in ({'intent':'Send'},{'intent':'Send','goal_kind':'write'},
                     {'intent':'Send','goal_kind':['effect']},
                     {'intent':'Send','goal_kind':'effect','tools':['send']}):
            with self.subTest(step=step),self.assertRaises(f.IntentFlowError):
                f.parse_intents({'authorization_steps':[step]})


class ExhaustionDiagnosticsTests(unittest.TestCase):
    def test_last_host_observation_is_emitted_before_bounded_stop(self):
        from baseintent.pipelines import defended as d
        from baseintent.task_diagnostics import DiagnosticSession
        from test_intent_flow import tools
        runtime,_=tools();client=Mock()
        client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(dict(satisfaction='not_yet',evidence_ids=[])),
                                    refusal=None),finish_reason='stop')])
        executor=d.OurFrameExecutor(SimpleNamespace(name='offline',client=client),
            sandbox=d.PermissionSandbox(list(runtime.functions)))
        executor.intent_flow=f.IntentFlow(('Answer','Send'),'Answer then send',goal_kinds=('answer','effect'))
        executor.intent_flow.continue_once()
        messages=[dict(role='assistant',content=[dict(type='text',content='I have not answered yet.')],tool_calls=None)]
        root=Path(__file__).resolve().parents[1]/'artifacts/tests/test_intent_host_fsm'
        with TemporaryDirectory(dir=root) as tmp:
            logger=SimpleNamespace(dirpath=tmp,context=dict(pipeline_name='engine',suite_name='sample',
                user_task_id='user_task_1',attack_type='attack',injection_task_id='injection_task_1'))
            with DiagnosticSession(logger,'one',{}):
                with self.assertRaises(f.IntentFlowError) as caught:
                    executor._observe_intent(messages,{},final=True,runtime=runtime)
            side=Path(tmp)/'engine/sample/user_task_1/attack/injection_task_1.baseintent.jsonl'
            observations=[row['record']['observation'][0] for row in map(json.loads,side.read_text().splitlines())
                          if row['event']=='intent_progress']
        self.assertEqual(caught.exception.reason_code,'INTENT_NO_PROGRESS')
        self.assertEqual(executor.intent_flow.steps[0]['state'],'active')
        self.assertEqual(executor.intent_flow.steps[1]['state'],'pending')
        self.assertEqual(len(observations),1)
        self.assertEqual(observations[0]['reason_code'],'SEMANTIC_NOT_YET')


if __name__=='__main__':unittest.main()
