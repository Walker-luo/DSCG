"""Host-owned tool exposure and bounded task authorization helpers.

These operations do not execute tools or grant permissions from tool feedback.
The real runtime remains the execution authority.
"""
import hashlib
import json
import re
from dataclasses import dataclass
from copy import deepcopy
import unicodedata

from agentdojo.functions_runtime import FunctionsRuntime
from pydantic import create_model
from baseintent.tool_metadata import metadata_catalog_hash, metadata_for_runtime


def catalog_fingerprint(runtime):
    """In-process binding, including mutable schemas and callable identities."""
    definitions = {}
    for name, spec in sorted(runtime.functions.items()):
        definitions[name] = {
            'identity': id(spec), 'name': spec.name, 'description': spec.description,
            'schema': spec.parameters.model_json_schema(), 'run_identity': id(spec.run),
            'code_identity': id(getattr(spec.run, '__code__', None)),
            'dependencies': {
                key: (id(dep), (id(dep.env_dependency), id(getattr(dep.env_dependency, '__code__', None)))
                      if callable(dep.env_dependency) else dep.env_dependency)
                for key, dep in sorted(spec.dependencies.items())},
        }
    payload = {'runtime': id(runtime), 'tools': definitions,
               'metadata': metadata_catalog_hash(metadata_for_runtime(runtime))}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def planning_runtime_view(runtime, allowed, *, preserve_order=False):
    """Expose whole definitions for valid granted tools, never mutate runtime."""
    metadata = metadata_for_runtime(runtime)
    names = [name for name in (runtime.functions if preserve_order else sorted(runtime.functions))
             if name in allowed and metadata[name].registered]
    definitions = []
    for name in names:
        definition = deepcopy(runtime.functions[name])
        # Python deepcopy shares classes. A presentation-only schema snapshot
        # preserves the exact native JSON without exposing host Pydantic classes.
        schema = deepcopy(runtime.functions[name].parameters.model_json_schema())
        parameters = create_model(runtime.functions[name].parameters.__name__)
        parameters.model_json_schema = classmethod(lambda cls, _schema=schema, **kwargs: deepcopy(_schema))
        definition.parameters = parameters
        definitions.append(definition)
    view = FunctionsRuntime(definitions)
    return view, {'catalog_tools': len(runtime.functions), 'visible_tools': len(names)}


class L2AuthorizationError(ValueError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class ToolAuthorizationProfile:
    """An explicit, immutable host policy, not a learned task classifier."""
    name: str
    request_patterns: tuple[str, ...]
    allowed_seed_tools: frozenset[str]
    prerequisites: tuple[tuple[str, tuple[str, ...]], ...] = ()
    deterministic_reads: frozenset[str] = frozenset()
    version: str = 'host-profile-v1'

    def __post_init__(self):
        object.__setattr__(self, 'request_patterns', tuple(self.request_patterns))
        object.__setattr__(self, 'allowed_seed_tools', frozenset(self.allowed_seed_tools))
        object.__setattr__(self, 'deterministic_reads', frozenset(self.deterministic_reads))
        object.__setattr__(self, 'prerequisites', tuple(
            (key, tuple(values)) for key, values in self.prerequisites))
        if (not isinstance(self.name, str) or not self.name or len(self.name) > 128
                or not isinstance(self.version, str) or not self.version or len(self.version) > 128
                or not self.request_patterns or len(self.request_patterns) > 32
                or len(self.allowed_seed_tools) > 128 or len(self.prerequisites) > 128
                or not self.deterministic_reads <= self.allowed_seed_tools):
            raise ValueError('invalid host authorization profile')
        for pattern in self.request_patterns:
            if not isinstance(pattern, str) or not pattern or len(pattern) > 2048:
                raise ValueError('invalid host request pattern')
            re.compile(pattern)
        names = set(self.allowed_seed_tools)
        keys = set()
        graph = dict(self.prerequisites)
        for key, values in self.prerequisites:
            if key in keys or len(values) > 128:
                raise ValueError('duplicate or oversized host prerequisite')
            keys.add(key)
            names.add(key)
            names.update(values)
        if any(not isinstance(name, str) or not name or len(name) > 128 for name in names):
            raise ValueError('invalid host tool name')
        visiting, visited = set(), set()

        def visit(name):
            if name in visiting:
                raise ValueError('cyclic host read prerequisites')
            if name in visited:
                return
            visiting.add(name)
            for target in graph.get(name, ()):
                visit(target)
            visiting.remove(name)
            visited.add(name)

        for name in graph:
            visit(name)

    def matches(self, request):
        # Pattern authors are trusted host code; bounded input avoids unbounded work.
        return len(request) <= 2048 and any(re.fullmatch(p, request, re.I) for p in self.request_patterns)

    def identity(self):
        payload = {'name': self.name, 'version': self.version, 'patterns': self.request_patterns,
                   'allowed': sorted(self.allowed_seed_tools), 'prerequisites': sorted(self.prerequisites),
                   'deterministic_reads': sorted(self.deterministic_reads)}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def validate_runtime(self, runtime):
        metadata = metadata_for_runtime(runtime)
        names = set(self.allowed_seed_tools)
        reads = set(self.deterministic_reads)
        for source, targets in self.prerequisites:
            names.add(source)
            names.update(targets)
            reads.update(targets)
        if any(name not in runtime.functions or not metadata[name].registered for name in names):
            raise L2AuthorizationError('AUTH_PROFILE_INVALID')
        if any(metadata[name].metadata.effect != 'read' or metadata[name].metadata.sink != 'none'
               for name in reads):
            raise L2AuthorizationError('AUTH_PROFILE_INVALID')

    def read_closure(self, seeds, prohibited):
        graph = dict(self.prerequisites)
        allowed = set(seeds)
        pending = list(seeds)
        while pending:
            for target in graph.get(pending.pop(), ()):
                if target not in allowed:
                    allowed.add(target)
                    pending.append(target)
        if allowed & set(prohibited):
            raise L2AuthorizationError('AUTH_CONSTRAINT_CONFLICT')
        return frozenset(allowed), frozenset(allowed - set(seeds))


def validate_profile_decision(data, request, runtime, profile):
    """Check literal evidence and graph consistency, not semantic entailment."""
    if not isinstance(data, dict) or set(data) != {'tools', 'prohibited_tools', 'evidence'}:
        raise L2AuthorizationError('AUTH_INVALID_SCHEMA')
    seeds, prohibited, evidence = data['tools'], data['prohibited_tools'], data['evidence']
    for values in (seeds, prohibited):
        if (not isinstance(values, list) or len(values) > 128
                or any(not isinstance(name, str) or not name for name in values)
                or len(set(values)) != len(values)):
            raise L2AuthorizationError('AUTH_INVALID_SCHEMA')
    if (set(seeds) | set(prohibited)) - set(runtime.functions):
        raise L2AuthorizationError('AUTH_UNKNOWN_TOOL')
    if not set(seeds) <= profile.allowed_seed_tools:
        raise L2AuthorizationError('AUTH_PROFILE_TOOL_NOT_ALLOWED')
    if not isinstance(evidence, list) or len(evidence) > 256:
        raise L2AuthorizationError('AUTH_INVALID_SCHEMA')
    supported, forbidden, references = set(), set(), []
    for entry in evidence:
        if (not isinstance(entry, dict) or set(entry) != {'tool', 'kind', 'span'}
                or not isinstance(entry['tool'], str) or not isinstance(entry['kind'], str)
                or not isinstance(entry['span'], str) or not entry['span'].strip()):
            raise L2AuthorizationError('AUTH_EVIDENCE_INVALID')
        start = request.find(entry['span'])
        if start < 0:
            raise L2AuthorizationError('AUTH_EVIDENCE_INVALID')
        tool, kind = entry['tool'], entry['kind']
        if kind in {'direct', 'conditional'} and tool in seeds:
            supported.add(tool)
        elif kind == 'prohibited' and tool in prohibited:
            forbidden.add(tool)
        else:
            raise L2AuthorizationError('AUTH_EVIDENCE_INVALID')
        references.append((tool, kind, start, start + len(entry['span'])))
    if supported != set(seeds) or forbidden != set(prohibited):
        raise L2AuthorizationError('AUTH_EVIDENCE_INVALID')
    allowed, prepared = profile.read_closure(seeds, prohibited)
    return allowed, frozenset(prohibited), prepared, tuple(sorted(references))


MAX_TASK_SOURCE_CHARS = 1536
MAX_EFFECTIVE_TASK_CHARS = 2048
MAX_SERIALIZED_TASK_SOURCE = 16384
DELEGATION_VERSION = 'explicit-source-v2'


@dataclass(frozen=True)
class DelegatedTaskSource:
    kind: str
    locator: str
    sender: str = ''


def _validate_source_tail(restrictions):
    if not restrictions:
        return
    allowed = (r'only (?:query|check) inventory|do not (?:send|pay|write|delete|book|transfer)'
               r'(?: (?:emails?|messages?|payments?))?|'
               r'仅(?:查询|检查)库存|(?:不要|禁止)(?:发送|付款|修改|删除|预订|转账)(?:邮件|消息)?')
    clauses = re.split(r'[,;，；]', restrictions.rstrip('。.!！ ').strip())
    if not clauses or any(not re.fullmatch(allowed, c.strip(), re.I) for c in clauses):
        raise L2AuthorizationError('DELEGATED_RESTRICTION_UNSUPPORTED')


def _match_message_source(request):
    text = request.strip()
    # Match the complete request. Do not eagerly resolve a later compound task.
    text = re.sub(r'^Hey\s+this\s+is\s+[A-Za-z][A-Za-z -]{0,63}!\s*', '', text, flags=re.I)
    verb = r'(?:please\s+)?(?:do|complete|execute|perform|carry out)\s+(?:all\s+)?(?:the\s+)?'
    email = (verb + r'(?:actions|tasks|instructions)\s+(?:(?:specified|listed)\s+)?in\s+(?:the\s+)?email\s+from\s+'
             r'''(?P<q1>['"])(?P<sender>[^'"\s<>]+@[^'"\s<>]+)(?P=q1)\s+with\s+(?:the\s+)?subject\s+'''
             r'''(?P<q2>['"])(?P<subject>[^'"\n]+)(?P=q2)''')
    web = (verb + r'(?:actions|tasks|instructions)(?:\s+i\s+have)?\s+(?:in|on|from|at)\s+'
           r'(?:(?:my|the|our)\s+)?(?:(?:(?:todo|task)\s+list|webpage|page)\s+)?(?:at\s+)?'
           r'''(?P<url>(?:https?://|www\.)[^\s<>"';,!]+?)''')
    tail = r'(?:\s*[,;，；](?P<restrictions>.*))?\s*[。.!！]?\s*'
    for kind, pattern in (('email', email), ('web', web)):
        match = re.fullmatch(pattern + tail, text, re.I)
        if match:
            _validate_source_tail(match.group('restrictions'))
            return (DelegatedTaskSource(kind, match.group('subject'), match.group('sender')) if kind == 'email'
                    else DelegatedTaskSource(kind, match.group('url')))
    return None


def match_delegated_task(request):
    """Recognize finite explicit execute-file forms, not a file-name keyword."""
    if not isinstance(request, str) or len(request) > MAX_EFFECTIVE_TASK_CHARS:
        return None
    source = r'''(?P<source>"[^"\n]+\.(?:txt|md)"|'[^'\n]+\.(?:txt|md)'|[^\s,;，；"']+\.(?:txt|md))'''
    patterns = (
        r'(?:please\s+)?(?:complete|execute|perform|run|carry out)\s+(?:all\s+)?(?:the\s+)?tasks?\s+(?:in|from|listed in)\s+(?:the file\s+)?' + source,
        r'(?:please\s+)?(?:complete|execute|perform|run)\s+' + source + r'\s+(?:tasks?|instructions)',
        r'(?:请)?(?:完成|执行)(?:文件\s*)?\s*' + source + r'\s*(?:里的|中的|里|中|的)?\s*(?:全部|所有)?(?:任务|指令)',
    )
    for pattern in patterns:
        match = re.fullmatch(pattern + r'(?:\s*[,;，；](?P<restrictions>.*))?\s*[。.!！]?\s*', request.strip(), re.I)
        if match:
            # Only finite downstream clauses are supported. An arbitrary tail
            # could revoke the preparation read; never postpone that check to
            # the business compiler or rely on a read-deny Monitor exception.
            _validate_source_tail(match.group('restrictions'))
            name = match.group('source').strip('"\'')
            if name and all(c.isprintable() for c in name):
                return name
    return _match_message_source(request)


@dataclass(frozen=True)
class DelegatedTaskReader:
    """Trusted adapter configuration. Documents cannot create this object."""
    tool_name: str
    path_argument: str
    output_format: str = 'text'

    def __post_init__(self):
        if (not isinstance(self.tool_name, str) or not isinstance(self.path_argument, str)
                or not self.tool_name or not self.path_argument
                or self.output_format not in {'text', 'yaml_file'}):
            raise ValueError('invalid delegated task reader')

    def identity(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class DelegatedTaskSpec:
    source_name: str
    tool_name: str
    arguments_json: str
    output_format: str

    @property
    def arguments(self):
        return json.loads(self.arguments_json)

    def task_text(self, serialized):
        if not isinstance(serialized, str) or len(serialized) > MAX_SERIALIZED_TASK_SOURCE:
            raise L2AuthorizationError('DELEGATED_SOURCE_TOO_LONG')
        text = serialized
        if self.output_format in {'yaml_file', 'yaml_email'}:
            import yaml
            from baseintent.audit_context import parse_structured
            try:
                item = parse_structured(serialized, MAX_SERIALIZED_TASK_SOURCE)
            except (ValueError, yaml.YAMLError) as exc:
                raise L2AuthorizationError('DELEGATED_SOURCE_INVALID') from exc
            if self.output_format == 'yaml_email':
                arguments = self.arguments
                matches = [r for r in item if isinstance(r, dict)
                           and r.get('sender') == arguments['sender']
                           and r.get('subject') == arguments['query']] if isinstance(item, list) else []
                if len(matches) != 1 or not isinstance(matches[0].get('body'), str):
                    raise L2AuthorizationError('DELEGATED_SOURCE_INVALID')
                text = matches[0]['body']
            elif (not isinstance(item, dict) or item.get('filename') != self.source_name
                    or item.get('id_') != self.arguments.get('file_id')
                    or not isinstance(item.get('content'), str)):
                raise L2AuthorizationError('DELEGATED_SOURCE_INVALID')
            else:
                text = item['content']
        if not text.strip():
            raise L2AuthorizationError('DELEGATED_SOURCE_EMPTY')
        if len(text) > MAX_TASK_SOURCE_CHARS:
            raise L2AuthorizationError('DELEGATED_SOURCE_TOO_LONG')
        return text


def resolve_delegated_task(source_name, runtime, env, reader=None):
    """Resolve metadata/arguments only; actual content must pass tool mediation."""
    if reader is not None and not isinstance(reader, DelegatedTaskReader):
        raise TypeError('delegated_task_reader must be a trusted adapter')
    if isinstance(source_name, DelegatedTaskSource):
        if reader is not None:
            raise L2AuthorizationError('DELEGATED_READER_UNSUPPORTED')
        source = source_name
        if source.kind == 'email':
            tool, arguments, output = 'search_emails', {'query': source.locator, 'sender': source.sender}, 'yaml_email'
            label = 'email from ' + source.sender + ' with subject ' + source.locator
        elif source.kind == 'web':
            tool, arguments, output, label = 'get_webpage', {'url': source.locator}, 'text', source.locator
        else:
            raise L2AuthorizationError('DELEGATED_READER_UNSUPPORTED')
        status = metadata_for_runtime(runtime).get(tool)
        required_sink = 'external_recipient' if source.kind == 'web' else 'none'
        if (tool not in runtime.functions or status is None or not status.registered
                or status.metadata.effect != 'read' or status.metadata.sink != required_sink):
            raise L2AuthorizationError('DELEGATED_READER_INVALID')
        try:
            runtime.functions[tool].parameters.model_validate(arguments)
        except Exception as exc:
            raise L2AuthorizationError('DELEGATED_READER_INVALID') from exc
        return DelegatedTaskSpec(label, tool, json.dumps(arguments, sort_keys=True, ensure_ascii=False), output)
    if reader is None:
        spec = runtime.functions.get('read_file')
        fields = spec.parameters.model_fields if spec else {}
        argument = next((name for name in ('file_path', 'path') if name in fields), None)
        if argument:
            reader = DelegatedTaskReader('read_file', argument)
        elif 'get_file_by_id' in runtime.functions and getattr(env, 'cloud_drive', None) is not None:
            reader = DelegatedTaskReader('get_file_by_id', 'file_id', 'yaml_file')
        else:
            raise L2AuthorizationError('DELEGATED_READER_UNSUPPORTED')
    metadata = metadata_for_runtime(runtime).get(reader.tool_name)
    if (reader.tool_name not in runtime.functions or metadata is None or not metadata.registered
            or metadata.metadata.effect != 'read' or metadata.metadata.sink != 'none'):
        raise L2AuthorizationError('DELEGATED_READER_INVALID')
    target = source_name
    if reader.output_format == 'yaml_file':
        drive = getattr(env, 'cloud_drive', None)
        files = getattr(drive, 'files', None)
        if not isinstance(files, dict):
            raise L2AuthorizationError('DELEGATED_SOURCE_UNAVAILABLE')
        matches = [key for key, item in files.items() if getattr(item, 'filename', None) == source_name]
        if len(matches) != 1:
            raise L2AuthorizationError('DELEGATED_SOURCE_UNAVAILABLE')
        target = matches[0]
    arguments = {reader.path_argument: target}
    if reader.path_argument not in runtime.functions[reader.tool_name].parameters.model_fields:
        raise L2AuthorizationError('DELEGATED_READER_INVALID')
    try:
        runtime.functions[reader.tool_name].parameters.model_validate(arguments)
    except Exception as exc:
        raise L2AuthorizationError('DELEGATED_READER_INVALID') from exc
    return DelegatedTaskSpec(source_name, reader.tool_name,
                             json.dumps(arguments, sort_keys=True, ensure_ascii=False), reader.output_format)


def effective_delegated_task(original_request, source_name, task_text):
    text = (f'Original user request (its restrictions remain in force):\n{original_request}\n\n'
            f'User-delegated business tasks from {source_name}:\n{task_text}')
    normalized = unicodedata.normalize('NFKC', text)
    visible_length = sum(1 if c in '\n\t' or c.isprintable() else len(f'\\u{ord(c):04x}')
                         for c in normalized)
    if visible_length > MAX_EFFECTIVE_TASK_CHARS:
        raise L2AuthorizationError('DELEGATED_TASK_INPUT_TOO_LONG')
    return text


@dataclass(frozen=True)
class EffectiveTaskContext:
    original_request: str
    effective_request: str
    catalog_sha256: str
    stage: str
    source: DelegatedTaskSpec | None = None
    bootstrap_call_id: str = ''
