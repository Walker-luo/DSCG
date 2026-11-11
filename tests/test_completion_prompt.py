import unittest
from unittest.mock import patch, Mock
from dscg.model_config import ModelConfig
from dscg.pipelines.defended import make_defended_pipeline

class CompletionPromptTests(unittest.TestCase):
    def build(self,enabled):
        with patch('dscg.pipelines.defended.create_openai_client',return_value=Mock()):
            return make_defended_pipeline(model_config=ModelConfig(provider='custom',model_id='fixture',api_key='offline',base_url='http://offline'),use_security_checker=False,completion_prompt=enabled)[0]
    def test_prompt_is_optional_and_preserves_monitor_and_ticket_executor(self):
        normal=self.build(False);guided=self.build(True)
        self.assertNotEqual(normal.elements[0].system_message,guided.elements[0].system_message)
        self.assertIn('Continue the task authorized by the trusted user',guided.elements[0].system_message)
        self.assertIn('requested fields',guided.elements[0].system_message)
        self.assertIn('do not add tools, recipients, objects, or data access',guided.elements[0].system_message)
        self.assertEqual([type(x) for x in normal.elements[-1].elements], [type(x) for x in guided.elements[-1].elements])
        self.assertTrue(guided.dscg_optimization_config['completion_prompt'])
