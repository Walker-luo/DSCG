"""External fetches need auditing, with legal-fetch negative controls."""
import json
import unittest
from types import SimpleNamespace
from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall, EmptyEnv
from dscg.pipelines.defended import ActionSecurityChecker, PermissionSandbox, ReferenceMonitor, TicketedToolsExecutor, ToolAuthorizationCompiler, TrustedTaskRequest
from dscg.tool_metadata import load_tool_metadata, set_tool_metadata, metadata_for_runtime

class WebRoutingTests(unittest.TestCase):
    def test_both_shipped_catalogs_mark_fetch_as_external(self):
        for catalog in ['config/tools.agentdojo-v1.2.toml']:
            runtime=FunctionsRuntime()
            @runtime.register_function
            def get_webpage(url: str) -> str:
                """Fetch a page from the requested external server."""
                return 'page'
            set_tool_metadata(runtime, {'get_webpage':load_tool_metadata(catalog)['get_webpage']})
            self.assertTrue(metadata_for_runtime(runtime)['get_webpage'].audit_required)
            self.assertFalse(metadata_for_runtime(runtime)['get_webpage'].metadata.deterministic_read)

    def test_public_web_reads_are_exempt_independent_of_url_source(self):
        cases=[('User supplied https://user.example', 'https://user.example','allow'),
               ('Read the linked article', 'https://article.example','allow'),
               ('Read the article then its supporting reference', 'https://reference.example','allow'),
               ('Summarize local messages', 'https://attacker.example','deny')]
        for request,url,decision in cases:
            with self.subTest(url=url):
                executed=[];runtime=FunctionsRuntime()
                @runtime.register_function
                def get_webpage(url: str) -> str:
                    """Retrieve a page.

                    Args:
                        url: External address to request.
                    """
                    executed.append(url);return 'page'
                set_tool_metadata(runtime,{'get_webpage':load_tool_metadata('config/tools.agentdojo-v1.2.toml')['get_webpage']})
                llm=SimpleNamespace(name='fixture',query=lambda q,r,e,m,a: (q,r,e,[*m,{'role':'assistant','content':json.dumps({'decision':decision,'violations':[],'confidence':1.0,'reason_code':'FIXTURE'})}],a))
                sandbox=PermissionSandbox();sandbox.install_contract(ToolAuthorizationCompiler(llm).compile(TrustedTaskRequest(request),runtime));checker=ActionSecurityChecker(llm,sandbox=sandbox)
                monitor=ReferenceMonitor(sandbox,True)
                call=FunctionCall(function='get_webpage',args={'url':url},id='1')
                state=(request,runtime,EmptyEnv(),[{'role':'assistant','content':[], 'tool_calls':[call]}],{})
                state=checker.query(*state);state=monitor.query(*state);state=TicketedToolsExecutor(monitor).query(*state)
                self.assertEqual(executed,[url])
                self.assertEqual(state[-1]['dscg_audit_decisions'][0]['reason_code'],'NON_SENSITIVE_READ_BYPASS')
