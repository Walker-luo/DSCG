"""Freeze a predeclared grid and grouped exact risk bound; never train weights."""
import argparse
import json
from pathlib import Path
from dscg.audit_router import SCHEMA,FEATURE_VERSION,INPUT_SCHEMA,LABELS,LABEL_SOURCES,calibrate,digest,load_json,validate_artifact


def calibrate_dataset(dataset_dir,grid,epsilon,delta,output,attest_independent_groups=False):
    out=Path(output)
    if out.exists():raise ValueError('artifact already exists; use a fresh path')
    if not attest_independent_groups:raise ValueError('independent group/label review must be explicitly attested')
    root=Path(dataset_dir);manifest,manifest_hash=load_json(root/'manifest.json');rows,_=load_json(root/'rows.json')
    if manifest['rows_sha256']!=digest(rows) or manifest['feature_version']!=FEATURE_VERSION:raise ValueError('dataset hash/version mismatch')
    group_splits={};correlations={};inputs={};sources=set()
    for r in rows:
        if (r.get('label') not in LABELS or r.get('label_source') not in LABEL_SOURCES or not r.get('label_evidence_ref') or
            r.get('split') not in {'development','calibration','test'} or not isinstance(r.get('episode_group_id'),str) or not r['episode_group_id']):
            raise ValueError('invalid independent row labels/splits')
        group=r['episode_group_id'];split=r['split'];correlation=r['correlation_key'];input_hash=r['input_sha256']
        if group in group_splits and group_splits[group]!=split:raise ValueError('actual groups cross splits')
        if correlation in correlations and correlations[correlation]!=group:raise ValueError('actual correlated rows cross groups')
        if input_hash in inputs and inputs[input_hash]!=group:raise ValueError('actual identical inputs cross groups')
        group_splits[group]=split;correlations[correlation]=group;inputs[input_hash]=group;sources.add(r['label_source'])
    groups={s:sorted(g for g,v in group_splits.items() if v==s) for s in ('development','calibration','test')}
    if (manifest['split_groups']!=groups or manifest['label_sources']!=sorted(sources) or manifest['valid_actions']!=len(rows)
        or manifest['valid_groups']!=len(group_splits) or manifest['invalid_actions']!=len(manifest['excluded'])):
        raise ValueError('manifest claims differ from actual rows')
    development=[r for r in rows if r['split']=='development'];calibration=[r for r in rows if r['split']=='calibration']
    if not development or not calibration or len(manifest['label_sources'])!=1:raise ValueError('development/calibration and a single independent label source required')
    # Grid is supplied before looking at calibration outcomes; record its exact bytes/hash.
    c=calibrate(calibration,grid,epsilon,delta)
    artifact=dict(schema_version=SCHEMA,feature_version=FEATURE_VERSION,input_schema=INPUT_SCHEMA,
                  scope='single-internal-read-no-sink',**manifest['bindings'],
                  approved_tool_schema_hashes=manifest['approved_tool_schema_hashes'],
                  development_manifest_sha256=digest(development),calibration_manifest_sha256=digest(calibration),
                  dataset_manifest_sha256=manifest_hash,split_groups=manifest['split_groups'],
                  label_source=manifest['label_sources'][0],independence_attested=True,
                  calibration=c,grid_sha256=digest(grid),cost_unit=manifest['cost_unit'])
    validate_artifact(artifact);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:f.write(json.dumps(artifact,ensure_ascii=True,indent=2)+'\n')
    return artifact


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-dir',required=True);parser.add_argument('--grid',type=float,nargs='+',required=True)
    parser.add_argument('--epsilon',type=float,required=True);parser.add_argument('--delta',type=float,required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--attest-independent-groups',action='store_true')
    args=parser.parse_args(argv)
    try:a=calibrate_dataset(args.dataset_dir,args.grid,args.epsilon,args.delta,args.output,args.attest_independent_groups)
    except (OSError,ValueError,KeyError,TypeError) as e:parser.error(str(e))
    print(json.dumps({'threshold':a['calibration']['threshold'],'valid_groups':a['calibration']['valid_groups'],'output':args.output}));return 0


if __name__=='__main__':raise SystemExit(main())
