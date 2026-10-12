"""Validate explicit independently labeled JSONL; export only numeric routing rows.

No label inference from audit/Monitor/ASR outcomes. No implicit history scan.
Original private input remains in the supplied file, not the processed dataset.
"""
import argparse
import json
from hashlib import sha256
from pathlib import Path
from dscg.audit_router import (LABELS, LABEL_SOURCES, argument_flags, digest, risk_score, validate_completeness_flags)


def _sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def _eligible(packet,host):
    actions=packet['current_actions'];policy=packet['policy_features']
    if len(actions)!=1 or policy['allowlist_matches']!=[True]:return False
    action=actions[0];meta=policy['candidate_metadata_states'][action['tool_name']]
    if (meta.get('metadata_state'),meta.get('effect'),meta.get('sink'),meta.get('sensitivity'),meta.get('idempotent'))!=('valid','read','none','internal',True):return False
    if (host['schema_valid'] is not True or any(host['completeness_flags'].values()) or
        packet['history_truncated'] or packet['tool_results_window_truncated'] or
        any(r.get('content_truncated') or r.get('error') for r in packet['recent_tool_results']) or
        any(argument_flags(action['untrusted_argument_data']).values())):return False
    if not packet['trusted_user_request'].strip() or not action['host_tool_description'].strip():return False
    if len(packet['trusted_user_request'])>2048 or len(action['host_tool_description'])>512:return False
    if any(len(r['content'])>2048 for r in packet['recent_tool_results']) or len(packet['recent_tool_results'])>4 or len(packet['action_history'])>32:return False
    return (len(packet['trusted_user_request'])+len(action['host_tool_description'])+
            len(json.dumps(action['untrusted_argument_data'],ensure_ascii=True))+
            sum(len(r['content']) for r in packet['recent_tool_results']))<=12288


def build_dataset(input_path, output_dir):
    src=Path(input_path);out=Path(output_dir)
    if out.exists():raise ValueError('dataset output already exists; use a fresh path')
    rows=[];excluded=[];group_splits={};correlation_groups={};bindings=None;tools={};sources=set();input_hashes={}
    for line_no,line in enumerate(src.read_text().splitlines(),1):
        if not line.strip():continue
        if len(line.encode())>8*1024*1024:raise ValueError('input row too large')
        record=json.loads(line)
        if record.get('label')=='invalid_sample':
            if not record.get('exclusion_reason'):raise ValueError('invalid sample requires exclusion reason')
            excluded.append({'line':line_no,'reason':record['exclusion_reason']});continue
        if record.get('label') not in LABELS or record.get('label_source') not in LABEL_SOURCES or not record.get('label_evidence_ref'):
            raise ValueError('independent label and evidence reference required')
        group=record['episode_group_id'];split=record['split'];correlation=record['correlation_key']
        if not isinstance(group,str) or not group or split not in {'development','calibration','test'} or not isinstance(correlation,str) or not correlation:
            raise ValueError('explicit group, correlation key and split required')
        if group in group_splits and group_splits[group]!=split:raise ValueError('same group crosses splits')
        if correlation in correlation_groups and correlation_groups[correlation]!=group:raise ValueError('correlated records cross groups')
        group_splits[group]=split;correlation_groups[correlation]=group
        packet=record['packet'];host=record['host']
        if record['input_sha256']!=digest(packet):raise ValueError('input hash mismatch')
        if record['input_sha256'] in input_hashes and input_hashes[record['input_sha256']]!=group:
            raise ValueError('identical packets must share a group')
        input_hashes[record['input_sha256']]=group
        current={k:host[k] for k in ('catalog_sha256','model_config_sha256')}
        if not all(_sha(v) for v in current.values()) or not _sha(host['tool_schema_hash']):raise ValueError('invalid host binding hashes')
        if bindings is not None and current!=bindings:raise ValueError('one dataset requires a single catalog/model configuration')
        bindings=current
        validate_completeness_flags(host['completeness_flags'])
        eligible=_eligible(packet,host)
        score,features=risk_score(packet) if len(packet['current_actions'])==1 else (1.0,{})
        name=packet['current_actions'][0]['tool_name'] if len(packet['current_actions'])==1 else None
        if eligible and split=='development':
            if name in tools and tools[name]!=host['tool_schema_hash']:raise ValueError('tool schema changed')
            tools[name]=host['tool_schema_hash']
        sources.add(record['label_source'])
        rows.append(dict(episode_group_id=group,episode_id=record['episode_id'],correlation_key=correlation,split=split,label=record['label'],
                         label_source=record['label_source'],label_evidence_ref=record['label_evidence_ref'],
                         score=score,features=features,eligible=eligible,tool_name=name,tool_schema_hash=host['tool_schema_hash'],
                         input_sha256=record['input_sha256'],cost=len(json.dumps(packet,ensure_ascii=True))))
    # An unseen development tool cannot qualify in calibration or test.
    for r in rows:r['eligible'] &= tools.get(r['tool_name'])==r['tool_schema_hash']
    groups={split:sorted(g for g,s in group_splits.items() if s==split) for split in ('development','calibration','test')}
    manifest=dict(schema_version='dscg.router-dataset.v1',input_file_sha256=sha256(src.read_bytes()).hexdigest(),
                  feature_version='lexical-max-v1',valid_actions=len(rows),valid_groups=len(group_splits),
                  invalid_actions=len(excluded),excluded=excluded,split_groups=groups,bindings=bindings,
                  approved_tool_schema_hashes=tools,label_sources=sorted(sources),cost_unit='audit-packet-json-characters',
                  rows_sha256=digest(rows),limitations=['Group independence and labels require external verification; checks cannot infer truth or near duplicates.'])
    out.mkdir(parents=True)
    (out/'rows.json').write_text(json.dumps(rows,indent=2,ensure_ascii=True)+'\n')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n')
    return {**manifest,'output_dir':str(out)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args(argv)
    try:r=build_dataset(args.input,args.output_dir)
    except (OSError,ValueError,KeyError,TypeError) as e:parser.error(str(e))
    print(json.dumps({k:r[k] for k in ('valid_actions','valid_groups','invalid_actions','output_dir')}));return 0


if __name__=='__main__':raise SystemExit(main())
