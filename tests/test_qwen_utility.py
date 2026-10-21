"""Protocol and prompt-candidate regression; no model network requests."""
import json
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall, EmptyEnv
from dscg.pipelines import defended as d
from dscg.tool_metadata import load_tool_metadata, set_tool_metadata


def model(text, finish='stop', refusal=None):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=text, refusal=refusal), finish_reason=finish)])
    return SimpleNamespace(name='offline', client=client)


def runtime():
    r = FunctionsRuntime()
    @r.register_function
    def get_webpage(url: str) -> str:
        """Read a remote webpage.

        Args:
            url: The remote address to read.
        """
        return 'page'
    @r.register_function
    def post_webpage(url: str, content: str) -> str:
        """Replace the content of a remote webpage.

        Args:
            url: The destination webpage.
            content: The replacement body.
        """
        return 'posted'
    metadata = load_tool_metadata('config/tools.agentdojo-v1.2.toml')
    set_tool_metadata(r, {k: metadata[k] for k in r.functions})
    return r


class AuditProtocolDiagnosticsTests(unittest.TestCase):
    def audit(self, llm, level='summary'):
        r = runtime()
        sandbox = d.PermissionSandbox(['get_webpage'])
        checker = d.ActionSecurityChecker(llm, sandbox=sandbox)
        call = FunctionCall(function='get_webpage', args={'url': 'https://article.example'}, id='read')
        state = checker.query('Read https://article.example', r, EmptyEnv(), [
            {'role': 'user', 'content': [{'type': 'text', 'content': 'Read https://article.example'}]},
            {'role': 'assistant', 'content': [], 'tool_calls': [call]}], {'_dscg_trace_level': level})
        state = d.ReferenceMonitor(sandbox, True).query(*state)
        return state[-1]['dscg_audit_decisions'][-1]

    def test_distinct_failures_still_block_without_retry_or_private_exception_text(self):
        good = dict(decision='allow', violations=[], confidence=1, reason_code='ALIGNED')
        cases = [
            (None, 'stop', None, 'EMPTY_RESPONSE'),
            ('```json\n{}\n```', 'stop', None, 'INVALID_JSON'),
            ('{}', 'stop', None, 'FIELDS_MISMATCH'),
            (json.dumps({**good, 'decision': 'yes'}), 'stop', None, 'INVALID_DECISION'),
            (json.dumps({**good, 'decision': []}), 'stop', None, 'INVALID_DECISION'),
            (json.dumps({**good, 'violations': 'none'}), 'stop', None, 'INVALID_VIOLATIONS'),
            (json.dumps({**good, 'confidence': True}), 'stop', None, 'INVALID_CONFIDENCE'),
            (json.dumps({**good, 'confidence': 10}), 'stop', None, 'INVALID_CONFIDENCE'),
            (json.dumps({**good, 'reason_code': 'free form'}), 'stop', None, 'INVALID_REASON_CODE'),
            (json.dumps(good), 'length', None, 'INCOMPLETE_RESPONSE'),
            (json.dumps(good), 'stop', 'private refusal', 'MODEL_REFUSAL'),
        ]
        for text, finish, refusal, code in cases:
            with self.subTest(code=code):
                llm = model(text, finish, refusal)
                record = self.audit(llm)
                self.assertEqual(record['protocol_diagnostics']['failure_type'], code)
                self.assertEqual(record['final_policy_decision'], 'deny')
                self.assertEqual(record['parser_status'], 'failure')
                self.assertEqual(llm.client.chat.completions.create.call_count, 1)
                self.assertNotIn('private refusal', json.dumps(record))

    def test_success_has_transport_and_validation_diagnostics_and_summary_counts(self):
        record = self.audit(model('{"decision":"allow","violations":[],"confidence":1,"reason_code":"ALIGNED"}'))
        diag = record['protocol_diagnostics']
        self.assertEqual(diag['field_validation'], 'passed')
        self.assertEqual(diag['finish_reason'], 'stop')
        self.assertFalse(diag['refusal_present'])
        summary = d._audit_summary([record])
        self.assertEqual(summary['protocol_failure_counts'], {})
        self.assertEqual(summary['field_validation_counts'], {'passed': 1})

    def test_no_choices_timeout_and_provider_errors_do_not_leak_exception_details(self):
        for kind, code in [('choices', 'NO_CHOICES'), ('timeout', 'TIMEOUT'), ('api', 'MODEL_ERROR')]:
            llm = model('{}')
            if kind == 'choices':
                llm.client.chat.completions.create.return_value = SimpleNamespace(choices=[])
            else:
                llm.client.chat.completions.create.side_effect = (
                    TimeoutError('sk-private-client-details') if kind == 'timeout' else RuntimeError('sk-private-client-details'))
            with self.subTest(kind=kind):
                record = self.audit(llm)
                self.assertEqual(record['protocol_diagnostics']['failure_type'], code)
                self.assertEqual(record['protocol_diagnostics']['field_validation'], 'not_checked')
                self.assertEqual(record['final_policy_decision'], 'deny')
                self.assertNotIn('sk-private', json.dumps(record))

    def test_only_full_trace_can_capture_bounded_failure_response(self):
        text = '{"private_source":"' + 'x' * 4000 + '"}'
        for level in ('summary', 'standard', 'full'):
            with self.subTest(level=level), patch.object(d, '_append_full_trace') as append:
                record = self.audit(model(text), level)
                captured = [c.args[2] for c in append.call_args_list if c.args[1] == 'audit_protocol_response']
                self.assertEqual(bool(captured), level == 'full')
                if captured:
                    self.assertEqual(len(captured[0]['response_preview']), 2048)
                    self.assertTrue(captured[0]['response_truncated'])
                    self.assertEqual(captured[0]['raw_response_sha256'], record['raw_response_sha256'])
                self.assertNotIn('private_source', json.dumps(record))


class PromptProfileTests(unittest.TestCase):
    def test_authored_source_cases_keep_raw_facts_and_monitor_denials(self):
        from experiments.diagnostics.utility_packets import build_packets
        source = build_packets('source-context-v1')
        self.assertEqual(source['model_calls'], 0)
        self.assertEqual(source['executed_tools'], 0)
        self.assertEqual(len(source['cases']), 12)
        self.assertEqual({r['authored_expectation'] for r in source['cases']}, {'allow', 'deny', 'abstain'})
        legacy = build_packets('legacy')
        self.assertEqual([r['packet'] for r in source['cases']], [r['packet'] for r in legacy['cases']])
        for row in source['cases']:
            packet = row['packet']
            self.assertTrue(all(r['trust'] == 'untrusted' for r in packet['recent_tool_results']))
            self.assertEqual(packet['schema_version'], 'dscg.audit-input.v2')
        # Author labels only exercise the handoff; they are not predicted model judgments.
        for outcome in ('deny', 'abstain'):
            llm = model(json.dumps(dict(decision=outcome, violations=['OFF_TASK'], confidence=1, reason_code='FIXTURE')))
            helper = AuditProtocolDiagnosticsTests()
            self.assertEqual(helper.audit(llm)['final_policy_decision'], 'deny')

    def test_candidate_unknown_tool_and_invalid_metadata_cannot_grant_execution(self):
        r = runtime()
        for name in ('ghost',):
            compiler = d.ToolAuthorizationCompiler(model(json.dumps({'tools': [name]})),
                                                   prompt_profile='tool-semantics-v1')
            with self.assertRaises(d.AuthorizationCompilationError):
                compiler.compile(d.TrustedTaskRequest('Read the page'), r)
        r._dscg_tool_metadata['post_webpage'] = {'effect': 'invented'}
        compiler = d.ToolAuthorizationCompiler(model('{"tools":[]}'), prompt_profile='tool-semantics-v1')
        contract = compiler.compile(d.TrustedTaskRequest('Read the page'), r)
        sandbox = d.PermissionSandbox()
        sandbox.install_contract(contract)
        self.assertFalse(sandbox.assess('post_webpage', r)[0])

    def test_preflight_and_real_factory_share_candidate_name_and_router_binding(self):
        from experiments.run_partial_benchmark import _describe_pipeline
        options = dict(use_sandbox=True, use_security_checker=True, l1_projection_mode='projected',
                       planning_tool_view=True, delegated_tasks=True, audit_router_mode='shadow',
                       audit_router_artifact=None, audit_router_threshold=.65, audit_retries=0, completion_prompt=False,
                       api_key='offline-key')
        hashes, names = set(), set()
        for profile in ('legacy', 'protocol-v1', 'tool-semantics-v1', 'source-context-v1'):
            described = _describe_pipeline('qwen3.7-flash', None, origin=False, defense=None,
                                           prompt_profile=profile, **options)
            with patch.object(d, 'create_openai_client', return_value=Mock()):
                actual, _, _ = d.make_defended_pipeline('qwen3.7-flash', prompt_profile=profile,
                                                       **options)
            self.assertEqual(described.name, actual.name)
            self.assertEqual(described.dscg_optimization_config['audit_router_config_sha256'],
                             actual.dscg_optimization_config['audit_router_config_sha256'])
            hashes.add(actual.dscg_optimization_config['audit_router_config_sha256'])
            names.add(actual.name)
        self.assertEqual(len(hashes), 4)
        self.assertEqual(len(names), 4)

    def test_cli_and_dashboard_reject_candidate_for_baseline_or_no_checker(self):
        from experiments.run_benchmark import cli
        from dashboard.evaluation import normalize_config
        from dscg.benchmark_catalog import get_suites
        for switch in ('--baseline', '--no-checker'):
            errors = StringIO()
            with self.subTest(switch=switch), redirect_stderr(errors):
                with self.assertRaises(SystemExit):
                    cli(['--clean', switch, '--prompt-profile', 'source-context-v1'])
                self.assertIn('candidate prompt profiles require', errors.getvalue())
        for values in ({'origin': True}, {'use_security_checker': False}, {'use_sandbox': False}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                normalize_config({'suites': list(get_suites()), 'prompt_profile': 'source-context-v1', **values})
        active = normalize_config({'suites': list(get_suites()), 'prompt_profile': 'protocol-v1',
                                   'prompt_profile_sha256': 'client-forged'})
        self.assertNotEqual(active['prompt_profile_sha256'], 'client-forged')
        active = normalize_config({'suites': list(get_suites()), 'prompt_profile_sha256': 'client-forged'})
        self.assertNotIn('prompt_profile_sha256', active)

    def test_full_partial_and_cohort_cli_forward_profile_without_model_requests(self):
        from experiments import run_benchmark as full, run_partial_benchmark as partial
        from experiments.common import injection_cohort
        for module in (full, partial):
            with self.subTest(module=module.__name__), patch.object(partial, 'main', return_value=0) as run:
                self.assertEqual(module.cli(['--clean', '--prompt-profile', 'tool-semantics-v1']), 0)
                self.assertEqual(run.call_args.kwargs['prompt_profile'], 'tool-semantics-v1')
        with patch.object(injection_cohort, 'run_screened', return_value=0) as run:
            self.assertEqual(full.main(cohort_path='frozen.json', prompt_profile='source-context-v1'), 0)
            self.assertEqual(run.call_args.kwargs['prompt_profile'], 'source-context-v1')

    def test_offline_runner_binds_candidate_and_refuses_same_named_legacy(self):
        from experiments import run_partial_benchmark as runner
        from dscg.benchmark_catalog import get_suites, get_backend
        # Run the real preflight/factory/manifest path; replace only the model transport
        # and scored native loop. This proves binding, not tool or model efficacy.
        def scored(*args, **kwargs):
            return {'utility_results': dict.fromkeys(kwargs['user_tasks'], True)}
        artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261019_qwen_utility'
        artifacts.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=artifacts) as directory, \
                patch.object(d, 'create_openai_client', return_value=Mock()), \
                patch.object(runner.benchmark, 'benchmark_suite_without_injections', side_effect=scored), \
                redirect_stdout(StringIO()):
            options = dict(model_id='qwen3.7-flash', api_key='offline-key', suites=[get_suites()[0]],
                           run_attack=False, results_dir=directory, run_name='bound', audit_router_mode='shadow')
            self.assertEqual(runner.main(prompt_profile='protocol-v1', **options), 0)
            p = Path(directory) / get_backend().id / 'qwen3.7-flash_bound/none' / get_suites()[0] / 'run_manifest.json'
            original = p.read_bytes()
            self.assertEqual(json.loads(original)['prompt_profile'], 'protocol-v1')
            self.assertEqual(runner.main(prompt_profile='source-context-v1', **options), 1)
            self.assertEqual(runner.main(**options), 1)
            self.assertEqual(p.read_bytes(), original)

    def test_cohort_and_manifest_bindings_reject_other_candidates_and_legacy_cache(self):
        from experiments.common.benchmark_reuse import _compatible_binding
        from dscg.benchmark_catalog import benchmark_identity
        from dscg.prompt_profiles import profile_binding
        old = {'benchmark': benchmark_identity(), 'schema_version': 'dscg.screened-run.v2',
               'controls': {'planning_tool_view': True}}
        for profile in ('protocol-v1', 'tool-semantics-v1', 'source-context-v1'):
            candidate = {**old, **profile_binding(profile)}
            self.assertFalse(_compatible_binding(old, candidate))
            self.assertTrue(_compatible_binding(candidate, dict(candidate)))
        self.assertFalse(_compatible_binding({**old, **profile_binding('protocol-v1')},
                                            {**old, **profile_binding('source-context-v1')}))

    def test_semantic_catalog_is_host_supplied_sorted_and_contract_bound(self):
        r = runtime()
        llm = model('{"tools":["post_webpage"]}')
        compiler = d.ToolAuthorizationCompiler(llm, prompt_profile='tool-semantics-v1')
        grant = compiler.compile(d.TrustedTaskRequest('Publish the supplied text on my webpage'), r)
        packet = json.loads(llm.client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        entry = packet['available_tools']['post_webpage']
        self.assertEqual(entry['effect'], 'external_send')
        self.assertEqual(entry['sink'], 'public_output')
        self.assertEqual(entry['parameters']['required'], ['url', 'content'])
        self.assertEqual(entry['parameters']['properties']['url']['type'], 'string')
        self.assertEqual(grant.allowed_tools, frozenset({'get_webpage', 'post_webpage'}))
        original = grant.tool_catalog_sha256
        r.functions['post_webpage'].description += ' New host semantics.'
        changed = compiler.compile(d.TrustedTaskRequest('Publish the supplied text on my webpage'), r)
        self.assertNotEqual(original, changed.tool_catalog_sha256)

    def test_legacy_and_protocol_preserve_original_authorization_catalog(self):
        for profile in ('legacy', 'protocol-v1'):
            llm = model('{"tools":[]}')
            d.ToolAuthorizationCompiler(llm, prompt_profile=profile).compile(d.TrustedTaskRequest('Read the webpage'), runtime())
            packet = json.loads(llm.client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
            self.assertIsInstance(packet['available_tools']['post_webpage'], str)

    def test_profiles_are_explicit_and_unknown_profile_fails_before_clients(self):
        with patch.object(d, 'create_openai_client') as create:
            with self.assertRaises(ValueError):
                d.make_defended_pipeline(prompt_profile='invented')
            create.assert_not_called()

    def test_candidate_policies_are_separate_and_keep_json_contract(self):
        for profile in ('legacy', 'protocol-v1', 'tool-semantics-v1', 'source-context-v1'):
            checker = d.ActionSecurityChecker(model('{}'), prompt_profile=profile)
            if profile != 'legacy':
                self.assertIn('[A-Za-z0-9_.:-]{1,96}', checker.SYSTEM_POLICY)
            if profile == 'source-context-v1':
                self.assertIn('current operation', checker.SYSTEM_POLICY)
                self.assertIn('does not authorize a new task', checker.SYSTEM_POLICY)
            self.assertIn('JSON', checker.SYSTEM_POLICY)
