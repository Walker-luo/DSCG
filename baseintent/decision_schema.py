"""Versioned decision contracts; provider constraints never replace host validation."""
from copy import deepcopy
import hashlib
import json
import math
from urllib.parse import urlsplit

AUDIT_PROTOCOL = 'baseintent.audit-decision.v2'
ACTION_PROTOCOL = 'action-steps-v2'
MAX_STEPS, MAX_INTENT = 24, 256
VIOLATIONS = ('OFF_TASK_ACTION', 'EXPLICIT_CONSTRAINT', 'UNSUPPORTED_PARAMETER',
              'UNREQUESTED_DISCLOSURE', 'INSTRUCTION_AS_AUTHORITY', 'ORDER_VIOLATION')
CODES = ('ALIGNED', *VIOLATIONS, 'MISSING_EVIDENCE')
AUDIT_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['decision', 'violations', 'confidence', 'reason_code'],
    'properties': {
        'decision': {'type': 'string', 'enum': ['allow', 'deny', 'abstain']},
        'violations': {'type': 'array', 'maxItems': len(CODES)-1,
                       'items': {'type': 'string', 'enum': list(CODES[1:])}},
        'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'reason_code': {'type': 'string', 'enum': list(CODES)},
    },
}


def action_schema(names):
    names = sorted(names)
    return {'type': 'object', 'additionalProperties': False, 'required': ['steps'],
            'properties': {'steps': {'type': 'array', 'maxItems': MAX_STEPS,
                'items': {'type': 'object', 'additionalProperties': False,
                    'required': ['intent', 'tools'], 'properties': {
                        'intent': {'type': 'string', 'minLength': 1, 'maxLength': MAX_INTENT},
                        'tools': {'type': 'array', 'minItems': 1, 'maxItems': len(names),
                                  'items': {'type': 'string', 'enum': names}}}}}}}


def response_format(config, schema, name):
    """Only documented Qwen/official DashScope endpoints opt into strict Schema."""
    public = config.public_dict() if hasattr(config, 'public_dict') else config or {}
    if not isinstance(public, dict):
        public = {}
    host = urlsplit(public.get('base_url') or '').hostname or ''
    official = host in {'dashscope.aliyuncs.com', 'dashscope-intl.aliyuncs.com'} or (
        host.endswith('.maas.aliyuncs.com') and len(host.split('.')) >= 5)
    if (public.get('provider') == 'dashscope' and public.get('model_id') == 'qwen3.7-flash'
            and official and urlsplit(public.get('base_url') or '').scheme == 'https'):
        return {'type': 'json_schema', 'json_schema': {
            'name': name, 'strict': True, 'schema': deepcopy(schema)}}
    return {'type': 'json_object'}


def contract_identity(config, schema, name):
    return {'protocol': name, 'response_format': response_format(config, schema, name)['type'],
            'schema_sha256': hashlib.sha256(json.dumps(schema, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest()}


def load_decision_json(content):
    def fields(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate decision field')
            value[key] = item
        return value
    return json.loads(content, object_pairs_hook=fields)


class DecisionContractError(ValueError):
    def __init__(self, code, path, expected, actual):
        super().__init__(code)
        self.code = code
        self.diagnostics = {'field_path': path, 'expected_type': expected,
                            'actual_type': type(actual).__name__}
        if isinstance(actual, (list, str)):
            self.diagnostics['array_count' if isinstance(actual, list) else 'raw_length'] = len(actual)


def validate_audit(payload):
    def fail(code, path, expected, value):
        raise DecisionContractError(code, path, expected, value)
    if not isinstance(payload, dict) or set(payload) != set(AUDIT_SCHEMA['required']):
        fail('FIELDS_MISMATCH', '$', 'four-field object', payload)
    d, vs, confidence, reason = (payload[k] for k in AUDIT_SCHEMA['required'])
    if not isinstance(d, str) or d not in ('allow', 'deny', 'abstain'):
        fail('INVALID_DECISION', '$.decision', 'decision enum', d)
    if (not isinstance(vs, list) or len(vs) > len(CODES)-1
            or any(not isinstance(v, str) or v not in CODES[1:] for v in vs)
            or len(set(vs)) != len(vs)):
        fail('INVALID_VIOLATIONS', '$.violations', 'unique violation codes', vs)
    if (isinstance(confidence, bool) or not isinstance(confidence, (float, int))
            or not math.isfinite(confidence) or not 0 <= confidence <= 1):
        fail('INVALID_CONFIDENCE', '$.confidence', 'finite number [0,1]', confidence)
    if not isinstance(reason, str) or reason not in CODES:
        fail('INVALID_REASON_CODE', '$.reason_code', 'reason enum', reason)
    consistent = ((d == 'allow' and not vs and reason == 'ALIGNED')
                  or (d == 'deny' and bool(vs) and all(v in VIOLATIONS for v in vs) and reason in vs)
                  or (d == 'abstain' and vs == ['MISSING_EVIDENCE'] and reason == 'MISSING_EVIDENCE'))
    if not consistent:
        fail('DECISION_INCONSISTENT', '$', 'consistent decision/codes', payload)
    return d, tuple(vs), float(confidence), reason
