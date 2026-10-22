"""Strict single-call step coverage with native tool schemas, no paid API."""
import json,unittest
from typing import Annotated
from types import SimpleNamespace
from unittest.mock import Mock
from agentdojo.functions_runtime import FunctionsRuntime
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata

def runtime():
 r=FunctionsRuntime()
 @r.register_function
 def discover() -> str:
  """Find the channel."""
  return 'general'
 @r.register_function
 def send_channel_message(channel:Annotated[str,"Channel"],body:Annotated[str,"Body"]) -> str:
  """Send content from author to a channel.

  Args:
      channel: Target channel.
      body: Message body.
  """
  return 'sent'
 set_tool_metadata(r,{'discover':dict(effect='read',source='local',sink='none',sensitivity='internal',idempotent=True,reversible=True),
   'send_channel_message':dict(effect='external_send',source='local',sink='public_output',sensitivity='internal',idempotent=False,reversible=False)})
 return r

def compile(payload):
 client=Mock();client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload),refusal=None),finish_reason='stop')]);llm=SimpleNamespace(name='offline',client=client)
 return d.ToolAuthorizationCompiler(llm).compile(d.TrustedTaskRequest('Find the channel and reply there.'),runtime()),client

def valid():return {'steps':[{'intent':'Find the channel','tools':['discover']},{'intent':'Reply to it','tools':['send_channel_message']}],'tools':['discover','send_channel_message']}

class StepAuthorizationTests(unittest.TestCase):
 def test_native_schema_full_catalogue_one_call_and_step_trace(self):
  grant,client=compile(valid());client.chat.completions.create.assert_called_once();packet=json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
  self.assertEqual(set(packet['available_tools']),{'discover','send_channel_message'})
  self.assertEqual(packet['available_tools']['send_channel_message']['parameters']['required'],['channel','body'])
  self.assertEqual(packet['available_tools']['discover']['authorization'],'automatic_read')
  self.assertIn('send_channel_message',grant.allowed_tools)
  self.assertEqual(grant.public_dict()['authorization_steps'],valid()['steps'])
 def test_bad_steps_unknown_tools_duplicates_and_union_mismatch_fail_closed(self):
  bad=[['send_channel_message'],{'tools':['send_channel_message']},{**valid(),'steps':[]},{**valid(),'tools':[]},{**valid(),'tools':['send_channel_message','send_channel_message']},
   {**valid(),'steps':[{'intent':'send','tools':['ghost']}]},{**valid(),'steps':[{'intent':'','tools':['send_channel_message']}]},
   {**valid(),'steps':[{'intent':'send','tools':['send_channel_message'],'extra':True}]}]
  for value in bad:
   with self.subTest(value=value),self.assertRaises(d.AuthorizationCompilationError):compile(value)
 def test_read_only_step_does_not_gain_action_and_no_host_semantic_pairing(self):
  grant,_=compile({'steps':[{'intent':'Only inspect','tools':['discover']}],'tools':['discover']})
  self.assertNotIn('send_channel_message',grant.allowed_tools)
 def test_version_and_default_policy_identity(self):
  self.assertEqual(d.FRAMEWORK_VERSION,'DSCG_v3.3');self.assertIn('steps',d.ToolAuthorizationCompiler.SYSTEM_POLICY)
 def test_router_identity_binds_the_policy_actually_used_by_each_profile(self):
  from unittest.mock import patch
  from dscg.model_config import ModelConfig
  cfg=ModelConfig('offline','offline','https://offline.invalid','custom')
  options=dict(input_isolation=True,authorization_precheck=True,l1_projection_mode='projected',planning_tool_view=True,delegated_tasks=True)
  def identity(profile):return d.router_configuration_hash(cfg,cfg,prompt_profile=profile,**options)
  default=identity('legacy');candidate=identity('protocol-v1')
  with patch.object(d.ToolAuthorizationCompiler,'CLASSIC_POLICY','changed candidate base'):
   self.assertEqual(default,identity('legacy'))
   self.assertNotEqual(candidate,identity('protocol-v1'))
