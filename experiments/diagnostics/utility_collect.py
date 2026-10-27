"""Explicitly authorized, bounded collection for fixed utility diagnostics.

No tools execute. No retries, resume, fallback models or automatic promotion.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

from baseintent.model_config import create_openai_client, reasoning_effort_for_config, resolve_model_config
from baseintent.request_compatibility import api_error_diagnostics
from experiments.diagnostics.utility_stages import (
    RESPONSE_SCHEMA, _destination, build_stage, compare_stage, digest, main as compare_cli)


def _save(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix='.responses-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def _ordered(bundle):
    lookup = {(r['case_id'],r['repetition'],r['profile']):r for r in bundle['requests']}
    for index,case in enumerate(bundle['cases']):
        for repetition in (1,2):
            profiles = bundle['profiles'] if (index+repetition)%2 else bundle['profiles'][::-1]
            for profile in profiles:
                yield lookup[(case['id'],repetition,profile)]


def collect_stage(bundle, config, output_dir, *, max_calls, client_factory=None):
    compare_stage(bundle)  # Validate every fixed input before creating clients.
    if bundle['stage'] not in ('audit','authorization'):
        raise ValueError('source collection requires a separate approved stage')
    if type(max_calls) is not int or not 1 <= max_calls <= bundle['planned_requests']:
        raise ValueError('max_calls must be an integer within the fixed stage budget')
    output = _destination(Path(output_dir))
    output.mkdir(parents=True, exist_ok=False)
    _save(output/'bundle.json',bundle)
    result = dict(schema_version=RESPONSE_SCHEMA, bundle_sha256=bundle['bundle_sha256'],
                  model_config=config.public_dict(), records=[], collector=dict(
                      schema_version='baseintent.utility-collector.v1', status='prepared',
                      stage=bundle['stage'], max_calls=max_calls, attempted_calls=0,
                      sdk_max_retries=0, tools_executed=0, order='counterbalanced_case_repetition_pairs'))
    _save(output/'responses.json',result)
    client = None
    try:
        client = (client_factory or create_openai_client)(config).with_options(max_retries=0)
        with (output/'attempts.jsonl').open('x',encoding='utf-8') as journal:
            def log(event, row):
                journal.write(json.dumps(dict(event=event,request_id=row['id'],
                    utc=datetime.now(timezone.utc).isoformat()))+'\n')
                journal.flush(); os.fsync(journal.fileno())

            for row in list(_ordered(bundle))[:max_calls]:
                kwargs = deepcopy(row['request'])
                kwargs['model'] = config.model_id
                effort = reasoning_effort_for_config(config)
                if effort is not None: kwargs['reasoning_effort'] = effort
                result['collector'].update(status='running',
                    attempted_calls=result['collector']['attempted_calls']+1)
                log('started',row)
                _save(output/'responses.json',result)
                record = dict(request_id=row['id'], request_sha256=row['request_sha256'],
                              actual_request_sha256=digest(kwargs), profile=row['profile'],
                              content=None, finish_reason=None, refusal_present=False, total_tokens=None)
                started = time.monotonic()
                failed = False
                try:
                    response = client.chat.completions.create(**kwargs)
                    choices = getattr(response,'choices',None)
                    if choices:
                        message = choices[0].message
                        record['content'] = message.content if isinstance(message.content,str) else None
                        record['refusal_present'] = bool(getattr(message,'refusal',None))
                        finish = getattr(choices[0],'finish_reason',None)
                        record['finish_reason'] = (finish if finish in (None,'stop','length','content_filter',
                            'tool_calls','function_call') else 'other')
                    else:
                        record['no_choices'] = True
                    usage = getattr(response,'usage',None)
                    tokens = getattr(usage,'total_tokens',None)
                    if type(tokens) is int and tokens >= 0: record['total_tokens'] = tokens
                    log('received',row)
                except (Exception, KeyboardInterrupt) as exc:
                    failed = True
                    record['error'] = 'TIMEOUT' if 'timeout' in type(exc).__name__.lower() else 'MODEL_ERROR'
                    record['api_error'] = api_error_diagnostics(exc)
                    result['collector']['status'] = ('interrupted' if isinstance(exc,KeyboardInterrupt)
                                                      else 'stopped_api_error')
                    log('failed',row)
                record['latency_ms'] = round((time.monotonic()-started)*1000,2)
                result['records'].append(record)
                _save(output/'responses.json',result)
                print(f"{bundle['stage']} {len(result['records'])}/{max_calls} {row['profile']} "
                      f"{'api_error_stop' if failed else 'received'}",flush=True)
                if failed: break
            else:
                result['collector']['status'] = ('complete' if len(result['records'])==bundle['planned_requests']
                                                  else 'budget_exhausted')
    finally:
        _save(output/'responses.json',result)
        if client is not None: client.close()
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',required=True,
                        help='Send paid model requests only within an explicitly approved budget.')
    parser.add_argument('--stage',choices=('audit','authorization'),required=True)
    parser.add_argument('--reference-manifest',type=Path,required=True,
                        help='Read public model settings from an existing native run, never its credentials.')
    parser.add_argument('--max-calls',type=int,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args = parser.parse_args(argv)
    reference = json.loads(args.reference_manifest.read_text())
    model = reference['security_model' if args.stage=='audit' else 'main_model']
    config = resolve_model_config(model['model_id'],provider=model['provider'],base_url=model['base_url'],
                                  api_key_env=model.get('api_key_env'),prefix='BASEINTENT_DIAGNOSTIC')
    bundle = build_stage(args.stage)
    result = collect_stage(bundle,config,args.output_dir,max_calls=args.max_calls)
    compare_cli(['compare','--bundle',str(args.output_dir/'bundle.json'),
                 '--responses',str(args.output_dir/'responses.json'),
                 '--output-dir',str(args.output_dir/'comparison')])
    return 0 if result['collector']['status']=='complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
