"""Deterministic event routing; no claims about model judgment quality."""
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
from baseintent import intent_flow as f
from baseintent.benchmark_catalog import get_suite,get_backend


def mapping(prepare=('get_webpage',), groups=(('invite_user_to_slack',),)):
    return (('intent_1', tuple(prepare), tuple(tuple(g) for g in groups)),)


class AssociationTests(unittest.TestCase):
    def test_preparations_merge_into_outcome_without_losing_constraints(self):
        intents,kinds=f.business_goals(('Find hotel details','Check explicit condition','Create only if true','Report result'),
            ('facts','condition','conditional_effect','answer'))
        self.assertEqual(kinds,('conditional_effect','answer'))
        self.assertEqual(intents,('Find hotel details; Check explicit condition; Create only if true','Report result'))
        self.assertEqual(f.business_goals(('First invite','Second invite'),('effect','effect')),
            (('First invite','Second invite'),('effect','effect')))
        self.assertEqual(f.business_goals(('Get facts',),('facts',)),(('Get facts',),('facts',)))

    def test_empty_catalog_schema_has_no_impossible_array_bounds(self):
        schema=f.tools_schema([])
        group=schema['properties']['step_tool_expectations']['properties']['intent_1']['properties']['completion_groups']['items']
        self.assertLessEqual(group['minItems'],group['maxItems'])

    def test_outbound_schema_uses_supported_keywords_but_parser_stays_unique(self):
        self.assertNotIn("uniqueItems",json.dumps(f.tools_schema(["a"])))

    def test_strict_associations_are_frozen_and_cannot_add_grants(self):
        payload=dict(tools=['invite_user_to_slack'],step_tool_expectations={'intent_1':dict(prepare_tools=['get_webpage'],completion_groups=[['invite_user_to_slack']])})
        selected, associations=f.parse_tools(payload, {'get_webpage','invite_user_to_slack'},
            {'get_webpage'}, ('intent_1',))
        self.assertEqual(associations,mapping())
        self.assertEqual(selected,frozenset({'invite_user_to_slack'}))
        for mutate in ('unknown','ungranted','empty_group','duplicate','extra'):
            bad=deepcopy(payload)
            if mutate=='unknown':bad['step_tool_expectations']['intent_1']['prepare_tools']=['x']
            if mutate=='ungranted':bad['tools']=[]
            if mutate=='empty_group':bad['step_tool_expectations']['intent_1']['completion_groups']=[[]]
            if mutate=='duplicate':bad['step_tool_expectations']['intent_2']=deepcopy(bad['step_tool_expectations']['intent_1'])
            if mutate=='extra':bad['step_tool_expectations']['intent_1']['allow']=True
            with self.subTest(mutate=mutate),self.assertRaises(f.IntentFlowError):
                f.parse_tools(bad,{'get_webpage','invite_user_to_slack'},{'get_webpage'},('intent_1',))

    def test_read_tools_cannot_be_mislabeled_as_completion_effects(self):
        payload=dict(tools=['invite_user_to_slack'],step_tool_expectations={'intent_1':dict(prepare_tools=[],completion_groups=[['get_webpage']])})
        with self.assertRaises(f.IntentFlowError):
            f.parse_tools(payload, {'get_webpage','invite_user_to_slack'},{'get_webpage'},('intent_1',))
        schema=f.tools_schema(['get_webpage','invite_user_to_slack'],automatic_reads={'get_webpage'})
        fields=schema['properties']['step_tool_expectations']['properties']['intent_1']['properties']
        self.assertEqual(fields['prepare_tools']['items']['enum'],['get_webpage'])
        self.assertEqual(fields['completion_groups']['items']['items']['enum'],['invite_user_to_slack'])

    def test_compact_authorization_preserves_progress_map(self):
        from baseintent.pipelines import defended as d
        record={'step_tool_expectations':[dict(step_id='intent_1',prepare_tools=[],completion_groups=[])]}
        self.assertEqual(d._compact_authorization_record(record),record)

    def test_empty_completion_groups_never_complete(self):
        obj=f.IntentFlow(('Answer the query',),'Answer',goal_kinds=('answer',),
            tool_expectations=mapping(groups=()))
        self.assertFalse(obj.execution_ready({}))


class HostDiagnosticTests(unittest.TestCase):
    def test_host_event_never_inherits_previous_semantic_response(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from baseintent.task_diagnostics import DiagnosticSession,record_event
        with TemporaryDirectory() as root:
            logger=SimpleNamespace(dirpath=root,context=dict(pipeline_name='p',suite_name='s',
                user_task_id='u',attack_type='none'))
            with DiagnosticSession(logger,'attempt',{}) as session:
                session.responses['intent_progress']='old-model-response'
                record_event('intent_progress',dict(revision=2, observations=[dict(
                    progress_source='host',route_reason='PREPARATION_OBSERVED')]))
                session.finish({})
            rows=[json.loads(l) for l in (Path(root)/'p/s/u/none/none.baseintent.jsonl').read_text().splitlines()]
            event=next(r for r in rows if r['event']=='intent_progress')
            self.assertNotIn('response_id',event)


class EventRoutingTests(unittest.TestCase):
    def flow(self,kind='effect',groups=(('invite_user_to_slack',),)):
        return f.IntentFlow(('Find email and invite the requested user',),'Invite Fixture Guest at guest@example.org',
            goal_kinds=(kind,),tool_expectations=mapping(groups=groups))

    def test_prepare_read_updates_host_without_progress_request(self):
        obj=self.flow();llm=Mock()
        messages=[dict(role='tool',tool_call_id='read',tool_call=dict(function='get_webpage',args={'url':'source'}),
                       content=[dict(type='text',content='email')],error=None)]
        from hashlib import sha256
        ledger=[dict(state='executed',call_id='read',tool_name='get_webpage',
            arguments_sha256=sha256(json.dumps({'url':'source'},sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest(),
            effect='read',intent_id='intent_1')]
        with patch.object(f,'request_json',side_effect=AssertionError('unexpected semantic request')):
            obj.observe(llm,messages,ledger)
        self.assertEqual(obj.current['intent_id'],'intent_1')
        self.assertTrue(obj.current['host_facts']['facts_observed'])
        self.assertEqual(obj.observations[-1]['progress_source'],'host')
        self.assertEqual(obj.observations[-1]['route_reason'],'PREPARATION_OBSERVED')

    def test_simple_native_invite_completes_only_with_valid_execution_and_audit(self):
        for success,audit,owner,body,expected in [(True,True,'intent_1','None',True),
            (False,True,'intent_1','None',False),(True,False,'intent_1','None',False),
            (True,True,'intent_0','None',False),(True,True,'intent_1','error',False)]:
            obj=self.flow();row=dict(successful=success,effect='external_send',intent_id=owner,
                tool_name='invite_user_to_slack',audit_verified=audit,content=body)
            with self.subTest(success=success,audit=audit,owner=owner,body=body):
                self.assertEqual(obj.can_complete_from_events({'call:x':row},
                    supported_tools={'invite_user_to_slack'}),expected)

    def test_two_invites_or_extra_deliveries_never_take_simple_host_completion(self):
        row=dict(successful=True,effect='external_send',intent_id='intent_1',
            tool_name='invite_user_to_slack',audit_verified=True,content='None')
        for request in ('Invite Alice and Bob', 'Invite Alice then send me a summary',
                'Invite Alice if the condition is true', 'Invite Dora to Slack. Find her email on a website.'):
            obj=self.flow();obj.request=request
            self.assertFalse(obj.can_complete_from_events({'call:x':row},supported_tools={'invite_user_to_slack'}))

    def test_failed_or_blocked_returns_are_semantic_events_not_absent(self):
        from hashlib import sha256
        for status,err in [('failed','tool failure'),('blocked','L3_BLOCKED:AUDIT_DENY'),
                           ('blocked','L3_BLOCKED:AUDIT_ABSTAIN'),('blocked','L3_BLOCKED:AUDIT_SCHEMA_INVALID')]:
            obj=self.flow();args={'user':'Fixture Guest','user_email':'guest@example.org'}
            message=dict(role='tool',tool_call_id='x',tool_call=dict(function='invite_user_to_slack',args=args),
                content=[dict(type='text',content='')],error=err)
            ledger=[dict(state=status,call_id='x',tool_name='invite_user_to_slack',intent_id='intent_1',
                effect='external_send',arguments_sha256=sha256(json.dumps(args,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest())]
            with patch.object(f,'request_json',return_value=dict(satisfaction='not_yet',evidence_ids=[])) as request:
                obj.observe(Mock(),[message],ledger)
                self.assertEqual(request.call_count,1)
            self.assertEqual(obj.observations[-1]['progress_source'],'semantic')

    def test_complex_and_conditional_goals_stay_semantic(self):
        row=dict(successful=True,effect='external_send',intent_id='intent_1',
            tool_name='invite_user_to_slack',audit_verified=True,content='None')
        for kind in ('facts','answer','condition','conditional_effect'):
            self.assertFalse(self.flow(kind).can_complete_from_events({'call:x':row},
                supported_tools={'invite_user_to_slack'}))
        for groups in ((),(('invite_user_to_slack',),('invite_user_to_slack',))):
            self.assertFalse(self.flow(groups=groups).can_complete_from_events({'call:x':row},
                supported_tools={'invite_user_to_slack'}))

    @unittest.skipUnless(get_backend().id == 'agentdojo','AgentDojo native completion contract')
    def test_known_native_contract_only_not_tool_name_or_new_backend(self):
        from agentdojo.functions_runtime import FunctionsRuntime
        suite=get_suite('v1.2','slack')
        runtime=FunctionsRuntime(suite.tools)
        self.assertEqual(f.reviewed_completion_tools(runtime),frozenset({'invite_user_to_slack'}))
        fake=SimpleNamespace(functions={'invite_user_to_slack':SimpleNamespace(run=lambda:None)})
        self.assertEqual(f.reviewed_completion_tools(fake),frozenset())


@unittest.skipUnless(get_backend().id == 'agentdojo','AgentDojo native completion contract')
class NativeEventPipelineTests(unittest.TestCase):
    def test_reviewed_invite_uses_host_advance_and_no_progress_model(self):
        import httpx
        from openai import OpenAI
        from agentdojo.functions_runtime import FunctionsRuntime
        from baseintent.pipelines import defended as d
        from baseintent.model_config import ModelConfig
        from baseintent.tool_metadata import load_tool_metadata
        from test_request_compatibility import completion
        suite=get_suite('v1.2','slack')
        runtime=FunctionsRuntime(suite.tools)
        env=suite.load_and_inject_default_environment({})
        count={'generation':0,'progress':0};clients=[]
        def handler(req):
            body=json.loads(req.content);policy=body['messages'][0]['content']
            if body.get('response_format'):
                packet=json.loads(body['messages'][-1]['content'])
                if policy.startswith('Decompose'):
                    value={'authorization_steps':[{'intent':'Invite the requested guest','goal_kind':'effect'}]}
                elif policy.startswith('Select global'):
                    value={'tools':['invite_user_to_slack'],'step_tool_expectations':{'intent_1':dict(prepare_tools=[],completion_groups=[['invite_user_to_slack']])}}
                elif policy.startswith('Observe progress'):
                    count['progress']+=1
                    value=dict(satisfaction='satisfied',evidence_ids=['call:invite'])
                else:value=dict(decision='allow',violations=[],confidence=.9,reason_code='ALIGNED')
                result=completion(json.dumps(value))
            else:
                count['generation']+=1
                if count['generation']==1:
                    result=completion('',[dict(id='invite',type='function',function=dict(name='invite_user_to_slack',
                        arguments=json.dumps(dict(user='Fixture Guest',user_email='guest@example.org'))))])
                    result['choices'][0]['finish_reason']='tool_calls'
                else:result=completion('The guest was invited.')
            return httpx.Response(200,json=result,request=req)
        def client(config):
            c=OpenAI(api_key='offline',base_url='https://offline.invalid/v1',max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            clients.append(c);return c
        try:
            with patch.object(d,'create_openai_client',side_effect=client):
                config=ModelConfig('qwen3.7-flash','offline','https://offline.invalid/v1','custom')
                pipe,main,audit=d.make_defended_pipeline(model_config=config,sec_model_config=config,
                    tool_metadata=load_tool_metadata('config/tools.agentdojo-v1.2.toml'))
                result=pipe.query('Invite Fixture Guest at guest@example.org',runtime,env)
            self.assertEqual(count,{'generation':2,'progress':0})
            state=result[-1]['baseintent_intent_flow']
            self.assertEqual(state['steps'][0]['state'],'completed')
            self.assertEqual(state['observations'][-1]['progress_source'],'host')
            self.assertIsNone(state['steps'][0]['host_facts']['semantic_satisfied'])
            self.assertIn('Fixture Guest',result[2].slack.users)
            self.assertNotIn('intent_progress',main.snapshot())
        finally:
            for c in clients:c.close()
