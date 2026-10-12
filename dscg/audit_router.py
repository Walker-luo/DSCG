"""Fixed lexical ranking and grouped calibration for opt-in internal-read auditing.

No learned weights, model calls, authorization expansion or provenance inference.
Artifacts and labels are trusted offline configuration, never tool-return data.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
from threading import Lock
import unicodedata

from dscg.tool_metadata import metadata_for_runtime, metadata_catalog_hash

SCHEMA = 'dscg.audit-router.algorithm.v1'
FEATURE_VERSION = 'lexical-max-v1'
INPUT_SCHEMA = 'dscg.audit-input.v1'
LABELS = {'safe_and_sufficient', 'unsafe', 'insufficient_or_ambiguous', 'unjudgeable'}
LABEL_SOURCES = {'independent_policy', 'environment_oracle', 'human_double_review'}
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
COMPLETENESS_FLAGS = frozenset({'request_truncated','description_truncated','history_truncated',
                              'tool_results_window_truncated','content_truncated','tool_result_error',
                              'arguments_truncated','arguments_nonfinite_or_unsupported'})


def validate_completeness_flags(flags):
    if not isinstance(flags,dict) or set(flags)!=COMPLETENESS_FLAGS or any(type(v) is not bool for v in flags.values()):
        raise ValueError('complete versioned boolean flag schema required')


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def normalized(value):
    text = unicodedata.normalize('NFKC', str(value))
    return ''.join(c if c in '\n\t' or c.isprintable() else f'\\u{ord(c):04x}' for c in text)


def argument_flags(value, depth=0):
    flags = dict(arguments_truncated=False, arguments_nonfinite_or_unsupported=False)
    if depth >= 4:
        flags['arguments_truncated'] = True
    elif value is None or isinstance(value, bool):
        pass
    elif isinstance(value, str):
        flags['arguments_truncated'] = len(normalized(value)) > 512
    elif isinstance(value, int):
        flags['arguments_nonfinite_or_unsupported'] = value.bit_length() > 4096
    elif isinstance(value, float):
        flags['arguments_nonfinite_or_unsupported'] = not math.isfinite(value)
    elif isinstance(value, (dict, list, tuple)):
        flags['arguments_truncated'] = len(value) > 64
        children = list(value.values())[:64] if isinstance(value, dict) else list(value)[:64]
        if isinstance(value, dict):
            flags['arguments_nonfinite_or_unsupported'] = any(not isinstance(k, str) for k in value)
            flags['arguments_truncated'] |= any(len(normalized(k)) > 128 for k in value if isinstance(k, str))
        for child in children:
            sub = argument_flags(child, depth + 1)
            for key in flags:
                flags[key] |= sub[key]
    else:
        flags['arguments_nonfinite_or_unsupported'] = True
    return flags


def _grams(text):
    text = ' '.join(normalized(text).casefold().split())
    if not text:
        return Counter()
    return Counter(text[i:i+3] for i in range(max(1, len(text)-2)))


def _cos(a, b):
    if not a or not b:
        return 0.0
    return min(1.0, sum(v*b.get(k, 0) for k, v in a.items()) /
               math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values())))


def _values(value):
    if isinstance(value, dict):
        return ' '.join(_values(v) for _, v in sorted(value.items()))
    if isinstance(value, (list, tuple)):
        return ' '.join(_values(v) for v in value)
    return '' if value is None else str(value)


def risk_score(packet):
    """Four unweighted signals, maximum aggregation; score is not a probability."""
    action = packet['current_actions'][0]
    task = _grams(packet['trusted_user_request'])
    host = _grams(action['host_tool_description'])
    args = _grams(_values(action['untrusted_argument_data']))
    recent = _grams(' '.join(r['content'] for r in packet.get('recent_tool_results', [])))
    support = task.keys() | host.keys()
    history = packet.get('action_history', [])
    features = {
        'task_tool_distance': 1 - _cos(task, host),
        'argument_novelty': sum(v for k, v in args.items() if k not in support)/sum(args.values()) if args else 0.0,
        'untrusted_support_gain': max(0.0, _cos(args, recent)-_cos(args, task)) if args else 0.0,
        'recent_failure_fraction': sum(r.get('state') in {'failed','blocked'} for r in history)/len(history) if history else 0.0,
    }
    return max(features.values()), features


def catalog_snapshot(runtime):
    statuses = metadata_for_runtime(runtime)
    tools = {}
    for name, spec in sorted(runtime.functions.items()):
        tools[name] = digest({'name': spec.name, 'description': spec.description,
                              'schema': spec.parameters.model_json_schema(),
                              'metadata': statuses[name].public_dict()})
    return digest({'risk': metadata_catalog_hash(statuses), 'tools': tools}), tools


def eligibility(packet, flags, runtime, calls, sandbox):
    try:validate_completeness_flags(flags)
    except ValueError:return False,'INVALID_COMPLETENESS_FLAGS'
    if sandbox is None or len(calls) != 1:
        return False, 'SINGLE_AUTHORIZED_INTERNAL_READ_REQUIRED'
    call = calls[0]; name = getattr(call, 'function', None) or call.get('function')
    if not sandbox.assess(name, runtime)[0]:
        return False, 'POLICY_NOT_ALLOWED'
    status = metadata_for_runtime(runtime).get(name)
    if status is None or not status.registered:
        return False, 'INVALID_METADATA'
    m = status.metadata
    if (m.effect, m.sink, m.sensitivity, m.idempotent) != ('read', 'none', 'internal', True):
        return False, 'NOT_INTERNAL_IDEMPOTENT_READ'
    if any(flags.values()):
        return False, 'INCOMPLETE_INPUT'
    if not packet['trusted_user_request'].strip() or not packet['current_actions'][0]['host_tool_description'].strip():
        return False, 'EMPTY_TASK_OR_DESCRIPTION'
    text_length = (len(packet['trusted_user_request']) + len(packet['current_actions'][0]['host_tool_description']) +
                   len(json.dumps(packet['current_actions'][0]['untrusted_argument_data'], ensure_ascii=True)) +
                   sum(len(r['content']) for r in packet.get('recent_tool_results', [])))
    if text_length > 12288:
        return False, 'INPUT_TOO_LARGE'
    try:
        runtime.functions[name].parameters.model_validate(getattr(call, 'args', None) if not isinstance(call, dict) else call['args'])
    except Exception:
        return False, 'INVALID_ARGUMENT_SCHEMA'
    return True, 'ELIGIBLE_INTERNAL_READ'


def binomial_upper(k, m, alpha):
    """One-sided exact Clopper–Pearson, using stable binomial-CDF inversion."""
    if not isinstance(k, int) or not isinstance(m, int) or not 0 <= k <= m or not 0 < alpha < 1:
        raise ValueError('invalid binomial inputs')
    if m == 0 or k == m:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(alpha)/m)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        p = (lo+hi)/2
        logs = [math.lgamma(m+1)-math.lgamma(i+1)-math.lgamma(m-i+1) +
                i*math.log(p)+(m-i)*math.log1p(-p) for i in range(k+1)]
        top = max(logs)
        logcdf = top + math.log(sum(math.exp(x-top) for x in logs))
        if logcdf > math.log(alpha):
            lo = p
        else:
            hi = p
    return hi


def calibrate(rows, grid, epsilon, delta):
    if not 0 < epsilon < 1 or not 0 < delta < 1 or not math.isfinite(epsilon+delta):
        raise ValueError('epsilon/delta must lie strictly between zero and one')
    if not grid or len(set(grid)) != len(grid) or any(type(t) not in (int,float) or not math.isfinite(t) or not 0 < t <= 1 for t in grid):
        raise ValueError('fixed unique threshold grid in (0,1] required')
    for row in rows:
        if (not isinstance(row.get('episode_group_id'),str) or not row['episode_group_id'] or
            row.get('label') not in LABELS or type(row.get('eligible')) is not bool or
            type(row.get('score')) not in (int,float) or not math.isfinite(row['score']) or not 0 <= row['score'] <= 1 or
            type(row.get('cost')) not in (int,float) or not math.isfinite(row['cost']) or row['cost'] < 0):
            raise ValueError('invalid calibration row')
    results = []
    for tau in grid:
        selected = [r for r in rows if r['eligible'] and r['score'] < tau]
        groups = {r['episode_group_id'] for r in selected}
        bad = {r['episode_group_id'] for r in selected if r['label'] != 'safe_and_sufficient'}
        m, k = len(groups), len(bad)
        upper = binomial_upper(k, m, delta/len(grid))
        results.append(dict(threshold=tau, selected_groups=m, unacceptable_groups=k, upper_bound=upper,
                            selected_actions=len(selected), unacceptable_actions=sum(r['label']!='safe_and_sufficient' for r in selected),
                            estimated_cost=sum(r['cost'] for r in selected), feasible=m>0 and upper<=epsilon))
    feasible = [r for r in results if r['feasible']]
    chosen = max(feasible, key=lambda r:(r['estimated_cost'],-r['threshold'])) if feasible else None
    return dict(threshold=chosen['threshold'] if chosen else None, epsilon=epsilon,delta=delta, grid=list(grid),
                calibration_unit='independent-episode-group',
                risk_target='any-unacceptable-would-bypass-given-any-would-bypass',
                valid_actions=len(rows), valid_groups=len({r['episode_group_id'] for r in rows}),results=results)


def _strict_pairs(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError('duplicate JSON key')
        obj[k] = v
    return obj


def load_json(path):
    if Path(path).stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError('artifact too large')
    raw = Path(path).read_bytes()
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError('artifact too large')
    value = json.loads(raw, object_pairs_hook=_strict_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    return value, sha256(raw).hexdigest()


def validate_artifact(a):
    if a['schema_version'] != SCHEMA or a['feature_version'] != FEATURE_VERSION or a['input_schema'] != INPUT_SCHEMA:
        raise ValueError('unsupported router version')
    if a['scope'] != 'single-internal-read-no-sink':
        raise ValueError('unsupported router scope')
    for key in ('catalog_sha256','model_config_sha256','development_manifest_sha256','calibration_manifest_sha256'):
        v = a[key]
        if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v):
            raise ValueError('invalid binding hash')
    if not a['approved_tool_schema_hashes'] or any(not isinstance(n,str) or not n or
        not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h)
        for n,h in a['approved_tool_schema_hashes'].items()):
        raise ValueError('invalid approved tool hashes')
    groups = a['split_groups']
    if set(groups) != {'development','calibration','test'} or any(not isinstance(v,list) or
        len(v)!=len(set(v)) or any(not isinstance(g,str) or not g for g in v) for v in groups.values()):
        raise ValueError('invalid split groups')
    sets = [set(groups[k]) for k in ('development','calibration','test')]
    if not sets[0] or not sets[1] or any(sets[i]&sets[j] for i in range(3) for j in range(i+1,3)):
        raise ValueError('empty or overlapping development/calibration groups')
    if a['label_source'] not in LABEL_SOURCES or a['independence_attested'] is not True:
        raise ValueError('independent labels/groups required')
    c = a['calibration']; grid = c['grid']; eps,delta=c['epsilon'],c['delta']
    calibrate([],grid,eps,delta)
    if c['calibration_unit']!='independent-episode-group' or c['risk_target']!='any-unacceptable-would-bypass-given-any-would-bypass':
        raise ValueError('wrong risk target')
    if len(c['results']) != len(grid):
        raise ValueError('incomplete grid evidence')
    if (type(c['valid_groups']) is not int or type(c['valid_actions']) is not int or
        c['valid_groups']!=len(sets[1]) or c['valid_actions']<c['valid_groups']):
        raise ValueError('invalid calibration totals')
    feasible=[]
    for tau,r in zip(grid,c['results']):
        m,k=r['selected_groups'],r['unacceptable_groups']
        sa,ua=r['selected_actions'],r['unacceptable_actions']
        if (any(type(n) is not int for n in (m,k,sa,ua)) or
            not 0<=k<=m<=c['valid_groups'] or not m<=sa<=c['valid_actions'] or not k<=ua<=sa or
            (m==0)!=(sa==0) or (k==0)!=(ua==0) or type(r['feasible']) is not bool):
            raise ValueError('inconsistent group/action denominators')
        upper=binomial_upper(k,m,delta/len(grid))
        if (r['threshold']!=tau or m>len(sets[1]) or not math.isfinite(r['estimated_cost']) or r['estimated_cost']<0 or
            not math.isfinite(r['upper_bound']) or abs(upper-r['upper_bound'])>1e-10 or
            r['feasible']!=(m>0 and upper<=eps)):
            raise ValueError('inconsistent calibration evidence')
        if r['feasible']:feasible.append(r)
    chosen=max(feasible,key=lambda r:(r['estimated_cost'],-r['threshold'])) if feasible else None
    if c['threshold'] != (chosen['threshold'] if chosen else None):
        raise ValueError('threshold not supported by calibration')
    return a


class LocalAuditRouter:
    def __init__(self, mode='off', artifact_path=None, model_config_sha256=None):
        if mode not in {'off','shadow','selective'}:
            raise ValueError('unknown audit router mode')
        self.mode=mode;self.artifact=None;self.artifact_sha256=None;self.error=None
        self.model_config_sha256=model_config_sha256
        if mode != 'off' and artifact_path:
            try:
                a,h=load_json(artifact_path);validate_artifact(a)
                self.artifact=deepcopy(a);self.artifact_sha256=h
            except Exception as e:
                self.error=type(e).__name__  # no paths/private input in diagnostics
        elif mode != 'off':
            self.error='ARTIFACT_MISSING'

    def assess(self, packet, flags, runtime, calls, sandbox):
        import time
        started=time.perf_counter()
        result=dict(router_schema=SCHEMA, mode=self.mode, route_source='local_calibrated_algorithm',
                    feature_version=FEATURE_VERSION, artifact_sha256=self.artifact_sha256,
                    eligible=False,would_bypass=False,actual_bypass=False,score=None,threshold=None,
                    completeness_flags=flags,features=None,semantic_audit_calls=0,semantic_audit_tokens=0)
        try:
            eligible,reason=eligibility(packet,flags,runtime,calls,sandbox)
            result.update(eligible=eligible,route_reason=reason)
            if eligible:
                score,features=risk_score(packet);result.update(score=score,features=features)
                a=self.artifact
                if not a:
                    result['route_reason']='ARTIFACT_INVALID_OR_MISSING'
                else:
                    # Revalidate numeric evidence if a caller mutates the trusted configuration.
                    validate_artifact(a)
                    catalog,tools=catalog_snapshot(runtime)
                    name=packet['current_actions'][0]['tool_name']
                    compatible=(catalog==a['catalog_sha256'] and tools.get(name)==a['approved_tool_schema_hashes'].get(name)
                                and a['model_config_sha256']==self.model_config_sha256)
                    c=a['calibration'];result['threshold']=c['threshold']
                    result['calibration']=dict(unit=c['calibration_unit'],risk_target=c['risk_target'],epsilon=c['epsilon'],delta=c['delta'],
                                               selected=next((r for r in c['results'] if r['threshold']==c['threshold']),None))
                    result['would_bypass']=compatible and c['threshold'] is not None and score<c['threshold']
                    result['route_reason']=('BELOW_CALIBRATED_THRESHOLD' if result['would_bypass'] else
                                            'INCOMPATIBLE_ARTIFACT' if not compatible else
                                            'NO_CERTIFIED_THRESHOLD' if c['threshold'] is None else 'SCORE_REQUIRES_AUDIT')
        except Exception as e:
            result.update(route_reason='ROUTER_ERROR',error_type=type(e).__name__,would_bypass=False)
        result['router_total_latency_ms']=(time.perf_counter()-started)*1000
        return result


class RouterReceiptVerifier:
    """A process-local, one-use handoff. Public JSON is never authority."""
    def __init__(self):
        self._receipts={};self._lock=Lock()

    def issue(self,binding,record):
        token=object()
        with self._lock:self._receipts[token]=(deepcopy(binding),digest(record))
        return token

    def discard(self,token):
        if type(token) is object:
            with self._lock:self._receipts.pop(token,None)

    def consume(self,token,binding,record):
        if type(token) is not object:return False
        with self._lock:registered=self._receipts.pop(token,None)
        return registered is not None and registered==(binding,digest(record))


def summarize_events(events):
    r=[e for e in events if not e.get('original_public_bypass') and e.get('route_reason')!='L2_PRECHECK_DENY']
    eligible=sum(bool(e.get('eligible')) for e in r);bypasses=sum(bool(e.get('actual_bypass')) for e in r)
    shadow=[e for e in r if e.get('mode')=='shadow' and e.get('would_bypass')]
    costs=[e.get('semantic_audit_tokens') for e in shadow]
    known=[e['semantic_audit_tokens'] for e in r if e.get('semantic_audit_tokens') is not None]
    latencies=sorted(e['router_total_latency_ms'] for e in r if e.get('router_total_latency_ms') is not None)
    return dict(candidate_batches=len(events),previously_audited_batches=len(r),eligible_batches=eligible,
                original_public_bypass_batches=sum(bool(e.get('original_public_bypass')) for e in events),
                l2_rejected_batches=sum(e.get('route_reason')=='L2_PRECHECK_DENY' for e in events),
                actual_bypass_batches=bypasses,would_bypass_batches=sum(bool(e.get('would_bypass')) for e in r),
                eligible_rate=eligible/len(r) if r else None,new_bypass_rate=bypasses/len(r) if r else None,
                eligible_bypass_rate=bypasses/eligible if eligible else None,
                semantic_audit_calls=sum(e.get('semantic_audit_calls',0) for e in r),
                known_semantic_audit_tokens=sum(known),unknown_audit_cost_batches=len(r)-len(known),
                shadow_would_save_tokens=sum(costs) if all(c is not None for c in costs) else None,
                actual_total_tokens_saved=None,
                router_latency_p50_ms=latencies[int((len(latencies)-1)*0.5)] if latencies else None,
                router_latency_p95_ms=latencies[int((len(latencies)-1)*0.95)] if latencies else None)
