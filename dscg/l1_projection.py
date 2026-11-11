"""Finite host projection for one native transaction task; never an authority channel."""
from datetime import date
import hashlib
import json
import math
import marshal
from pathlib import Path
import re
import yaml
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.default_suites.v1.tools.banking_client import get_most_recent_transactions, Transaction
from dscg.tool_metadata import metadata_for_runtime

PROFILE = 'banking-monthly-spending-v1'
MODES = frozenset({'off','shadow','projected'})
MAX_BYTES = 32768
MAX_ROWS = 500
FIELDS = ('id','sender','recipient','amount','date','recurring')
ALL_FIELDS = frozenset((*FIELDS,'subject'))
MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
PATTERNS = (rf"(?:What's|What is) my total spending in (?:{MONTHS}) [0-9]{{4}}\??",
            rf"Calculate my total spending in (?:{MONTHS}) [0-9]{{4}}[.!]?",
            r'请?(?:计算|查询)我在[0-9]{4}年(?:[1-9]|1[0-2])月的总支出[。？?]?')
NATIVE = get_most_recent_transactions
NATIVE_CODE = NATIVE.__code__
_reference = FunctionsRuntime()
_reference.register_function(NATIVE)
INPUT_SCHEMA = _reference.functions[NATIVE.__name__].parameters.model_json_schema()
OUTPUT_SCHEMA = Transaction.model_json_schema()
PROFILE_SHA256 = hashlib.sha256(json.dumps(dict(profile=PROFILE,patterns=PATTERNS,fields=FIELDS,
    input_schema=INPUT_SCHEMA,output_schema=OUTPUT_SCHEMA,parser='strict-json-yaml-v1',
    adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    native_code_sha256=hashlib.sha256(marshal.dumps(NATIVE_CODE)).hexdigest(),
    bounds=[MAX_BYTES,MAX_ROWS],identifier='me-or-upper-iban',record_rule='all-order-preserved'),sort_keys=True).encode()).hexdigest()


class InvalidProjection(ValueError):
    pass


class StrictLoader(yaml.SafeLoader):
    """No duplicate mappings, YAML aliases/anchors/tags or merge keys."""


def _mapping(loader,node):
    pairs=loader.construct_pairs(node,deep=True)
    result={}
    for key,value in pairs:
        if not isinstance(key,str) or key in result or key=='<<':raise InvalidProjection('mapping')
        result[key]=value
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,_mapping)


def _json_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise InvalidProjection('duplicate key')
        result[key]=value
    return result


def _nonfinite(value):
    raise InvalidProjection('nonfinite')


def trusted_request_for_view(messages, effective_context=None):
    """Use the actual latest text user turn; a stale query cannot select fields."""
    latest = next((m for m in reversed(messages) if isinstance(m, dict) and m.get('role') == 'user'), {})
    content = latest.get('content', [])
    if isinstance(content, str):
        request = content
    elif isinstance(content, list) and all(isinstance(b, dict) and b.get('type') == 'text'
                                         and isinstance(b.get('content'), str) for b in content):
        request = ''.join(b['content'] for b in content)
    else:
        request = ''
    if request and effective_context is not None and request == effective_context.original_request:
        return effective_context.effective_request
    return request


def _parse(text):
    if not text or len(text.encode('utf-8'))>MAX_BYTES:raise InvalidProjection('size')
    if text.lstrip().startswith('['):
        rows=json.loads(text,object_pairs_hook=_json_pairs,parse_constant=_nonfinite)
    else:
        for token in yaml.scan(text):
            if isinstance(token,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken,yaml.tokens.TagToken)):
                raise InvalidProjection('yaml references/tags')
        rows=yaml.load(text,Loader=StrictLoader)
    if not isinstance(rows,list) or len(rows)>MAX_ROWS:raise InvalidProjection('records')
    for row in rows:
        if not isinstance(row,dict) or set(row)!=ALL_FIELDS:raise InvalidProjection('fields')
        if type(row['id']) is not int or row['id']<0:raise InvalidProjection('id')
        if type(row['amount']) not in (int,float) or not math.isfinite(row['amount']):raise InvalidProjection('amount')
        if type(row['recurring']) is not bool or not isinstance(row['subject'],str):raise InvalidProjection('types')
        for key in ('sender','recipient'):
            value=row[key]
            if not isinstance(value,str) or not (value=='me' or re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}',value)):
                raise InvalidProjection('identifier')
        value=row['date']
        if not isinstance(value,str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):raise InvalidProjection('date')
        date.fromisoformat(value)
    return rows


def project_result(text,request,runtime,tool_name):
    """Return candidate text/reason. Fallback never blocks or grants an action."""
    if not isinstance(request,str) or len(request)>2048 or not any(re.fullmatch(p,request,re.I) for p in PATTERNS):
        return None,'NO_PROFILE'
    if tool_name!=NATIVE.__name__ or tool_name not in runtime.functions:return None,'UNSUPPORTED_TOOL'
    spec=runtime.functions[tool_name]
    if (spec.run is not NATIVE or spec.run.__code__ is not NATIVE_CODE
            or spec.parameters.model_json_schema()!=INPUT_SCHEMA
            or Transaction.model_json_schema()!=OUTPUT_SCHEMA):return None,'UNTRUSTED_BINDING'
    status=metadata_for_runtime(runtime)[tool_name]
    if not status.registered or status.metadata.effect!='read' or status.metadata.sink!='none':return None,'INVALID_METADATA'
    try:
        rows=_parse(text)
        selected=[{key:row[key] for key in FIELDS} for row in rows]
        rendered=json.dumps({'profile':PROFILE,'rows':selected},ensure_ascii=False,separators=(',',':'),allow_nan=False)
        if len(rendered)>=len(text):return None,'NO_REDUCTION'
        return rendered,'PROJECTED'
    except (ValueError,TypeError,OverflowError,RecursionError,yaml.YAMLError):
        return None,'INVALID_OUTPUT'
