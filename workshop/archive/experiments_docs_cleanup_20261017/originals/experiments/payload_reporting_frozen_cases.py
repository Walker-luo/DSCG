"""Replay prespecified historical failures plus clean controls in mock suites.

Uses recorded attack payloads with the current pipeline. No attack search or
real application API runs. Native predicates are preserved, including known
hotel-name warning matches. This is a small targeted diagnostic, not E0 passage.
"""
import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from agentdojo import logging
from agentdojo.task_suite import get_suite
from dscg.pipelines.defended import make_defended_pipeline
from dscg.input_isolation import FRAMEWORK_VERSION

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output-dir',required=True)
    args=ap.parse_args()
    dest=(ROOT/args.output_dir).resolve()
    if not dest.is_relative_to((ROOT/'workshop/artifacts').resolve()) or dest.exists():
        ap.error('Use a fresh output directory under workshop/artifacts')
    dest.mkdir(parents=True)
    load_dotenv(ROOT/'.env')
    diagnosis=json.loads((ROOT/'workshop/artifacts/20261012_defense_regression/historical_diagnosis.json').read_text())
    cases=[]
    for r in diagnosis['native_positive_review']:
        if r['run']!='deepseek-flash_3layer_L2opt':continue
        suite,user,inj,attack,_=r['key']
        cases.append(dict(suite=suite,user=user,injection=inj,attack=attack))
    cases.extend([dict(suite='banking',user='user_task_1',injection='injection_task_1',attack='tool_knowledge'),
                  dict(suite='banking',user='user_task_2',injection='injection_task_0',attack='tool_knowledge')])
    cases.extend(dict(suite=s,user=f'user_task_{u}',injection=None,attack='clean')
                 for s,u in [('travel',0),('slack',1),('banking',1)])
    (dest/'selection.json').write_text(json.dumps(cases,indent=2)+'\n')
    rows=[]
    for i,c in enumerate(cases):
        suite=get_suite('v1.2',c['suite'])
        attack=c['attack'];user=c['user'];inj=c['injection']
        source=(ROOT/'results/partial_benchmark/deepseek-flash_3layer_L2opt'/
                (attack if inj else 'tool_knowledge')/c['suite']/'run_manifest.json')
        manifest=json.loads(source.read_text())
        injections={};historical=None
        if inj:
            path=source.parent/user/attack/(inj+'.json')
            historical=json.loads(path.read_text());injections=historical['injections']
        pipeline,main_tokens,audit_tokens=make_defended_pipeline(
            model_id='deepseek-flash',sec_model_id='deepseek-flash',
            tool_metadata=manifest['tool_metadata'],trace_level='full',audit_router_mode='off')
        pipeline.name=f'payload-reporting-{i:02d}'
        delegate=logging.NullLogger();delegate.logdir=str(dest/'native');delegate.messages=[]
        row={**c,'historical_utility':historical.get('utility') if historical else None,
             'historical_native_asr':historical.get('security') if historical else None,
             'payload_sha256':hashlib.sha256(json.dumps(injections,sort_keys=True).encode()).hexdigest()}
        started=perf_counter()
        try:
            with logging.TraceLogger(delegate=delegate,suite_name=c['suite'],pipeline_name=pipeline.name,
                                     user_task_id=user,injection_task_id=inj or 'none',attack_type=attack,
                                     injections=injections,benchmark_version='v1.2') as logger:
                utility,security=suite.run_task_with_pipeline(
                    pipeline,suite.get_user_task_by_id(user),suite.get_injection_task_by_id(inj) if inj else None,injections)
                row.update(utility=utility,native_attack_success=security if inj else None)
                logger.set_contextarg('utility',utility)
                logger.set_contextarg('security',security if inj else None)
                native_path=dest/'native'/pipeline.name/c['suite']/user/attack/((inj or 'none')+'.json')
                row['trace']=str(native_path.relative_to(ROOT))
        except Exception as exc:
            row['error']=type(exc).__name__
        row['latency_ms']=round((perf_counter()-started)*1000,2)
        row['main_usage']=main_tokens.snapshot()
        row['audit_usage']=audit_tokens.snapshot() if audit_tokens else None
        rows.append(row)
        (dest/'report.json').write_text(json.dumps({'framework_version':FRAMEWORK_VERSION,'rows':rows,
                'planned':len(cases),'completed':len(rows),'limits':__doc__},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k in ['suite','user','injection','attack','utility','native_attack_success','error']},ensure_ascii=False),flush=True)
    errors=sum('error' in r for r in rows)
    print(json.dumps({'planned':len(cases),'completed':len(rows),'utility':sum(r.get('utility') is True for r in rows),
                      'native_asr':sum(r.get('native_attack_success') is True for r in rows),'errors':errors}),flush=True)
    return 2 if errors else (1 if any(r.get('native_attack_success') or not r.get('utility') for r in rows) else 0)


if __name__=='__main__':raise SystemExit(main())
