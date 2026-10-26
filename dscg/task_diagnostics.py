"""Append-only task diagnostics, separate from native interactions and scoring."""
from contextvars import ContextVar
from copy import deepcopy
import gzip
import hashlib
import json
import math
from pathlib import Path
from uuid import uuid4

SCHEMA = 'dscg.task-diagnostics.v2'
LEGACY_SCHEMA = 'dscg.task-diagnostics.v1'
REQUEST_REFERENCE_SCHEMA = 'dscg.request-reference.v1'
_current = ContextVar('dscg_task_diagnostics', default=None)


class DiagnosticWriteError(OSError):
    pass


def current_session():
    return _current.get()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def _within(root, path):
    target = path.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('diagnostic path outside task directory')
    return target


class DiagnosticSession:
    def __init__(self, logger, attempt_id, config, level='summary'):
        self.logger, self.attempt_id, self.config, self.level = logger, attempt_id, config, level
        self.path, self.latest, self.responses, self.finished = None, {}, {}, False
        self.routers = {}
        self.audit_updates, self.action_updates = {}, {}
        self.response_refs = {}
        self.response_path = None

    def __enter__(self):
        self.token = _current.set(self)
        try:
            context = getattr(self.logger, 'context', {})
            root = getattr(self.logger, 'dirpath', None)
            if root and all(context.get(k) is not None for k in ('pipeline_name','suite_name','user_task_id','attack_type')):
                directory = Path(root)/str(context['pipeline_name']).replace('/', '_')/str(context['suite_name'])
                group = _within(Path(root), directory)
                directory = _within(group, group/str(context['user_task_id'])/str(context['attack_type']))
                directory.mkdir(parents=True, exist_ok=True)
                stem = str(context.get('injection_task_id') or 'none')
                self.path = _within(directory, directory/(stem+'.dscg.jsonl'))
                self.response_path = _within(directory, directory/(stem+'.dscg.responses.jsonl'))
                config_ref = self._configuration(group)
                with self.path.open('ab+') as stream:
                    stream.seek(0, 2)
                    if stream.tell():
                        stream.seek(-1, 2)
                        if stream.read(1) != b'\n': stream.write(b'\n')
                    offset = stream.tell()
                self.logger.context['dscg_diagnostics'] = dict(path=self.path.name,
                    attempt_id=self.attempt_id, offset=offset)
                self.emit('task_start', {'config_ref': '../../'+config_ref, 'trace_level':self.level,
                    'responses_path': self.response_path.name})
            return self
        except Exception as exc:
            _current.reset(self.token)
            if isinstance(exc, DiagnosticWriteError): raise
            raise DiagnosticWriteError('DIAGNOSTIC_WRITE_FAILED') from exc

    def _configuration(self, group):
        config = deepcopy(self.config)
        manifest = group/'run_manifest.json'
        if manifest.is_file():
            binding = json.loads(manifest.read_text(encoding='utf-8'))
            frame = config.get('framework', {})
            keys = [k for k,v in frame.items() if k in binding and binding[k] == v]
            config = {'manifest':'run_manifest.json', 'framework_manifest_keys':keys,
                      'framework':{k:v for k,v in frame.items() if k not in keys}}
        data = _json(config).encode('utf-8')
        name = 'dscg_config.'+hashlib.sha256(data).hexdigest()[:16]+'.json'
        path = _within(group, group/name)
        try:
            with path.open('xb') as stream: stream.write(data)
        except FileExistsError:
            if path.read_bytes() != data: raise DiagnosticWriteError('DIAGNOSTIC_CONFIG_CONFLICT')
        return name

    def __exit__(self, exc_type, exc, tb):
        try:
            if not self.finished: self.finish({}, failed=exc_type is not None)
        finally:
            _current.reset(self.token)

    def _write(self, event, record, **metadata):
        if self.path is None: return
        row = dict(schema_version=SCHEMA, attempt_id=self.attempt_id, event=event, record=record, **metadata)
        try:
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(_json(row)+'\n')
        except (OSError, TypeError, ValueError) as exc:
            raise DiagnosticWriteError('DIAGNOSTIC_WRITE_FAILED') from exc

    def emit(self, event, record, **metadata):
        record = deepcopy(record)
        module = {'authorization':'L2', 'authorization_task_view':'L2', 'audit_request':'L3', 'audit_decision':'L3', 'audit_decision_final':'L3',
                  'audit_router':'L3', 'intent_progress':'Intent Progress'}.get(event)
        if module: metadata['module'] = module
        phase = 'audit' if event in ('audit_decision','audit_decision_final') else 'intent_progress' if event == 'intent_progress' else None
        if phase and (phase != 'audit' or (record.get('parser_status') != 'deterministic_bypass'
                and record.get('semantic_attempt') != 0
                and not str(record.get('model_version','')).startswith(('host','local-router:')))):
            metadata['response_id'] = self.responses.get(phase)
        if event in ('audit_decision','audit_decision_final'):
            index = metadata.get('history_index', len(self.audit_updates))
            self.audit_updates[index] = (event, record, metadata)
            if event == 'audit_decision_final':
                self._flush_audits(index)
            return
        if event == 'audit_router':
            self.routers[metadata.get('router_index',len(self.routers))] = record
            return
        if event == 'action_ledger':
            self.action_updates[record['action_id']] = record
            return
        if event == 'authorization':
            keys = ('authorization_steps','allowed_tools','tool_permissions','implicit_read_tools',
                    'policy_state','contract_version','authorization_source','authorization_protocol',
                    'task_phase','error_code','error_type','error_stage','static_task_view','static_task_view_protocol')
            record = {k:v for k,v in record.items() if k in keys}
        self._write(event, record, **metadata)

    def _flush_audits(self, through=None):
        for index in sorted(list(self.audit_updates)):
            if through is not None and index > through: continue
            event, record, metadata = self.audit_updates.pop(index)
            record.pop('schema_version', None)
            mediation = record.get('mediation_diagnostics')
            if isinstance(mediation,dict): mediation.pop('checker_protocol_diagnostics',None)
            self._write('audit_decision_final', record,
                **metadata, finalized=event == 'audit_decision_final')

    def save_response(self, phase, record):
        if self.response_path is None: return
        try:
            with self.response_path.open('ab+') as stream:
                stream.seek(0,2)
                if stream.tell():
                    stream.seek(-1,2)
                    if stream.read(1) != b'\n': stream.write(b'\n')
                offset = stream.tell()
                stream.write((_json(dict(schema_version='dscg.model-response.v1',
                    attempt_id=self.attempt_id, event='model_response', record=record))+'\n').encode('utf-8'))
            self.response_refs[phase] = dict(path=self.response_path.name, offset=offset,
                response_id=record['response_id'])
            self._write('response',dict(phase=phase),response_ref=self.response_refs[phase],
                module='L3' if phase == 'audit' else 'Intent Progress')
        except (OSError,TypeError,ValueError) as exc:
            raise DiagnosticWriteError('DIAGNOSTIC_WRITE_FAILED') from exc

    def sync(self, context):
        for index,record in enumerate(context.get('dscg_router_events', [])):
            self.routers[index] = deepcopy(record)
        excluded = {'dscg_framework','dscg_authorizations','dscg_audit_decisions',
                    'dscg_action_ledger','dscg_router_events','dscg_trace_artifact'}
        for key,value in context.items():
            if key.startswith('dscg_') and key not in excluded:
                self.latest[key] = deepcopy(value)
        flow = self.latest.get('dscg_intent_flow')
        if isinstance(flow, dict):
            flow.pop('observations', None)
            for step in flow.get('steps',[]): step.pop('intent',None)

    def finish(self, context, *, failed=False):
        if self.finished: return
        self.finished = True
        if 'dscg_cost' in context: self.latest['dscg_cost'] = deepcopy(context['dscg_cost'])
        self._flush_audits()
        for record in self.action_updates.values():
            record.pop('schema_version',None)
            self._write('action_ledger',record,module=record.get('blocked_by','Tools Executor'))
        # Keep routing measurements, omit repeated policy/catalogue/input hashes.
        for index, record in sorted(self.routers.items()):
            record = {k:v for k,v in record.items() if (not k.endswith(('_sha256','_hash','_fingerprint'))
                      or k in ('artifact_sha256','model_config_sha256'))
                      and k not in ('router_schema','feature_version','features','tool_schema_hash','contract_version')}
            self._write('audit_router',record,router_index=index,module='L3')
        l1 = {k:self.latest.pop(k) for k in ('dscg_input_isolation','dscg_l1_projection') if k in self.latest}
        if l1:self._write('l1_summary',l1,module='L1')
        self.latest.pop('dscg_trace_level',None)
        status = ('infrastructure_error' if failed or self.latest.get('dscg_infrastructure_failure') else
                  self.latest.get('dscg_termination',{}).get('kind','finished'))
        self.emit('task_end', {'status':status, 'summary':self.latest})


def sync_context(context):
    if current_session(): current_session().sync(context)


def record_event(event, record, **metadata):
    session = current_session()
    if session is None: return
    if event in ('audit_input','audit_retry_input','audit_protocol_response'):
        return  # Responses are recorded separately; never duplicate prompts/tool bodies.
    if event == 'intent_progress':
        record = {'revision':record['revision'], 'observation':record.get('observations', [])[-1:]}
    if event == 'authorization_precheck' and session.level == 'summary': return
    session.emit(event, record, **metadata)


def _get(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def record_response(phase, response, *, elapsed_ms=0, **identity):
    session = current_session()
    if session is None or phase not in ('audit','intent_progress'): return
    choices = _get(response,'choices') or []
    choice = choices[0] if isinstance(choices,(list,tuple)) and choices else None
    message = _get(choice,'message')
    content = _get(message,'content')
    if isinstance(content, list):
        content = ''.join(_get(block,'text', '') for block in content if _get(block,'type') == 'text')
    usage = _get(response,'usage')
    counts = {k:_get(usage,k) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    counts = {k:v if type(v) is int and v >= 0 else None for k,v in counts.items()}
    response_id = uuid4().hex
    session.responses[phase] = response_id
    session.save_response(phase, dict(response_id=response_id, phase=phase,
        content=content if isinstance(content,str) else None,
        refusal=_get(message,'refusal') if isinstance(_get(message,'refusal'),str) else None,
        finish_reason=_get(choice,'finish_reason'), usage=counts,
        elapsed_ms=round(elapsed_ms,3), **identity))


def begin_model_call(phase):
    session = current_session()
    if session is not None:
        session.responses.pop(phase, None)
        session.response_refs.pop(phase, None)


def record_model_request(phase, options, call_index):
    """Record only settings actually supplied to the shared transport."""
    session = current_session()
    if session is None:
        return
    sampling = {}
    for key in ('temperature', 'top_p', 'max_tokens', 'max_completion_tokens',
                'seed', 'presence_penalty', 'frequency_penalty', 'reasoning_effort'):
        value = options.get(key)
        if ((type(value) in (int, float) and math.isfinite(value)) or
                (key == 'reasoning_effort' and value in ('none','minimal','low','medium','high','xhigh'))):
            sampling[key] = value
    tools = options.get('tools')
    record = dict(phase=phase, call_index=call_index, sampling=sampling,
                  tools_count=len(tools) if isinstance(tools, list) else None,
                  tools_sha256=hashlib.sha256(_json(tools).encode()).hexdigest()
                      if isinstance(tools, list) else None)
    body = options.get('extra_body')
    if isinstance(body, dict) and type(body.get('enable_thinking')) is bool:
        record['enable_thinking'] = body['enable_thinking']
    session.emit('model_request', record)


def record_validation(phase, status, *, diagnostics=None):
    session = current_session()
    if session is not None and status != 'passed':
        session.emit('validation',dict(response_id=session.responses.get(phase),
            phase=phase,status=status,diagnostics=diagnostics or {}),
            module='L3' if phase == 'audit' else 'L2' if phase.startswith('authorization') else 'Intent Progress')


def load_diagnostic_events(path, *, offset=0):
    """Also read historical explicit-full gzip files without rewriting them."""
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rb') as stream:
        stream.seek(offset)
        for line in stream:
            if line.strip(): yield json.loads(line)


def merge_task_diagnostics(path, raw):
    if not isinstance(raw,dict) or 'dscg_diagnostics' not in raw: return raw
    result = deepcopy(raw)
    # A broken reference must never resurrect unrelated/stale inline diagnostics.
    for key in list(result):
        if key.startswith('dscg_') and key != 'dscg_diagnostics': result.pop(key)
    ref = raw['dscg_diagnostics']; path = Path(path)
    try:
        if (not isinstance(ref,dict) or ref.get('path') != path.with_suffix('.dscg.jsonl').name
                or not isinstance(ref.get('attempt_id'),str) or not ref['attempt_id']
                or type(ref.get('offset',0)) is not int or ref.get('offset',0)<0):
            raise ValueError('invalid diagnostic reference')
        side = _within(path.parent,path.parent/ref['path'])
    except (ValueError,TypeError):
        result['dscg_diagnostics_status']='invalid_reference';return result
    audits, actions, observations = [], {}, {}
    authorizations, routers, config = [], {}, None
    response_refs, validations = {}, []
    model_requests, audit_requests, task_views = [], [], []
    new_schema = False
    start, end = False, False
    try:
        for row in load_diagnostic_events(side,offset=ref.get('offset',0)):
            if row.get('schema_version') not in (SCHEMA,LEGACY_SCHEMA) or row.get('attempt_id') != ref['attempt_id']:
                raise ValueError('diagnostic attempt mismatch')
            new_schema = row['schema_version'] == SCHEMA
            event,record=row['event'],row['record']
            response_ref = row.get('response_ref')
            if response_ref is not None:
                if not isinstance(response_ref,dict): raise ValueError('invalid response reference')
                response_refs[response_ref['response_id']] = response_ref
            if not start and event!='task_start': raise ValueError('missing task start')
            if event=='task_start':
                if start: raise ValueError('duplicate task start')
                start=True
                group=path.parent.parent.parent
                cfg_path=_within(group,path.parent/record['config_ref'])
                config=json.loads(cfg_path.read_text(encoding='utf-8'))
                frame=dict(config.get('framework',{}))
                if config.get('manifest'):
                    binding=json.loads(_within(group,cfg_path.parent/config['manifest']).read_text(encoding='utf-8'))
                    frame.update({k:binding[k] for k in config.get('framework_manifest_keys',[])})
                result['dscg_framework']=frame
                result['dscg_trace_level']=record['trace_level']
            elif event=='authorization': authorizations.append(record)
            elif event in ('audit_decision','audit_decision_final'):
                if new_schema:record.setdefault('schema_version','dscg.audit-decision.v1')
                index,length=row.get('history_index'),row.get('history_length')
                if index is not None:
                    if (type(index) is not int or type(length) is not int or
                            not 0 <= index < length or length > len(audits)+1):
                        raise ValueError('invalid audit occurrence')
                    audits=audits[:length]
                    if index==len(audits):audits.append(record)
                    else:audits[index]=record
                    if len(audits)!=length:raise ValueError('missing audit occurrence')
                elif event=='audit_decision_final' and audits and audits[-1].get('batch_fingerprint')==record.get('batch_fingerprint'):
                    audits[-1]=record
                else:audits.append(record)
            elif event=='action_ledger':actions[record['action_id']]=record
            elif event=='intent_progress':observations[record['revision']]=record['observation']
            elif event=='audit_router':routers[row.get('router_index',len(routers))]=record
            elif event=='validation':validations.append(record)
            elif event=='model_request':model_requests.append(record)
            elif event=='audit_request':audit_requests.append(record)
            elif event=='authorization_task_view':task_views.append(record)
            elif event=='l1_summary':result.update(record)
            elif event=='task_end':result.update(record['summary']);end=True;break
        if not start:raise ValueError('missing diagnostic attempt')
    except FileNotFoundError:
        result['dscg_diagnostics_status']='missing';return result
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        # Never turn incomplete/corrupt diagnostics into zero audits or zero costs.
        for k in list(result):
            if k.startswith('dscg_') and k!='dscg_diagnostics':result.pop(k)
        result['dscg_diagnostics_status']='corrupt';return result
    result.update(dscg_task_id=ref['attempt_id'], dscg_authorizations=authorizations,
        dscg_audit_decisions=audits, dscg_action_ledger=list(actions.values()),
        dscg_router_events=[routers[k] for k in sorted(routers)], dscg_diagnostics_status='complete' if end else 'incomplete')
    if model_requests: result['dscg_model_requests'] = model_requests
    if audit_requests: result['dscg_audit_requests'] = audit_requests
    if task_views: result['dscg_static_task_views'] = task_views
    if isinstance(result.get('dscg_intent_flow'),dict):
        state=result['dscg_intent_flow']
        state['observations']=[x for rev in sorted(observations) for x in observations[rev]]
        if new_schema and authorizations:
            intents=authorizations[-1].get('authorization_steps',[])
            for step, original in zip(state.get('steps',[]),intents):
                if isinstance(original,dict) and 'intent' in original:step['intent']=original['intent']
    if new_schema:
        replies=[];response_status='complete'
        for response_ref in response_refs.values():
            try:
                if (response_ref.get('path') != path.with_suffix('.dscg.responses.jsonl').name
                        or type(response_ref.get('offset')) is not int or response_ref['offset']<0):
                    raise ValueError('invalid response reference')
                response_path=_within(path.parent,path.parent/response_ref['path'])
                response=next(load_diagnostic_events(response_path,offset=response_ref['offset']))
                if (response.get('schema_version')!='dscg.model-response.v1'
                        or response.get('attempt_id')!=ref['attempt_id']
                        or response.get('record',{}).get('response_id')!=response_ref['response_id']):
                    raise ValueError('response identity mismatch')
                replies.append(response['record'])
            except FileNotFoundError:
                response_status='missing'
            except (OSError,ValueError,TypeError,KeyError,AttributeError,StopIteration):
                response_status='corrupt'
        result.update(dscg_model_responses=replies, dscg_responses_status=response_status,
                      dscg_validation_failures=validations)
        if response_status!='complete':result['dscg_diagnostics_status']='incomplete'
    return result


def load_task_trace(path):
    path=Path(path)
    return merge_task_diagnostics(path,json.loads(path.read_text(encoding='utf-8')))


def diagnostic_dependencies(path):
    """Existing companion bytes needed to keep a native reuse snapshot readable."""
    path=Path(path);files=[]
    try:
        raw=json.loads(path.read_text(encoding='utf-8'));ref=raw.get('dscg_diagnostics',{})
        if ref.get('path')!=path.with_suffix('.dscg.jsonl').name:return files
        side=_within(path.parent,path.parent/ref['path'])
        if not side.is_file():return files
        files.append(side)
        start=next(load_diagnostic_events(side,offset=ref.get('offset',0)))
        if start.get('attempt_id')!=ref.get('attempt_id') or start.get('event')!='task_start':return files
        response_name=start['record'].get('responses_path')
        if response_name==path.with_suffix('.dscg.responses.jsonl').name:
            response_path=_within(path.parent,path.parent/response_name)
            if response_path.is_file():files.append(response_path)
        group=path.parent.parent.parent
        config=_within(group,path.parent/start['record']['config_ref'])
        if config.is_file():
            files.append(config);value=json.loads(config.read_text(encoding='utf-8'))
            if value.get('manifest'):
                manifest=_within(group,config.parent/value['manifest'])
                if manifest.is_file():files.append(manifest)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,StopIteration):
        pass  # Keep any existing raw companion even if it cannot be decoded.
    return files
