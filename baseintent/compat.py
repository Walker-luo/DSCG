"""Read-only legacy envelope support; never migrate native facts or identities."""
from copy import deepcopy
import json
import os
from pathlib import Path

_METADATA = frozenset({'record','config','configuration','framework','framework_config','optimization_config',
    'summary','aggregate','results','records','groups','runs','models','phases','stats','statistics',
    'metadata','evaluation','defense_config','layer_stats','by_suite','suites','by_attack','attacks',
    'main_model','security_model','pipeline','entries','task_outcomes'})
_IDENTITY_MAPS = frozenset({'results','groups','runs','models','phases','by_suite','suites','by_attack','attacks','entries','task_outcomes'})
_NATIVE = frozenset({'messages','injections','content','args','arguments','candidate_arguments',
    'untrusted_argument_data','tool_results','tool_result','payload','facts','data','input','output',
    'parameters','native_schema','tool_metadata','tools','available_tools','user_request',
    'original_user_request','trusted_user_request'})


def normalize_legacy_keys(value):
    if isinstance(value,list):return [normalize_legacy_keys(v) for v in value]
    if not isinstance(value,dict):return deepcopy(value)
    result={}
    for key,item in value.items():
        renamed=key
        if isinstance(key,str):
            if key.startswith('dscg_'):renamed='baseintent_'+key[5:]
            elif key.startswith('_dscg_'):renamed='_baseintent_'+key[6:]
        metadata=renamed!=key or renamed in _METADATA or (isinstance(renamed,str) and renamed.startswith(('baseintent_','_baseintent_')))
        if metadata and key not in _NATIVE:
            # Container keys are run/model/suite identities, not metadata fields.
            if renamed in _IDENTITY_MAPS and isinstance(item,dict):
                converted={identity:normalize_legacy_keys(record) for identity,record in item.items()}
            else:
                converted=normalize_legacy_keys(item)
        else:
            converted=deepcopy(item)
        if renamed in result and result[renamed]!=converted:
            raise ValueError('conflicting legacy metadata fields')
        result[renamed]=converted
    return result


def compatible_json_load(path):
    return normalize_legacy_keys(json.loads(Path(path).read_text(encoding='utf-8')))


def schema_matches(actual,expected):
    return actual==expected or (isinstance(expected,str) and expected.startswith('baseintent.') and actual=='dscg.'+expected[11:])


def environment_aliases(mapping):
    result=dict(mapping)
    for old,value in mapping.items():
        if not old.startswith('DSCG_'):continue
        new='BASEINTENT_'+old[5:]
        if new in mapping and str(mapping[new]).strip() and str(value).strip() and mapping[new]!=value:
            raise ValueError(f'conflicting environment aliases: {new} / {old}')
        if new not in result or not str(result[new]).strip():result[new]=value
    return result


def getenv(name,default=None,environ=None):
    values=environment_aliases(os.environ if environ is None else environ)
    if name.startswith('DSCG_'):name='BASEINTENT_'+name[5:]
    return values.get(name,default)
