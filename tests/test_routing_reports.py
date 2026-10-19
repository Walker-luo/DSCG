"""Result reporting with synthetic stored traces; no backend or model requests."""
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'workshop/artifacts/20261019_result_reports'
BENCHMARK = {'id': 'fixture-backend', 'revision': 'fixture-1', 'suite_version': 'v1.2'}


def event(**changes):
    row = dict(mode='shadow', eligible=True, would_bypass=True, actual_bypass=False,
               artifact_sha256='a' * 64, model_config_sha256='b' * 64,
               score=0.1, threshold=0.2, route_reason='BELOW_CALIBRATED_THRESHOLD',
               semantic_audit_calls=1, semantic_audit_tokens=100,
               router_total_latency_ms=2, raw_audit_decision='allow', final_monitor_decision='allow')
    row.update(changes)
    return row


def trace(events, user='u0', **changes):
    row = dict(suite_name='sample', user_task_id=user, injection_task_id='i0', attack_type='attack',
               utility=True, security=False, error=None, benchmark_version='v1.2',
               dscg_framework={'audit_router_mode': 'shadow', 'audit_router_artifact_sha256': 'a' * 64,
                               'audit_router_config_sha256': 'b' * 64, 'audit_router_load_error': None},
               messages=[{'role': 'assistant', 'tool_calls': [{'id': 'c', 'function': 'read'}]}])
    if events is not None:
        row['dscg_router_events'] = events
    row.update(changes)
    return row


class RoutingReportTests(unittest.TestCase):
    def setUp(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        self.tmp = TemporaryDirectory(dir=ARTIFACTS)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def fixture(self, rows):
        self.put('attack_manifest.json', dict(benchmark=BENCHMARK, model_id='fixture',
                 attacks=['attack'], suites=['sample'], task_scope='full'))
        self.put('attack/sample/run_manifest.json', dict(benchmark=BENCHMARK, attack='attack',
            audit_router_mode='shadow', audit_router_artifact_sha256='a' * 64,
            task_selection={'users': list(rows), 'injections': ['i0']}))
        for user, row in rows.items():
            self.put(f'attack/sample/{user}/attack/i0.json', row)

    def test_event_weighted_statistics_exclude_preflight_and_snapshots(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0': trace([event(), event(score=.8, would_bypass=False, router_total_latency_ms=20)], 'u0'),
                      'u1': trace([event(eligible=False, score=None, threshold=None, would_bypass=False,
                                         route_reason='INCOMPLETE_INPUT', router_total_latency_ms=3)], 'u1')})
        self.put('attack/sample/i0/none/none.json', trace([event(actual_bypass=True)]))
        self.put('validation/snapshot/attack/sample/u0/attack/i0.json', trace([event()]))
        report = collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'], 2)
        self.assertEqual(report['totals']['candidate_batches'], 3)
        self.assertEqual(report['totals']['eligible_batches'], 2)
        self.assertAlmostEqual(report['totals']['eligible_rate'], 2/3)
        self.assertEqual(report['totals']['router_latency_p95_ms'], 3)
        self.assertEqual(report['totals']['shadow_would_save_tokens'], 100)
        self.assertEqual(report['totals']['shadow_audit_cross_counts'], {'allow': 1})

    def test_unknown_scope_does_not_report_zero_audit_calls(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0': trace([event()])})
        path = self.root/'attack/sample/run_manifest.json'
        for selection in ({'users':['u0']}, {}):
            binding = json.loads(path.read_text())
            binding['task_selection'] = selection
            path.write_text(json.dumps(binding))
            report = collect_routing_summary(self.root)
            self.assertEqual(report['groups'][0]['status'], 'unknown_scope')
            self.assertIsNone(report['totals']['semantic_audit_calls'])
            self.assertIsNone(report['groups'][0]['totals']['semantic_audit_calls'])
            self.assertIsNone(report['totals']['shadow_would_save_tokens'])

    def test_missing_or_invalid_trace_makes_effective_shadow_savings_unknown(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0': trace([event()]), 'u1': trace([event()], 'u1')})
        path = self.root/'attack/sample/u1/attack/i0.json'
        path.unlink()
        report = collect_routing_summary(self.root)
        self.assertEqual(report['totals']['known_shadow_would_save_tokens'], 100)
        self.assertIsNone(report['totals']['shadow_would_save_tokens'])
        self.assertIsNone(report['groups'][0]['totals']['shadow_would_save_tokens'])
        self.put('attack/sample/u1/attack/i0.json', trace([event(eligible=None)], 'u1'))
        report = collect_routing_summary(self.root)
        self.assertIsNone(report['totals']['shadow_would_save_tokens'])
        self.assertIsNone(report['configurations'][0]['totals']['shadow_would_save_tokens'])

    def test_missing_calibration_is_unknown_not_zero_savings(self):
        from experiments.common.routing_reports import collect_routing_summary
        row = trace([event(artifact_sha256=None, threshold=None, would_bypass=False,
                           route_reason='ARTIFACT_INVALID_OR_MISSING')])
        row['dscg_framework'].update(audit_router_artifact_sha256=None, audit_router_load_error='ARTIFACT_MISSING')
        self.fixture({'u0': row})
        report = collect_routing_summary(self.root)
        self.assertEqual(report['totals']['eligible_batches'], 1)
        self.assertIsNone(report['totals']['shadow_would_save_tokens'])
        self.assertEqual(report['configurations'][0]['calibration_status'], 'uncalibrated')

    def test_no_candidates_missing_corrupt_and_wrong_identity_are_distinct(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0': trace(None, 'u0', messages=[{'role':'assistant','tool_calls':None,'content':'done'}]),
                      'u1': trace(None, 'u1'), 'u2': trace([event()], 'foreign'),
                      'u3': trace([event()], 'u3'), 'u4': trace([event()], 'u4')})
        (self.root/'attack/sample/u3/attack/i0.json').write_text('{broken')
        (self.root/'attack/sample/u4/attack/i0.json').unlink()
        report = collect_routing_summary(self.root)
        coverage = report['coverage']
        for name in ('no_candidate_traces','unrecorded_traces','inconsistent_traces','corrupt_traces','missing_traces'):
            self.assertEqual(coverage[name], 1, name)
        self.assertEqual(report['totals']['candidate_batches'], 0)

    def test_modes_configurations_and_public_bypasses_do_not_merge(self):
        from experiments.common.routing_reports import collect_routing_summary
        a = trace([event(), event(eligible=False, would_bypass=False, score=None, threshold=None,
                  original_public_bypass=True, route_reason='READ_AUDIT_BYPASS', semantic_audit_calls=0, semantic_audit_tokens=0)])
        b = trace([event(mode='selective', actual_bypass=True, semantic_audit_calls=0, semantic_audit_tokens=0)], 'u1')
        b['dscg_framework']['audit_router_mode'] = 'selective'
        self.fixture({'u0':a,'u1':b})
        report = collect_routing_summary(self.root)
        self.assertEqual(len(report['configurations']), 2)
        self.assertEqual(report['totals']['original_public_bypass_batches'], 1)
        self.assertEqual(report['totals']['actual_bypass_batches'], 1)
        self.assertIsNone(report['totals']['actual_total_tokens_saved'])

    def test_outputs_are_additive_refresh_owned_only_and_no_symlink_escape(self):
        from experiments.common.routing_reports import write_routing_summary, collect_routing_summary
        self.fixture({'u0':trace([event()])})
        legacy = self.root/'summary.md';legacy.write_text('old human report')
        before = {p.relative_to(self.root):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        write_routing_summary(self.root)
        self.assertEqual({p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file()} - set(before),
                         {Path('l3_router_summary.json'),Path('l3_router_summary.md')})
        for name, content in before.items():self.assertEqual((self.root/name).read_bytes(),content)
        with self.assertRaises(FileExistsError):write_routing_summary(self.root)
        write_routing_summary(self.root, refresh=True)
        p=self.root/'attack/sample/u0/attack/i0.json';p.unlink()
        p.symlink_to(ROOT/'README.md')
        self.assertEqual(collect_routing_summary(self.root)['coverage']['outside_run_traces'],1)
        (self.root/'l3_router_summary.md').write_text('my own notes')
        with self.assertRaises(ValueError):write_routing_summary(self.root,refresh=True)

    def test_dashboard_clean_off_and_backend_independent_reading(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.put('overall_results.json', dict(benchmark=BENCHMARK, config={'origin':False,'run_attack':False},
            suites=[{'suite_name':'sample','pipeline_name':'native','benchmark':BENCHMARK,
                     'task_selection':{'user_task_ids':['u0'],'injection_task_ids':[]},
                     'framework':{'audit_router_mode':'off'}}]))
        row=trace(None,injection_task_id=None,attack_type='none')
        row['dscg_framework']['audit_router_mode']='off'
        row['dscg_layer_routing']={'semantic_audit_calls':2}
        self.put('native/sample/u0/none/none.json',row)
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['disabled_traces'],1)
        self.assertEqual(report['totals']['semantic_audit_calls'],2)
        self.assertEqual(report['benchmark']['id'],'fixture-backend')

    def test_incomplete_metadata_and_missing_traces_never_report_zero_calls(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event()])})
        (self.root/'attack/sample/u0/attack/i0.json').unlink()
        report=collect_routing_summary(self.root)
        self.assertIsNone(report['totals']['semantic_audit_calls'])
        self.assertIn('missing_trace', report['issue_counts'])
        (self.root/'attack/sample/summary.json').write_text('{bad')
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'],1)
        self.assertIn('metadata_unreadable',report['issue_counts'])

    def test_invalid_event_flags_and_mode_conflicts_remain_unknown(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event(eligible='yes'),event(mode='selective',actual_bypass=True)])})
        report=collect_routing_summary(self.root)
        self.assertEqual(report['totals']['invalid_event_records'],2)
        self.assertEqual(report['totals']['eligible_batches'],0)
        self.assertIsNone(report['totals']['semantic_audit_calls'])

    def test_active_run_lock_and_unowned_output_do_not_change_any_file(self):
        from experiments.common.routing_reports import write_routing_summary
        import fcntl
        self.fixture({'u0':trace([event()])})
        with (self.root/'.benchmark.lock').open('w') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError,'active'):
                write_routing_summary(self.root)
        self.assertFalse((self.root/'l3_router_summary.json').exists())
        self.assertFalse((self.root/'l3_router_summary.md').exists())

    def test_same_native_baseline_does_not_fabricate_shadow_savings(self):
        from experiments.common.routing_reports import collect_routing_summary
        row=trace(None)
        row.pop('dscg_framework')
        self.fixture({'u0':row})
        path=self.root/'attack/sample/run_manifest.json';binding=json.loads(path.read_text())
        binding.update(profile='baseline',audit_router_mode='off');path.write_text(json.dumps(binding))
        report=collect_routing_summary(self.root)
        self.assertIsNone(report['totals']['shadow_would_save_tokens'])

    def test_summary_binding_conflict_does_not_pool_foreign_scope(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event()])})
        self.put('attack/sample/summary.json', {'suite_name':'sample', 'benchmark':{**BENCHMARK,'id':'other'}})
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['inconsistent_traces'],1)
        self.assertEqual(report['totals']['candidate_batches'],0)

    def test_interrupted_plan_keeps_unfinished_declared_groups(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event()])})
        (self.root/'attack_manifest.json').unlink()
        self.put('benchmark_plan.json',dict(benchmark=BENCHMARK,attacks=['attack'],suites=['sample'],task_scope='full'))
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'],1)

    def test_missing_flags_are_unknown_and_inconsistent_bypass_is_not_counted(self):
        from experiments.common.routing_reports import collect_routing_summary
        missing=event();missing.pop('eligible')
        self.fixture({'u0':trace([missing,event(eligible=False,actual_bypass=False,would_bypass=True)])})
        report=collect_routing_summary(self.root)
        self.assertEqual(report['totals']['invalid_event_records'],2)
        self.assertEqual(report['totals']['would_bypass_batches'],0)

    def test_off_audit_cost_is_unknown_and_public_reads_are_not_audit_unknowns(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event(eligible=False, would_bypass=False, original_public_bypass=True,
                                       route_reason='READ_AUDIT_BYPASS', raw_audit_decision=None, semantic_audit_calls=0,semantic_audit_tokens=0)])})
        report=collect_routing_summary(self.root)
        self.assertEqual(report['totals']['raw_audit_decision_counts'],{'not_audited':1})

    def test_raw_declared_backend_conflict_and_artifact_conflict_are_reported(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.fixture({'u0':trace([event()],benchmark={**BENCHMARK,'id':'other'}),
                      'u1':trace([event(artifact_sha256='foreign')], 'u1')})
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['inconsistent_traces'],1)
        self.assertEqual(report['totals']['invalid_event_records'],1)

    def test_unfinished_cohort_empty_target_group_uses_declared_selection(self):
        from experiments.common.routing_reports import collect_routing_summary
        self.put('screened_run_manifest.json',dict(benchmark=BENCHMARK,attacks=['attack'],requested_suites=['sample'],
                  selected_tasks={'sample':{'user_task_ids':['u0'],'injection_task_ids':[]}},task_scope='screened'))
        report=collect_routing_summary(self.root)
        self.assertEqual(report['coverage']['planned_traces'],0)
        self.assertNotIn('incomplete_task_selection',report['issue_counts'])

    def test_dashboard_overview_adapter_preserves_source_and_uses_native_trace_path(self):
        from types import SimpleNamespace
        from dashboard.evaluation import build_suite_report
        self.put('native/sample/u0/none/none.json',trace(None,user='u0',attack_type='none',injection_task_id=None))
        summary = dict(suite_name='sample', pipeline_name='native', benchmark=BENCHMARK,
            task_selection={'user_task_ids':['u0'],'injection_task_ids':[]},
            task_counts={'total_tasks':1,'utility_passed':0,'utility_valid':1,'attacked_tasks':0,'security_valid':0},
            overhead={'total_tokens':10},metrics={'utility_rate':0,'attack_success_rate':None})
        original=deepcopy(summary)
        records=[dict(user_task_id='u0',injection_task_id='None',model_id='fixture',utility_success=False,
                      attack_success=None,sample_status='valid',execution_error=False)]
        report=build_suite_report(self.root,summary,records,SimpleNamespace(user_tasks={},injection_tasks={}),{'run_attack':False})
        self.assertEqual(summary,original)
        self.assertEqual(report['summary']['task_counts']['planned_tasks'],1)
        self.assertEqual(report['summary_path'],'sample/summary.json')
        self.assertEqual(report['cases'][0]['trace_path'],'native/sample/u0/none/none.json')
