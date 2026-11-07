"""Offline reporting reads both layouts without adding excluded tasks to metrics."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ARTIFACTS = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261030_fliter_goal_impl/offline/readers'


class FlatReportReaderTests(unittest.TestCase):
    def setUp(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(dir=ARTIFACTS)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def test_outcome_flat_precedes_legacy_and_retains_raw_grades(self):
        from experiments.common.benchmark_outcomes import project_outcomes
        flat = self.put('u/i.json', {'messages': [], 'error': 'ServerError', 'utility': False, 'security': True})
        self.put('u/attack/i.json', {'messages': [], 'error': None})
        before = flat.read_bytes()
        row = project_outcomes({('u', 'i'): False}, {('u', 'i'): True}, self.root,
                               'attack', run_attack=True)[('u', 'i')]
        self.assertIsNone(row['utility_success'])
        self.assertTrue(row['native_attack_success'])
        self.assertEqual(before, flat.read_bytes())

    def test_selection_summary_preserves_goal_checkpoint_and_has_no_failure_cases(self):
        from experiments.common.partial_reporting import write_run_overview
        self.put('run_manifest.json', {'schema_version': 'dscg.run.v3'})
        self.put('summary.json', {'goal_checkpoint': {'done': ['i0']}})
        selection = dict(targets_before=3, targets_retained=1, removed_pairs=6, goal_enabled=True,
            goal_pipeline='baseline', fliter_excluded=[dict(suite='workspace', injection_task_id='i0',
                reason='fliter', status='excluded', removed_pairs=3)],
            goal_checks=[dict(suite='workspace', injection_task_id='i1', status='failed',
                cost={'models': [{'generation': {'total_tokens': 7, 'failed_calls': 0, 'missing_usage_calls': 0}}]})])
        with patch('experiments.common.partial_reporting.get_backend', return_value=SimpleNamespace(label='fixture', suites=['workspace'])), patch('experiments.common.partial_reporting.benchmark_identity', return_value={'revision': 'fixture'}):
            summary, failures = write_run_overview(self.root, ['attack'], [], [], [], selection_report=selection)
        structured = json.loads((self.root / 'summary.json').read_text())
        self.assertEqual(structured['goal_checkpoint'], {'done': ['i0']})
        self.assertEqual(structured['selection_report'], selection)
        self.assertEqual(failures.read_text(), '')
        self.assertIn('**fliter 排除**', summary.read_text())
        self.assertIn('**GOAL 失败（不计分）**', summary.read_text())
        self.assertIn('不能直接比较不同分母原始成功率', summary.read_text())
        self.assertEqual(structured['cost_summary']['combined']['known_total_tokens'], 7)
        self.assertEqual(structured['cost_summary']['goal']['unknown_usage_records'], 0)
        self.assertEqual(structured['configuration_path'], 'run_manifest.json')

    def test_aborted_group_without_suite_report_has_unknown_usage(self):
        from experiments.common.partial_reporting import write_run_overview
        run = dict(attack='attack', failed_suite='workspace', status='error', error_type='ConnectionError')
        with patch('experiments.common.partial_reporting.get_backend', return_value=SimpleNamespace(label='fixture', suites=['workspace'])), patch(
                'experiments.common.partial_reporting.benchmark_identity', return_value={'revision': 'fixture'}):
            write_run_overview(self.root, ['attack'], ['workspace'], [run], [])
        summary = json.loads((self.root / 'summary.json').read_text())
        self.assertEqual(summary['cost_summary']['scored'], {'known_total_tokens': 0, 'unknown_usage_records': 1})
        self.assertEqual(summary['cost_summary']['combined']['unknown_usage_records'], 1)
        self.assertNotIn('task_counts', summary)
        report = dict(attack='attack', suite='workspace', cases=[], status='partial', task_errors=1,
            tsr_failures=0, asr_successes=0, metric_unavailable=0, summary_path='attack/workspace/summary.json',
            summary=dict(attack_kind='targeted', overhead={'total_tokens': 0}, sec_overhead={'total_tokens': 0},
                api_accounting={'main': {'generation': {'failed_calls': 1}}}, task_counts=dict(
                    total_tasks=0, attacked_tasks=0, planned_tasks=1, utility_passed=0, utility_valid=0)))
        with patch('experiments.common.partial_reporting.get_backend', return_value=SimpleNamespace(label='fixture', suites=['workspace'])), patch(
                'experiments.common.partial_reporting.benchmark_identity', return_value={'revision': 'fixture'}):
            write_run_overview(self.root, ['attack'], ['workspace'], [run], [report])
        summary = json.loads((self.root / 'summary.json').read_text())
        self.assertEqual(summary['cost_summary']['scored']['unknown_usage_records'], 1)

    def test_failed_final_publication_preserves_durable_goal_checkpoint(self):
        from experiments.common.partial_reporting import write_run_overview
        checkpoint = self.put('summary.json', {'selection_report': {'goal_checks': [
            {'suite': 'workspace', 'injection_task_id': 'i0', 'status': 'passed'}]}})
        original = checkpoint.read_bytes()
        with patch('experiments.common.partial_reporting.get_backend', return_value=SimpleNamespace(label='fixture', suites=[])), patch(
                'experiments.common.partial_reporting.benchmark_identity', return_value={'revision': 'fixture'}), patch(
                'experiments.common.partial_reporting.os.replace', side_effect=OSError('fixture publication failure')):
            with self.assertRaises(OSError):
                write_run_overview(self.root, [], [], [], [])
        self.assertEqual(checkpoint.read_bytes(), original)
        self.assertFalse(list(self.root.glob('.run-summary-*')))

    def test_routing_new_root_manifest_reads_only_retained_scored_tasks(self):
        from experiments.common.routing_reports import collect_routing_summary
        benchmark = {'id': 'fixture', 'revision': 'one', 'suite_version': 'v1.2'}
        binding = dict(benchmark=benchmark, attack='attack', profile='baseline',
                       task_selection={'users': ['u'], 'injections': ['i']})
        self.put('run_manifest.json', {'schema_version': 'dscg.run.v3', 'common': {'benchmark': benchmark},
                                     'groups': {'attack/sample': binding}})
        self.put('attack/sample/u/i.json', dict(suite_name='sample', user_task_id='u',
            injection_task_id='i', attack_type='attack', utility=True, security=False,
            error=None, messages=[]))
        self.put('attack/sample/excluded.json', {'error': 'GOAL failure'})
        report = collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'], 1)
        self.assertEqual(report['coverage']['read_traces'], 1)
        self.assertEqual(report['coverage'].get('missing_traces', 0), 0)

    def test_routing_derives_post_goal_scope_and_rejects_invalid_checkpoints(self):
        from experiments.common.routing_reports import collect_routing_summary
        benchmark = {'id': 'fixture', 'revision': 'one', 'suite_version': 'v1.2'}
        binding = dict(benchmark=benchmark, attack='attack', profile='baseline', selection_options={'goal': True},
                       task_selection={'users': ['u'], 'injections': ['i2', 'i0', 'i1']})
        self.put('run_manifest.json', {'schema_version': 'dscg.run.v3', 'common': {'benchmark': benchmark},
                                     'groups': {'attack/sample': binding}})
        checks = [dict(suite='sample', injection_task_id=target, status=status)
                  for target, status in [('i0', 'failed'), ('i1', 'error'), ('i2', 'passed')]]
        self.put('summary.json', {'selection_report': {'goal_checks': checks}})
        self.put('attack/sample/summary.json', dict(benchmark=benchmark, suite_name='sample',
            task_selection={'user_task_ids': ['u'], 'injection_task_ids': ['i2']}))
        self.put('attack/sample/u/i2.json', dict(suite_name='sample', user_task_id='u',
            injection_task_id='i2', attack_type='attack', utility=True, security=False, error=None, messages=[]))
        report = collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'], 1)
        self.assertEqual(report['coverage']['read_traces'], 1)
        self.assertEqual(report['coverage'].get('missing_traces', 0), 0)
        self.assertEqual(report['coverage'].get('inconsistent_traces', 0), 0)
        for invalid in (checks[:1], checks + [checks[0]], [dict(c, status='running') for c in checks],
                        [dict(c, status='invented') for c in checks]):
            with self.subTest(checkpoint=invalid):
                self.put('summary.json', {'selection_report': {'goal_checks': invalid}})
                report = collect_routing_summary(self.root)
                self.assertEqual(report['groups'][0]['status'], 'unknown_scope')
                self.assertEqual(report['coverage'].get('missing_traces', 0), 0)

    def test_dashboard_stats_read_flat_and_historical_traces(self):
        from dashboard.evaluation import trace_stats
        for location in ('pipeline/sample/u/i.json', 'legacy/sample/u/attack/i.json'):
            self.put(location, {'messages': [], 'error': None, 'dscg_input_isolation': {'isolated_returns': 2}})
        for pipeline in ('pipeline', 'legacy'):
            stats = trace_stats(self.root, pipeline, 'sample', 'attack', [('u', 'i')])
            self.assertEqual(stats['trace_records'], 1)
            self.assertEqual(stats['isolation_records'], 1)

    def test_reuse_snapshot_preserves_flat_old_and_goal_incomplete_bytes(self):
        from experiments.common.benchmark_reuse import snapshot_run_evidence
        from pydantic import ValidationError
        names = ['attack/sample/user_task_0/injection_task_0.json',
                 'attack/sample/user_task_1/attack/injection_task_0.json',
                 'attack/sample/injection_task_0.json']
        paths = [self.put(name, {'messages': [], 'error': None}) for name in names]
        self.put('summary.json', {'goal_checkpoint': {'incomplete': True}})
        failure = ValidationError.from_exception_data('TaskResults',
            [{'type': 'missing', 'loc': ('utility',), 'input': {}}])
        destination = self.root / 'reuse' / 'fixture'
        with patch('experiments.common.benchmark_reuse.load_task_results', side_effect=failure), patch(
                'experiments.common.task_storage.load_task_results', side_effect=failure):
            records = snapshot_run_evidence(self.root, destination)
        self.assertEqual({row['path'] for row in records}, set(names + ['summary.json']))
        for path in paths:
            self.assertEqual(path.read_bytes(), (destination / 'snapshot' / path.relative_to(self.root)).read_bytes())


if __name__ == '__main__':
    unittest.main()
