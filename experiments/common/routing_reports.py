"""Stored-run routing reports. Standard library only; never loads a backend/model.

This is observational bookkeeping, not a calibration or security oracle.
Only task IDs declared by a run are read; recursive globbing would include
preflight tasks, snapshots and old invocations and is deliberately avoided.
"""
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import re
import tempfile

SCHEMA = 'baseintent.l3-router-summary.v2'
THRESHOLD_POLICY = 'threshold-read-v1'
READ_POLICY = 'read-purpose-v2'
DIRECT_POLICIES = {THRESHOLD_POLICY, READ_POLICY}
MARKER = '<!-- ' + SCHEMA + ' -->'
OWNED_SCHEMAS = (SCHEMA, 'baseintent.l3-router-summary.v1', 'dscg.l3-router-summary.v1', 'dscg.l3-router-summary.v2')
JSON_NAME, MD_NAME = 'l3_router_summary.json', 'l3_router_summary.md'
MODES = {'off', 'shadow', 'selective', 'baseline', 'unknown'}
COVERAGE = ('planned_traces', 'read_traces', 'event_traces', 'no_candidate_traces',
            'disabled_traces', 'unrecorded_traces', 'missing_traces', 'corrupt_traces',
            'inconsistent_traces', 'outside_run_traces', 'diagnostic_unavailable_traces')


def _component(value):
    if not isinstance(value, str) or not re.fullmatch(r'[\w.-]{1,255}', value) or value in {'.', '..'}:
        raise ValueError('invalid stored path component')
    return value


def _safe(root, path):
    if not path.resolve().is_relative_to(root):
        raise ValueError('path outside run')
    return path


def _read(root, path):
    from baseintent.task_diagnostics import load_task_trace
    value = load_task_trace(_safe(root, path))
    if not isinstance(value, dict):
        raise ValueError('expected JSON object')
    return value


def _backend(value):
    if not isinstance(value, dict) or not isinstance(value.get('id'), str):
        return None
    return {k: value[k] for k in ('id', 'repository', 'revision', 'suite_version', 'package_version') if isinstance(value.get(k), str)}


def _conflicts(left, right):
    return bool(left and right and any(left[k] != right[k] for k in left.keys() & right.keys()))


def _number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _count(value):
    return type(value) is int and value >= 0


def _distribution(values):
    values = sorted(values)
    return {'count': len(values), 'min': values[0] if values else None,
            'p50': values[int((len(values)-1)*.5)] if values else None,
            'p95': values[int((len(values)-1)*.95)] if values else None,
            'max': values[-1] if values else None}


class _Stats:
    def __init__(self):
        self.c = Counter()
        self.reasons, self.decisions, self.monitor, self.cross, self.monitor_cross = (Counter() for _ in range(5))
        self.scores, self.latencies, self.thresholds = [], [], set()
        self.shadow_samples = []
        self.threshold_shadow = False
        self.uncalibrated = False

    def observe_config(self, config):
        self.c['shadow_traces'] += config['mode'] == 'shadow'
        self.threshold_shadow |= config['mode'] == 'shadow' and config.get('policy_version') == THRESHOLD_POLICY
        if config['mode'] == 'shadow' and config.get('policy_version') not in DIRECT_POLICIES and (not config['artifact_sha256'] or config['load_error']):
            self.uncalibrated = True

    def event(self, row):
        self.c['candidate_batches'] += 1
        reason = row.get('route_reason')
        self.reasons[reason if isinstance(reason, str) and len(reason) <= 128 else 'unknown'] += 1
        public = row.get('original_public_bypass') is True or reason == 'READ_AUDIT_BYPASS'
        rejected = reason == 'L2_PRECHECK_DENY'
        self.c['original_public_bypass_batches'] += public
        self.c['l2_rejected_batches'] += rejected
        router = not public and not rejected
        self.c['previously_audited_batches'] += router
        self.c['eligible_batches'] += router and row.get('eligible') is True
        self.c['would_bypass_batches'] += router and row.get('would_bypass') is True
        self.c['actual_bypass_batches'] += router and row.get('actual_bypass') is True
        calls = row.get('semantic_audit_calls')
        if _count(calls):
            self.c['known_semantic_audit_calls'] += calls
        else:
            self.c['unknown_audit_call_records'] += 1
        cost = row.get('semantic_audit_tokens')
        if router:
            if _count(cost):
                self.c['known_semantic_audit_tokens'] += cost
            else:
                self.c['unknown_audit_cost_batches'] += 1
            latency = row.get('router_total_latency_ms')
            if _number(latency) and latency >= 0:
                self.latencies.append(latency)
            if row.get('eligible') is True:
                score, threshold = row.get('score'), row.get('threshold')
                if _number(score):
                    self.scores.append(score)
                if _number(threshold):
                    self.thresholds.add(threshold)
                if row.get('mode') == 'shadow' and (
                        threshold is None or reason in {'INCOMPATIBLE_ARTIFACT', 'ARTIFACT_INVALID_OR_MISSING', 'NO_CERTIFIED_THRESHOLD', 'ROUTER_ERROR'}):
                    self.uncalibrated = True
        if (router and row.get('mode') == 'shadow' and row.get('policy_version') == THRESHOLD_POLICY
                and row.get('eligible') is True and _number(row.get('score')) and 0 <= row['score'] <= 1):
            self.shadow_samples.append(row)
        decision = row.get('raw_audit_decision')
        decision = decision if decision in ('allow', 'deny', 'abstain') else 'not_audited' if calls == 0 else 'unknown'
        self.decisions[decision] += 1
        monitor = row.get('final_monitor_decision')
        self.monitor[monitor if monitor in ('allow', 'deny') else 'unknown'] += 1
        if row.get('mode') == 'shadow' and router and row.get('would_bypass') is True:
            self.cross[decision] += 1
            self.monitor_cross[monitor if monitor in ('allow', 'deny') else 'unknown'] += 1
            self.c['shadow_protocol_failure_batches'] += row.get('mediation_failure_stage') == 'model_protocol'
            self.c['shadow_request_failure_batches'] += row.get('mediation_failure_stage') == 'model_request'
            self.c['shadow_record_failure_batches'] += row.get('mediation_failure_stage') == 'audit_record'
            if _count(cost):
                self.c['known_shadow_would_save_tokens'] += cost
            else:
                self.c['unknown_shadow_cost_batches'] += 1

    def threshold_sweep(self, configured_threshold):
        if not self.threshold_shadow:
            return []
        candidates = {.65, .70, .75}
        if _number(configured_threshold):
            candidates.add(configured_threshold)
        result = []
        for threshold in sorted(candidates):
            selected = [e for e in self.shadow_samples if e['score'] < threshold]
            decisions = Counter(e.get('raw_audit_decision', 'unknown') for e in selected)
            costs = [e.get('semantic_audit_tokens') for e in selected]
            known = [c for c in costs if _count(c)]
            incomplete = (len(known) != len(selected) or self.c['unknown_audit_cost_traces']
                          or self.c['unknown_scope_groups'] or self.c['invalid_event_records'])
            result.append(dict(threshold=threshold, eligible_batches=self.c['eligible_batches'],
                would_bypass_batches=len(selected),
                rate_of_audited_batches=len(selected)/self.c['previously_audited_batches'] if self.c['previously_audited_batches'] else None,
                rate_of_eligible_batches=len(selected)/self.c['eligible_batches'] if self.c['eligible_batches'] else None,
                audit_decision_counts=dict(decisions),
                protocol_failure_batches=sum(e.get('audit_parser_status') == 'failure' for e in selected),
                unknown_protocol_batches=sum(e.get('audit_parser_status') not in ('ok','failure') for e in selected),
                known_shadow_would_save_tokens=sum(known), unknown_cost_batches=len(selected)-len(known),
                shadow_would_save_tokens=None if incomplete else sum(known)))
        return result

    def finish(self, scores=False):
        keys = ('candidate_batches', 'previously_audited_batches', 'eligible_batches',
                'original_public_bypass_batches', 'l2_rejected_batches', 'actual_bypass_batches',
                'would_bypass_batches', 'known_semantic_audit_calls', 'unknown_audit_call_records',
                'known_semantic_audit_tokens', 'unknown_audit_cost_batches', 'unknown_shadow_cost_batches',
                'invalid_event_records', 'unknown_audit_cost_traces', 'unknown_scope_groups',
                'known_shadow_would_save_tokens', 'shadow_protocol_failure_batches', 'shadow_record_failure_batches', 'shadow_request_failure_batches')
        result = {k: self.c[k] for k in keys}
        n, eligible = self.c['previously_audited_batches'], self.c['eligible_batches']
        result.update(eligible_rate=eligible/n if n else None,
                      new_bypass_rate=self.c['actual_bypass_batches']/n if n else None,
                      eligible_bypass_rate=self.c['actual_bypass_batches']/eligible if eligible else None,
                      semantic_audit_calls=None if self.c['unknown_audit_call_records'] else self.c['known_semantic_audit_calls'],
                      shadow_would_save_tokens=None if not self.c['shadow_traces'] or self.uncalibrated or self.c['unknown_shadow_cost_batches'] or self.c['unknown_audit_cost_traces'] or self.c['unknown_scope_groups'] else self.c['known_shadow_would_save_tokens'],
                      actual_total_tokens_saved=None, route_reason_counts=dict(self.reasons),
                      raw_audit_decision_counts=dict(self.decisions), final_monitor_decision_counts=dict(self.monitor),
                      shadow_audit_cross_counts=dict(self.cross), shadow_monitor_cross_counts=dict(self.monitor_cross),
                      router_latency_p50_ms=_distribution(self.latencies)['p50'],
                      router_latency_p95_ms=_distribution(self.latencies)['p95'])
        if scores:
            result.update(score_distribution=_distribution(self.scores), thresholds=sorted(self.thresholds))
        return result


def _ids(value):
    if not isinstance(value, list) or len(set(value)) != len(value):
        raise ValueError('missing or duplicate task IDs')
    return [_component(v) for v in value]


def _descriptors(root):
    """Use declared CLI groups or Dashboard summaries, never the active registry."""
    plan_path = (root/'attack_manifest.json' if (root/'attack_manifest.json').exists() else
                 root/'benchmark_plan.json' if (root/'benchmark_plan.json').exists() else
                 root/'screened_run_manifest.json')
    if plan_path.exists():
        manifest = _read(root, plan_path)
        if 'suites' not in manifest and isinstance(manifest.get('requested_suites'), list):
            manifest = {**manifest, 'suites': manifest['requested_suites']}
        groups = []
        for attack in _ids(manifest.get('attacks')) or ['none']:
            for suite in _ids(manifest.get('suites')):
                directory = root/attack/suite
                errors = []
                def optional(name):
                    try:
                        return _read(root, directory/name) if (directory/name).exists() else {}
                    except (OSError, ValueError):
                        errors.append(name)
                        return {}
                binding, summary = optional('run_manifest.json'), optional('summary.json')
                binding = binding or summary.get('run_manifest', {})
                selection = (binding.get('task_selection') or summary.get('task_selection')
                             or manifest.get('selected_tasks', {}).get(suite, {}))
                groups.append(dict(attack=attack, suite=suite, directory=directory, binding=binding,
                    summary=summary, selection=selection, baseline=binding.get('profile') == 'baseline', metadata_errors=errors))
        return manifest, groups
    if (root/'overall_results.json').exists():
        manifest = _read(root, root/'overall_results.json')
        config = manifest.get('config', {})
        groups = []
        for summary in manifest.get('suites', []):
            suite = _component(summary['suite_name'])
            attacked = config.get('run_attack')
            if not isinstance(attacked, bool):
                raise ValueError('Dashboard run lacks explicit attack scope')
            attack = _component(config.get('attack_name', 'unknown')) if attacked else 'none'
            pipeline = _component(str(summary['pipeline_name']).replace('/', '_'))
            groups.append(dict(attack=attack, suite=suite, directory=root/pipeline/suite,
                selection=summary.get('task_selection', {}), baseline=config.get('origin') is True,
                binding=summary.get('framework') or {}, summary=summary))
        return manifest, groups
    # Historical flat/attack layouts can be summarized from explicit suite metadata.
    groups = []
    for path in sorted(list(root.glob('*/summary.json')) + list(root.glob('*/*/summary.json'))):
        if path.relative_to(root).parts[0] in {'validation','reuse','execution','compatibility','archive'}:
            continue
        summary = _read(root, path)
        if not summary.get('suite_name'):
            continue
        binding = summary.get('run_manifest') or {}
        selection = binding.get('task_selection') or summary.get('task_selection', {})
        attack = binding.get('attack', selection.get('attack'))
        if attack is None and summary.get('attack_kind') == 'none':
            attack = 'none'
        groups.append(dict(attack=_component(attack), suite=_component(summary['suite_name']), directory=path.parent,
            binding=binding, summary=summary, selection=selection, baseline=binding.get('profile') == 'baseline'))
    if not groups:
        raise ValueError('no declared run/task metadata; directory names cannot establish scope')
    return {'benchmark': None}, groups


def _config(frame, binding, baseline, benchmark):
    frame = {**binding, **frame}
    mode = frame.get('audit_router_mode', 'baseline' if baseline else 'unknown')
    def text(value):
        return value if isinstance(value, str) and len(value) <= 200 else None
    return {'mode': mode if isinstance(mode,str) and mode in MODES else 'unknown', 'benchmark': benchmark,
            'artifact_sha256': text(frame.get('audit_router_artifact_sha256')),
            'policy_version': text(frame.get('audit_router_policy_version')),
            'threshold': frame.get('audit_router_threshold') if _number(frame.get('audit_router_threshold')) else None,
            'config_sha256': text(frame.get('audit_router_config_sha256')),
            'prompt_profile': text(frame.get('prompt_profile')) or 'unrecorded',
            'prompt_profile_sha256': text(frame.get('prompt_profile_sha256')),
            'framework_version': text(frame.get('framework_version', frame.get('defense_version'))),
            'load_error': text(frame.get('audit_router_load_error'))}


def collect_routing_summary(run_dir):
    root = Path(run_dir).resolve(strict=True)
    manifest, descriptors = _descriptors(root)
    benchmark = _backend(manifest.get('benchmark'))
    total, coverage, configs, groups = _Stats(), Counter(), {}, []
    issues, issue_counts = [], Counter()
    comparison_stats = {}

    def issue(kind, path, detail=None):
        issue_counts[kind] += 1
        if len(issues) < 100:
            issues.append({'kind': kind, 'path': str(path.relative_to(root)), 'detail': detail})

    seen = set()
    for descriptor in descriptors:
        attack, suite = descriptor['attack'], descriptor['suite']
        binding, summary, selection = descriptor['binding'], descriptor['summary'], descriptor['selection']
        stats, covered = _Stats(), Counter()
        group_backend = _backend(binding.get('benchmark')) or _backend(summary.get('benchmark'))
        group_id = attack + '/' + suite
        for name in descriptor.get('metadata_errors', []):
            issue('metadata_unreadable', descriptor['directory']/name)
        try:
            users = _ids(selection.get('users', selection.get('user_task_ids')))
            injections = _ids(selection.get('injections', selection.get('injection_task_ids'))) if attack != 'none' else ['none']
        except (ValueError, TypeError):
            issue('incomplete_task_selection', descriptor['directory'])
            for acc in (total, stats):
                acc.c['unknown_scope_groups'] += 1
                acc.c['unknown_audit_call_records'] += 1
            groups.append({'attack': attack, 'suite': suite, 'coverage': dict(covered), 'totals': stats.finish(), 'status': 'unknown_scope'})
            continue
        summary_selection = summary.get('task_selection', {})
        selection_conflict = any(summary_selection.get(name) is not None and summary_selection[name] != expected
                                 for name,expected in [('user_task_ids',users), ('injection_task_ids',injections if attack != 'none' else [])])
        if (_conflicts(benchmark, group_backend)
                or _conflicts(_backend(binding.get('benchmark')), _backend(summary.get('benchmark')))
                or (summary.get('suite_name') is not None and summary['suite_name'] != suite)
                or selection_conflict):
            issue('benchmark_conflict', descriptor['directory'])
            covered['planned_traces'] = covered['inconsistent_traces'] = len(users)*len(injections)
            stats.c['unknown_audit_call_records'] += covered['planned_traces']
            total.c['unknown_audit_call_records'] += covered['planned_traces']
            stats.c['unknown_audit_cost_traces'] += covered['planned_traces']
            total.c['unknown_audit_cost_traces'] += covered['planned_traces']
            coverage.update(covered)
            groups.append({'attack': attack, 'suite': suite, 'coverage': dict(covered), 'totals': stats.finish(), 'status': 'inconsistent'})
            continue
        for user in users:
            for injection in injections:
                path = descriptor['directory']/user/attack/(injection+'.json')
                key = (attack, suite, user, injection)
                if key in seen:
                    raise ValueError('duplicate declared task scope')
                seen.add(key)
                covered['planned_traces'] += 1
                try:
                    _safe(root, path)
                except ValueError:
                    covered['outside_run_traces'] += 1; issue('outside_run_trace', path)
                    for acc in (total,stats):
                        acc.c['unknown_audit_call_records'] += 1; acc.c['unknown_audit_cost_traces'] += 1
                    continue
                if not path.exists():
                    covered['missing_traces'] += 1; issue('missing_trace', path)
                    for acc in (total,stats):
                        acc.c['unknown_audit_call_records'] += 1; acc.c['unknown_audit_cost_traces'] += 1
                    continue
                try:
                    raw = _read(root, path)
                except (OSError, ValueError):
                    covered['corrupt_traces'] += 1; issue('corrupt_trace', path)
                    for acc in (total,stats):
                        acc.c['unknown_audit_call_records'] += 1; acc.c['unknown_audit_cost_traces'] += 1
                    continue
                covered['read_traces'] += 1
                if raw.get('baseintent_diagnostics_status') in ('missing','corrupt','invalid_reference','incomplete'):
                    covered['diagnostic_unavailable_traces'] += 1
                    issue('diagnostic_'+raw['baseintent_diagnostics_status'],path)
                    for acc in (total,stats):
                        acc.c['unknown_audit_call_records'] += 1
                        acc.c['unknown_audit_cost_traces'] += 1
                    continue
                raw_injection = raw.get('injection_task_id') or 'none'
                if (raw.get('suite_name') != suite or raw.get('user_task_id') != user
                        or raw_injection != injection or raw.get('attack_type') != attack
                        or (benchmark and raw.get('benchmark_version') and benchmark.get('suite_version')
                            and raw['benchmark_version'] != benchmark['suite_version'])
                        or _conflicts(benchmark, _backend(raw.get('benchmark')))):
                    covered['inconsistent_traces'] += 1; issue('trace_identity_conflict', path)
                    for acc in (total,stats):
                        acc.c['unknown_audit_call_records'] += 1; acc.c['unknown_audit_cost_traces'] += 1
                    continue
                frame = raw.get('baseintent_framework') if isinstance(raw.get('baseintent_framework'), dict) else {}
                config = _config(frame, binding, descriptor['baseline'], group_backend or benchmark)
                config_key = json.dumps(config, sort_keys=True, ensure_ascii=False)
                if config_key not in configs:
                    configs[config_key] = {'configuration': config, 'stats': _Stats(), 'groups': set(), 'traces': 0}
                selected = configs[config_key]
                selected['traces'] += 1; selected['groups'].add(group_id)
                comparison_key = (group_id, config_key)
                if comparison_key not in comparison_stats:
                    comparison_stats[comparison_key] = dict(attack=attack, suite=suite, configuration=config, stats=_Stats())
                group_config = comparison_stats[comparison_key]
                accumulators = (total, stats, selected['stats'], group_config['stats'])
                for acc in accumulators: acc.observe_config(config)
                events = raw.get('baseintent_router_events')
                if isinstance(events, list) and events:
                    covered['event_traces'] += 1
                    for row in events:
                        if (not isinstance(row, dict) or row.get('mode') not in ('shadow','selective')
                                or row.get('mode') != config['mode']
                                or (row.get('actual_bypass') is True and row.get('mode') != 'selective')
                                or any(type(row.get(k)) is not bool for k in ('eligible','would_bypass','actual_bypass'))
                                or (row.get('would_bypass') is True and row.get('eligible') is not True)
                                or (row.get('actual_bypass') is True and row.get('would_bypass') is not True)
                                or (row.get('eligible') is True and row.get('artifact_sha256') != config['artifact_sha256'])
                                or (config['policy_version'] == THRESHOLD_POLICY and (
                                    row.get('eligible') is True and (row.get('policy_version') != THRESHOLD_POLICY
                                        or row.get('threshold') != config['threshold'])))
                                or (row.get('policy_version') == THRESHOLD_POLICY and config['policy_version'] != THRESHOLD_POLICY)
                                or (config['policy_version'] == READ_POLICY and row.get('eligible') is True and (
                                    row.get('policy_version') != READ_POLICY or row.get('threshold_applied') is not False))
                                or (row.get('policy_version') == READ_POLICY and config['policy_version'] != READ_POLICY)
                                or any(k in row and type(row[k]) is not bool for k in ('eligible','would_bypass','actual_bypass','original_public_bypass'))
                                or (row.get('model_config_sha256') and config['config_sha256'] and row['model_config_sha256'] != config['config_sha256'])):
                            issue('invalid_event', path)
                            for acc in accumulators:
                                acc.c['invalid_event_records'] += 1
                                acc.c['unknown_audit_call_records'] += 1
                                acc.c['unknown_audit_cost_traces'] += 1
                            continue
                        for acc in accumulators: acc.event(row)
                elif config['mode'] in {'off', 'baseline'}:
                    covered['disabled_traces'] += 1
                    routing = raw.get('baseintent_layer_routing')
                    calls = routing.get('semantic_audit_calls') if isinstance(routing,dict) else None
                    for acc in accumulators:
                        if descriptor['baseline'] or frame.get('use_security_checker') is False:
                            continue
                        if _count(calls): acc.c['known_semantic_audit_calls'] += calls
                        else: acc.c['unknown_audit_call_records'] += 1
                        if calls != 0: acc.c['unknown_audit_cost_traces'] += 1
                else:
                    messages = raw.get('messages')
                    complete = (isinstance(messages, list) and bool(messages)
                                and isinstance(messages[-1], dict) and messages[-1].get('role') == 'assistant'
                                and not raw.get('error') and isinstance(raw.get('utility'), bool)
                                and not raw.get('messages_truncated')
                                and all(isinstance(m, dict) for m in messages))
                    if complete and not any(m.get('tool_calls') for m in messages):
                        covered['no_candidate_traces'] += 1
                    else:
                        covered['unrecorded_traces'] += 1; issue('routing_unrecorded', path)
                        for acc in accumulators:
                            acc.c['unknown_audit_call_records'] += 1
                            acc.c['unknown_audit_cost_traces'] += 1
        coverage.update(covered)
        groups.append({'attack': attack, 'suite': suite, 'coverage': {k: covered[k] for k in COVERAGE},
                       'totals': stats.finish(), 'status': 'partial' if any(covered[k] for k in COVERAGE[5:]) or stats.c['invalid_event_records'] else 'recorded'})
    # Missing traces cannot be assigned to a configuration: conservatively retain
    # uncertainty for every configuration observed in the affected group.
    by_group = {row['attack']+'/'+row['suite']: row for row in groups}
    for selected in configs.values():
        for key in ('unknown_audit_cost_traces','unknown_audit_call_records','unknown_scope_groups','invalid_event_records'):
            unknown = sum(by_group[group]['totals'].get(key, 0) for group in selected['groups'])
            selected['stats'].c[key] = max(selected['stats'].c[key], unknown)
    configurations = []
    for selected in configs.values():
        conf, stat = selected['configuration'], selected['stats']
        calibration = ('disabled' if conf['mode'] in {'off','baseline'} else
                       'empirical_threshold_uncalibrated' if conf['policy_version'] == THRESHOLD_POLICY else
                       'rule_based_unvalidated' if conf['policy_version'] == READ_POLICY else
                       'uncalibrated' if not conf['artifact_sha256'] or conf['load_error'] else
                       'calibrated' if stat.thresholds else 'threshold_unobserved_or_uncertified')
        configurations.append({'configuration': conf, 'calibration_status': calibration,
                               'groups': sorted(selected['groups']), 'traces': selected['traces'],
                               'totals': stat.finish(scores=True)})
    # Missing/corrupt traces have no per-trace configuration; retain their group uncertainty.
    by_group = {row['attack']+'/'+row['suite']: row for row in groups}
    for value in comparison_stats.values():
        parent = by_group[value['attack']+'/'+value['suite']]['totals']
        for key in ('unknown_audit_cost_traces','unknown_audit_call_records','unknown_scope_groups','invalid_event_records'):
            value['stats'].c[key] = max(value['stats'].c[key], parent.get(key, 0))
    totals = total.finish()
    if benchmark is None:
        for name in ('eligible_rate','new_bypass_rate','eligible_bypass_rate'):
            totals[name] = None
    return {'schema_version': SCHEMA, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'benchmark': benchmark, 'run_name': root.name, 'task_scope': manifest.get('task_scope', 'recorded'),
            'coverage': {k: coverage[k] for k in COVERAGE}, 'totals': totals,
            'aggregation_status': 'recorded_run_identity' if benchmark else 'benchmark_identity_unavailable_rates_not_pooled',
            'groups': groups, 'configurations': configurations,
            'threshold_comparisons': [dict(attack=v['attack'], suite=v['suite'], configuration=v['configuration'],
                thresholds=v['stats'].threshold_sweep(v['configuration']['threshold']))
                for v in comparison_stats.values() if v['stats'].threshold_shadow],
            'issue_counts': dict(issue_counts), 'issues': issues, 'issues_truncated': sum(issue_counts.values()) > len(issues),
            'limitations': ['Recorded scored traces only; preflight, snapshots and current backend registry excluded.',
                           'Legacy missing calibration remains unknown; threshold-read-v1 uses an empirical threshold. read-purpose-v2 selects by rules; scores/thresholds are diagnostic, without independent safety validation.',
                           'Audit disagreement is not a security oracle; selective actual Token savings remain unknown.',
                           'Audit Tokens here exclude preflight; do not add them again to run total Tokens.']}


def render_routing_summary(report):
    def cell(value):
        return str(value if value is not None else '未知').replace('|','\\|').replace('\n',' ')
    total, coverage = report['totals'], report['coverage']
    eligible_rate = f"{total['eligible_rate']:.2%}" if total['eligible_rate'] is not None else '未知'
    lines = [MARKER, '# L3 路由汇总', '', f"运行：{cell(report['run_name'])}；基准：{cell((report['benchmark'] or {}).get('id'))}。", '',
             f"计分轨迹计划 {coverage['planned_traces']}；读取 {coverage['read_traces']}；含事件 {coverage['event_traces']}；无候选 {coverage['no_candidate_traces']}；路由关闭/基线 {coverage['disabled_traces']}。", '',
             f"已记录候选批次 {total['candidate_batches']}；原公开免审 {total['original_public_bypass_batches']}；L2拒绝 {total['l2_rejected_batches']}；路由适用 {total['eligible_batches']}；模拟免审 {total['would_bypass_batches']}；实际选择性免审 {total['actual_bypass_batches']}。", '',
             f"已记录的路由适用率：{eligible_rate}（分母排除原公开免审及L2前置拒绝）；不是安全通过率。", '',
             f"语义审计调用：{cell(total['semantic_audit_calls'])}；已记录计分轨迹审计Token：{total['known_semantic_audit_tokens']}；成本未知批次：{total['unknown_audit_cost_batches']}，另有{total['unknown_audit_cost_traces']}条轨迹缺少可用成本事件。", '',
             f"Shadow有效模拟节省Token：{cell(total['shadow_would_save_tokens'])}；selective实际节省：未知（无反事实）。", '',
             f"候选免审的Shadow实际Monitor结果：{cell(total.get('shadow_monitor_cross_counts'))}；模型请求失败批次：{cell(total.get('shadow_request_failure_batches'))}；模型协议失败批次：{cell(total.get('shadow_protocol_failure_batches'))}；记录校验失败批次：{cell(total.get('shadow_record_failure_batches'))}。分歧不是安全标签。", '',
             '未校准时不能将would_bypass=false或已记录零值解释为已验证无收益。费用不含GOAL预检，不与运行总Token重复相加。', '',
             '## 攻击 / 场景', '',
             '| 攻击 | 场景 | 计划/读取/含事件 | 无候选/未记录 | 候选/原公开免审 | 适用/模拟/实际免审 | 审计调用 |',
             '| --- | --- | --- | --- | --- | --- | --- |']
    for group in report['groups']:
        c, t = group['coverage'], group['totals']
        values = [group['attack'],group['suite'],f"{c.get('planned_traces',0)}/{c.get('read_traces',0)}/{c.get('event_traces',0)}",
                  f"{c.get('no_candidate_traces',0)}/{c.get('unrecorded_traces',0)}",f"{t['candidate_batches']}/{t['original_public_bypass_batches']}",
                  f"{t['eligible_batches']}/{t['would_bypass_batches']}/{t['actual_bypass_batches']}",t['semantic_audit_calls']]
        lines.append('| '+' | '.join(map(cell, values))+' |')
    lines.extend(['', '## 实际模式与配置（风险分数/阈值不跨配置合并）', '',
                  '| 模式 | 提示候选 | 校准状态 | 配置hash / 策略或artifact | 轨迹 | 阈值 | 风险分数P50/P95 | 延迟P50/P95毫秒 |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |'])
    for row in report['configurations']:
        c, t = row['configuration'], row['totals']
        d = t['score_distribution']
        values = [c['mode'],c['prompt_profile'],('经验阈值、未独立校准' if row['calibration_status'] == 'empirical_threshold_uncalibrated' else row['calibration_status']),
                  f"{str(c['config_sha256'] or 'unknown')[:12]} / {c['policy_version'] if c['policy_version'] in DIRECT_POLICIES else str(c['artifact_sha256'] or 'missing')[:12]}",row['traces'],t['thresholds'],
                  f"{cell(d['p50'])}/{cell(d['p95'])}", f"{cell(t['router_latency_p50_ms'])}/{cell(t['router_latency_p95_ms'])}"]
        lines.append('| '+' | '.join(map(cell, values))+' |')
    lines.extend(['', '## Shadow经验阈值比较（未独立校准）', '',
                  '以下为已记录历史轨迹上的模拟；审计分歧不是误放率，Token不是实际节省。', '',
                  '| 攻击/场景 | 配置 | 阈值 | 模拟免审/适用 | 占原审计比例 | 审计判决 | 协议失败/未知 | 已知模拟Token/未知批次 | 模拟Token |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- | --- |'])
    for group in report.get('threshold_comparisons', []):
        for row in group['thresholds']:
            rate = row['rate_of_audited_batches']
            values = [group['attack']+'/'+group['suite'], (group['configuration']['config_sha256'] or 'unknown')[:12],
                      row['threshold'], f"{row['would_bypass_batches']}/{row['eligible_batches']}",
                      f'{rate:.2%}' if rate is not None else None, row['audit_decision_counts'],
                      f"{row['protocol_failure_batches']}/{row['unknown_protocol_batches']}",
                      f"{row['known_shadow_would_save_tokens']}/{row['unknown_cost_batches']}", row['shadow_would_save_tokens']]
            lines.append('| '+' | '.join(map(cell, values))+' |')
    lines.extend(['','## 路由原因',''])
    lines.extend(f'- {cell(k)}：{v}' for k,v in sorted(total['route_reason_counts'].items()))
    lines.extend(['','## Shadow模拟免审与实际审计判断','',
                  '以下仅为判断分歧，不是误放率或安全标签：', '', cell(total['shadow_audit_cross_counts']), '',
                  '## 完整性', '', cell(report['coverage']), '', cell(report['issue_counts']), '',
                  f'完整配置、分组、统计与问题明细见 [{JSON_NAME}]({JSON_NAME})。'])
    return '\n'.join(lines)+'\n'


@contextmanager
def _report_lock(root, check_running):
    handles = []
    try:
        if check_running:
            for name in ('.benchmark.lock', '.screening.lock'):
                path = root/name
                if path.exists():
                    handle = os.open(_safe(root,path), os.O_RDONLY)
                    handles.append(handle)
                    fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        handle = os.open(root, os.O_RDONLY)
        handles.append(handle)
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise ValueError('run or report generation is active') from exc
    finally:
        for handle in reversed(handles):
            os.close(handle)


def write_routing_summary(run_dir, *, refresh=False, check_running=True):
    root = Path(run_dir).resolve(strict=True)
    with _report_lock(root, check_running):
        output, markdown = root/JSON_NAME, root/MD_NAME
        for path in (output, markdown):
            if path.is_symlink():
                raise ValueError('report output must not be a symlink')
            if path.exists():
                if not refresh:
                    raise FileExistsError('routing report exists; use --refresh for tool-owned reports')
                owned = (_read(root,path).get('schema_version') in OWNED_SCHEMAS if path == output
                         else path.read_text(encoding='utf-8').startswith(tuple('<!-- '+schema+' -->\n' for schema in OWNED_SCHEMAS)))
                if not owned:
                    raise ValueError('refusing to replace a file not generated by this reporter')
        report = collect_routing_summary(root)
        data = [(output, json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'),
                (markdown, render_routing_summary(report))]
        pending = []
        try:
            for target, text in data:
                with tempfile.NamedTemporaryFile('w', encoding='utf-8',dir=root,prefix='.l3-report-',suffix='.tmp',delete=False) as stream:
                    pending.append((Path(stream.name),target));stream.write(text)
            for source,target in pending:os.replace(source,target)
        finally:
            for source,_ in pending:source.unlink(missing_ok=True)
        return report
