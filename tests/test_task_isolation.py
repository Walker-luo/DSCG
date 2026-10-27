"""Top-level task boundaries must not inherit BASEINTENT authority or history."""
import unittest
from types import SimpleNamespace
from agentdojo import agent_pipeline
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from baseintent.pipelines.defended import (
    TaskIsolatedPipeline, PermissionSandbox, ReferenceMonitor, SandboxPolicyState,
)


class Recorder(agent_pipeline.BasePipelineElement):
    def __init__(self):
        self.contexts = []
    def query(self, query, runtime, env, messages, extra_args):
        self.contexts.append(extra_args)
        extra_args.setdefault('baseintent_action_ledger', []).append(query)
        extra_args.setdefault('baseintent_audit_decisions', []).append(query)
        return query, runtime, env, messages, extra_args


class TaskIsolationTests(unittest.TestCase):
    def test_order_repeated_query_and_cross_runtime_have_fresh_context(self):
        for order in [('A','B'), ('B','A'), ('A','A')]:
            with self.subTest(order=order):
                recorder = Recorder()
                pipeline = TaskIsolatedPipeline([recorder, recorder])
                results = [pipeline.query(q, FunctionsRuntime()) for q in order]
                self.assertEqual(results[0][-1]['baseintent_action_ledger'], [order[0]] * 2)
                self.assertEqual(results[1][-1]['baseintent_action_ledger'], [order[1]] * 2)
                self.assertIs(recorder.contexts[0], recorder.contexts[1])
                self.assertIsNot(recorder.contexts[1], recorder.contexts[2])
                self.assertNotEqual(results[0][-1]['baseintent_task_id'], results[1][-1]['baseintent_task_id'])

    def test_explicit_context_is_copied_and_stale_authority_is_removed(self):
        supplied = {'host_value': 7, 'baseintent_action_ledger':['old'],
                    '_baseintent_pending_batch': object(), 'baseintent_authorization': {'allowed_tools':['x']}}
        result = TaskIsolatedPipeline([Recorder()]).query('new', FunctionsRuntime(), extra_args=supplied)
        self.assertEqual(result[-1]['host_value'], 7)
        self.assertEqual(result[-1]['baseintent_action_ledger'], ['new'])
        self.assertNotIn('_baseintent_pending_batch', result[-1])
        self.assertEqual(supplied['baseintent_action_ledger'], ['old'])

    def test_boundary_revokes_ticket_sandbox_and_authorization_cache(self):
        sandbox = PermissionSandbox(['x'])
        monitor = ReferenceMonitor(sandbox, False)
        call = FunctionCall(function='x', args={}, id='x')
        ticket = monitor._issue('old', call, 'old-contract')
        executor = SimpleNamespace(sandbox=sandbox, _authorization_cache_key='old',
                                   _authorization_cache_contract=object())
        TaskIsolatedPipeline([Recorder()], executor=executor, monitor=monitor).query('new', FunctionsRuntime())
        self.assertFalse(monitor.consume(ticket, call))
        self.assertEqual(sandbox.policy_state, SandboxPolicyState.UNINITIALIZED)
        self.assertIsNone(executor._authorization_cache_key)
        self.assertIsNone(executor._authorization_cache_contract)

    def test_exception_still_revokes_unspent_tickets(self):
        monitor = ReferenceMonitor(None, False)
        call = FunctionCall(function='x', args={}, id='x')
        tickets = []
        class Broken(agent_pipeline.BasePipelineElement):
            def query(self, *state):
                tickets.append(monitor._issue('new', call, 'c'))
                raise RuntimeError('failed task')
        with self.assertRaises(RuntimeError):
            TaskIsolatedPipeline([Broken()], monitor=monitor).query('new', FunctionsRuntime())
        self.assertFalse(monitor.consume(tickets[0], call))

    def test_trace_save_failure_cannot_leave_ticket_live_or_hide_task_error(self):
        from unittest.mock import Mock, patch
        from agentdojo.logging import TraceLogger
        monitor=ReferenceMonitor(None,False)
        call=FunctionCall(function='x',args={},id='1');tickets=[]
        class Broken(agent_pipeline.BasePipelineElement):
            def query(self,*state):
                tickets.append(monitor._issue('action',call,'contract'))
                raise RuntimeError('original task error')
        logger=Mock(spec=TraceLogger);logger.context={};logger.save.side_effect=OSError('disk full')
        with patch('baseintent.pipelines.defended.logging.Logger') as manager:
            manager.return_value.get.return_value=logger
            with self.assertRaisesRegex(RuntimeError,'original task error'):
                TaskIsolatedPipeline([Broken()],monitor=monitor).query('new',FunctionsRuntime())
        self.assertFalse(monitor.consume(tickets[0],call))
