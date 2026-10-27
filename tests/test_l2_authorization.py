# Frozen v3.4 controls; intent-flow defaults are tested in test_intent_flow*.py.
from authorization_fixture import adapt_client
"""Tool exposure must not change authority or the registered execution runtime."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from baseintent.pipelines import defended as d
from baseintent.tool_metadata import set_tool_metadata, register_tool_metadata


def response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        content=text, refusal=None), finish_reason='stop')])


def make_runtime():
    runtime = FunctionsRuntime()
    effects = []

    @runtime.register_function
    def read_data() -> str:
        """Read task facts."""
        effects.append('read')
        return 'facts'

    @runtime.register_function
    def write_data() -> str:
        """Update an existing record."""
        effects.append('write')
        return 'updated'

    set_tool_metadata(runtime, {
        'read_data': dict(effect='read', source='local', sink='none', sensitivity='public',
                          idempotent=True, reversible=False),
        'write_data': dict(effect='write', source='local', sink='none', sensitivity='internal',
                           idempotent=False, reversible=False),
    })
    return runtime, effects


def model(*outputs):
    client = Mock()
    client.chat.completions.create.side_effect = [response(x) for x in outputs]
    adapt_client(client)
    planner = SimpleNamespace(name='offline', client=client, views=[])

    def query(q, runtime, env, messages, extra):
        planner.views.append(runtime)
        return q, runtime, env, [*messages, {'role': 'assistant', 'content': [], 'tool_calls': []}], extra

    planner.query = query
    return planner


def user(text):
    return {'role': 'user', 'content': [{'type': 'text', 'content': text}]}


class PlanningViewTests(unittest.TestCase):
    def test_planner_sees_only_authorized_valid_tools_and_execution_runtime_is_intact(self):
        runtime, effects = make_runtime()
        llm = model('{"tools": []}')
        sandbox = d.PermissionSandbox()
        state = d.OurFrameExecutor(llm, sandbox, planning_tool_view=True, prompt_profile='legacy-v34').query(
            'Read facts', runtime, EmptyEnv(), [user('Read facts')], {})
        view = llm.views[0]
        self.assertEqual(set(view.functions), {'read_data'})
        self.assertEqual(set(runtime.functions), {'read_data', 'write_data'})
        self.assertIs(state[1], runtime)
        self.assertIsNot(view, runtime)
        view.functions.clear()
        self.assertEqual(len(runtime.functions), 2)
        self.assertEqual(effects, [])

    def test_compilation_failure_exposes_no_tools(self):
        runtime, _ = make_runtime()
        llm = model('not JSON')
        sandbox = d.PermissionSandbox(['write_data'])
        d.OurFrameExecutor(llm, sandbox, planning_tool_view=True, prompt_profile='legacy-v34').query(
            'Read facts', runtime, EmptyEnv(), [user('Read facts')], {})
        self.assertEqual(llm.views[0].functions, {})
        self.assertEqual(sandbox.policy_state, d.SandboxPolicyState.ERROR)

    def test_new_user_turn_replaces_previous_write_grant(self):
        runtime, _ = make_runtime()
        llm = model('{"tools": ["write_data"]}', '{"tools": []}')
        sandbox = d.PermissionSandbox()
        executor = d.OurFrameExecutor(llm, sandbox, planning_tool_view=True, prompt_profile='legacy-v34')
        first = executor.query('Update record', runtime, EmptyEnv(), [user('Update record')], {})
        self.assertTrue(sandbox.assess('write_data', runtime)[0])
        executor.query('Now only read', runtime, EmptyEnv(), [*first[3], user('Now only read')], first[4])
        self.assertFalse(sandbox.assess('write_data', runtime)[0])
        self.assertEqual(set(llm.views[-1].functions), {'read_data'})
        self.assertEqual(llm.client.chat.completions.create.call_count, 2)

    def test_registered_tool_semantic_change_invalidates_existing_grant_without_recompile(self):
        runtime, _ = make_runtime()
        llm = model('{"tools": ["write_data"]}')
        sandbox = d.PermissionSandbox()
        executor = d.OurFrameExecutor(llm, sandbox, planning_tool_view=True, prompt_profile='legacy-v34')
        state = executor.query('Update record', runtime, EmptyEnv(), [user('Update record')], {})
        runtime.functions['write_data'].description = 'Create a different payment.'
        allowed, reason = sandbox.assess('write_data', runtime)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'AUTH_CATALOG_CHANGED')
        executor.query(*state)
        self.assertEqual(llm.views[-1].functions, {})
        self.assertEqual(llm.client.chat.completions.create.call_count, 1)

    def test_missing_metadata_is_not_visible_even_if_host_allowlist_contains_tool(self):
        from baseintent.l2_authorization import planning_runtime_view
        runtime, _ = make_runtime()
        runtime._baseintent_tool_metadata.pop('write_data')
        view, stats = planning_runtime_view(runtime, {'read_data', 'write_data'})
        self.assertEqual(set(view.functions), {'read_data'})
        self.assertEqual(stats['catalog_tools'], 2)
        self.assertEqual(stats['visible_tools'], 1)

    def test_invented_hidden_call_still_hits_precheck_and_never_executes(self):
        runtime, effects = make_runtime()
        llm = model('{"tools": []}')
        sandbox = d.PermissionSandbox()
        state = d.OurFrameExecutor(llm, sandbox, planning_tool_view=True, prompt_profile='legacy-v34').query(
            'Read facts', runtime, EmptyEnv(), [user('Read facts')], {})
        state[3].append({'role': 'assistant', 'content': [], 'tool_calls': [
            FunctionCall(function='write_data', args={}, id='invented')]})
        precheck = d.ToolAuthorizationPrecheck(sandbox)
        monitor = d.ReferenceMonitor(sandbox, False, precheck=precheck)
        for component in (precheck, monitor, d.TicketedToolsExecutor(monitor)):
            state = component.query(*state)
        self.assertEqual(effects, [])
        self.assertEqual(state[4]['baseintent_action_ledger'][0]['state'], 'blocked')

    def test_catalog_change_after_approval_cannot_execute_replacement(self):
        runtime, effects = make_runtime()
        sandbox = d.PermissionSandbox()
        grant = d.ToolAuthorizationCompiler(model('{"tools": ["write_data"]}'), prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest('Update record'), runtime)
        sandbox.install_contract(grant)
        call = FunctionCall(function='write_data', args={}, id='approved')
        state = ('Update record', runtime, EmptyEnv(), [
            {'role': 'assistant', 'content': [], 'tool_calls': [call]}], {})
        precheck = d.ToolAuthorizationPrecheck(sandbox)
        monitor = d.ReferenceMonitor(sandbox, False, precheck=precheck)
        state = monitor.query(*precheck.query(*state))
        runtime.functions['write_data'].run = lambda: effects.append('replacement') or 'bad'
        state = d.TicketedToolsExecutor(monitor).query(*state)
        self.assertEqual(effects, [])
        self.assertIn('AUTH_CATALOG_CHANGED', state[3][-1]['error'])

    def test_planning_definition_edits_do_not_mutate_host_catalogue(self):
        from baseintent.l2_authorization import planning_runtime_view
        runtime, _ = make_runtime()
        description = runtime.functions['read_data'].description
        view, _ = planning_runtime_view(runtime, {'read_data'})
        view.functions['read_data'].description = 'Changed display text'
        self.assertEqual(runtime.functions['read_data'].description, description)

    def test_planning_schema_configuration_and_fields_are_isolated(self):
        from baseintent.l2_authorization import planning_runtime_view
        runtime, _ = make_runtime()
        view, _ = planning_runtime_view(runtime, {'read_data'})
        original = runtime.functions['read_data'].parameters
        shown = view.functions['read_data'].parameters
        self.assertIsNot(shown, original)
        shown.model_config['title'] = 'display-only'
        shown.model_fields['display_only'] = None
        self.assertNotEqual(original.model_config.get('title'), 'display-only')
        self.assertNotIn('display_only', original.model_fields)

    def test_dependency_code_change_after_ticket_issue_prevents_execution(self):
        from agentdojo.functions_runtime import Depends
        from typing import Annotated
        from pydantic import BaseModel
        runtime, effects = FunctionsRuntime(), []
        class Env(BaseModel):
            value: str = 'original'
        def extract(env):
            return env.value
        @runtime.register_function
        def update(value: Annotated[str, Depends(extract)]) -> str:
            """Update a record using a host dependency."""
            effects.append(value)
            return value
        set_tool_metadata(runtime, {'update': dict(effect='write', source='local', sink='none',
                          sensitivity='internal', idempotent=False, reversible=False)})
        sandbox = d.PermissionSandbox()
        sandbox.install_contract(d.ToolAuthorizationCompiler(model('{"tools": ["update"]}'), prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest('Update record'), runtime))
        call = FunctionCall(function='update', args={}, id='dependency-change')
        state = ('Update record', runtime, Env(), [{'role': 'assistant', 'content': [], 'tool_calls': [call]}], {})
        precheck = d.ToolAuthorizationPrecheck(sandbox)
        monitor = d.ReferenceMonitor(sandbox, False, precheck=precheck)
        state = monitor.query(*precheck.query(*state))
        extract.__code__ = (lambda env: 'changed').__code__
        state = d.TicketedToolsExecutor(monitor).query(*state)
        self.assertEqual(effects, [])
        self.assertIn('AUTH_CATALOG_CHANGED', state[3][-1]['error'])

    def test_replacing_code_on_same_callable_invalidates_task_grant(self):
        runtime, effects = make_runtime()
        grant = d.ToolAuthorizationCompiler(model('{"tools": ["write_data"]}'), prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest('Update record'), runtime)
        sandbox = d.PermissionSandbox()
        sandbox.install_contract(grant)
        replacement = lambda: effects.append('replacement') or 'bad'
        runtime.functions['write_data'].run.__code__ = replacement.__code__
        self.assertEqual(sandbox.assess('write_data', runtime), (False, 'AUTH_CATALOG_CHANGED'))


class BoundedProfileTests(unittest.TestCase):
    request = 'Update the record, do not send.'

    def profile(self, **changes):
        from baseintent.l2_authorization import ToolAuthorizationProfile
        options = dict(name='fixture-update', request_patterns=(r'Update the record, do not send\.',),
                       allowed_seed_tools=frozenset({'write_data', 'read_data'}),
                       prerequisites=(('write_data', ('read_data',)),))
        options.update(changes)
        return ToolAuthorizationProfile(**options)

    def payload(self, **changes):
        data = {'tools': ['write_data'], 'prohibited_tools': [], 'evidence': [
            {'tool': 'write_data', 'kind': 'direct', 'span': 'Update the record'}]}
        data.update(changes)
        return json.dumps(data)

    def compile(self, payload, profile=None, request=None):
        runtime, _ = make_runtime()
        llm = model(payload)
        compiler = d.ToolAuthorizationCompiler(llm, authorization_profile=profile or self.profile(), prompt_profile='legacy-v34')
        return compiler.compile(d.TrustedTaskRequest(request or self.request), runtime), llm, runtime

    def test_profile_adds_only_host_required_reads_and_records_actual_evidence(self):
        grant, llm, _ = self.compile(self.payload())
        self.assertEqual(grant.allowed_tools, {'write_data', 'read_data'})
        self.assertEqual(grant.preparatory_read_tools, {'read_data'})
        self.assertEqual(grant.public_dict()['profile_status'], 'applied')
        self.assertEqual(llm.client.chat.completions.create.call_count, 1)

    def test_unrelated_reads_are_not_implicitly_granted_by_profile(self):
        runtime, _ = make_runtime()
        @runtime.register_function
        def read_secret() -> str:
            """Read unrelated secrets."""
            return 'secret'
        register_tool_metadata(runtime, 'read_secret', dict(effect='read', source='local', sink='none',
                          sensitivity='secret', idempotent=True, reversible=False))
        grant = d.ToolAuthorizationCompiler(model(self.payload()), authorization_profile=self.profile(), prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest(self.request), runtime)
        self.assertNotIn('read_secret', grant.allowed_tools)

    def test_forged_evidence_and_extra_protocol_fields_fail_closed(self):
        for payload in (self.payload(evidence=[{'tool': 'write_data', 'kind': 'direct', 'span': 'fabricated'}]),
                        self.payload(approved=True)):
            with self.subTest(payload=payload), self.assertRaises(d.AuthorizationCompilationError):
                self.compile(payload)

    def test_prohibited_required_read_is_a_conflict_not_silent_subtraction(self):
        payload = self.payload(prohibited_tools=['read_data'], evidence=[
            {'tool': 'write_data', 'kind': 'direct', 'span': 'Update the record'},
            {'tool': 'read_data', 'kind': 'prohibited', 'span': 'do not read facts'}])
        request = 'Update the record, do not read facts.'
        profile = self.profile(request_patterns=(r'Update the record, do not read facts\.',))
        with self.assertRaises(d.AuthorizationCompilationError) as error:
            self.compile(payload, profile, request)
        self.assertEqual(error.exception.reason_code, 'AUTH_CONSTRAINT_CONFLICT')

    def test_unmatched_task_uses_legacy_protocol_without_added_call(self):
        runtime, _ = make_runtime()
        llm = model('{"tools": []}')
        grant = d.ToolAuthorizationCompiler(llm, authorization_profile=self.profile(), prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest('Only read facts'), runtime)
        self.assertEqual(grant.allowed_tools, {'read_data'})
        self.assertEqual(grant.public_dict()['profile_status'], 'unsupported_task_fallback')
        self.assertEqual(llm.client.chat.completions.create.call_count, 1)

    def test_host_closure_cannot_auto_grant_a_write_or_external_sink(self):
        for target in ('write_data', 'read_data'):
            runtime, _ = make_runtime()
            if target == 'read_data':
                register_tool_metadata(runtime, 'read_data', dict(effect='read', source='local', sink='external_recipient',
                              sensitivity='public', idempotent=True, reversible=False))
            source = 'write_data' if target == 'read_data' else 'read_data'
            profile = self.profile(prerequisites=((source, (target,)),))
            llm = model(self.payload())
            with self.subTest(target=target), self.assertRaises(d.AuthorizationCompilationError):
                d.ToolAuthorizationCompiler(llm, authorization_profile=profile, prompt_profile='legacy-v34').compile(
                    d.TrustedTaskRequest(self.request), runtime)
            llm.client.chat.completions.create.assert_not_called()

    def test_dependency_cycles_are_rejected_at_host_configuration(self):
        with self.assertRaises(ValueError):
            self.profile(prerequisites=(('write_data', ('read_data',)), ('read_data', ('write_data',))))

    def test_read_only_catalogue_keeps_zero_model_calls(self):
        runtime, _ = make_runtime()
        runtime.functions.pop('write_data')
        profile = self.profile(allowed_seed_tools=frozenset({'read_data'}), prerequisites=(),
                               deterministic_reads=frozenset({'read_data'}))
        llm = model()
        grant = d.ToolAuthorizationCompiler(llm, authorization_profile=profile, prompt_profile='legacy-v34').compile(
            d.TrustedTaskRequest(self.request), runtime)
        self.assertEqual(grant.allowed_tools, {'read_data'})
        llm.client.chat.completions.create.assert_not_called()

