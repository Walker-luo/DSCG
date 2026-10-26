"""Bounded semantic evidence for auditing; never an authorization channel."""
import json
import re
import unicodedata

import yaml

INPUT_SCHEMA = 'dscg.audit-input.v2'
EVIDENCE_VERSION = 'task-evidence-v2'
MAX_RESULTS = 8
RECENT_RESULTS = 4
FACT_BUDGET = 8192
MAX_CALL_ARGUMENTS = 1024
MAX_SOURCE_RETURNS = 256
MAX_STRUCTURED_BYTES = 131072
FILE_FIELDS = frozenset({'id_', 'filename', 'size', 'owner', 'shared_with', 'last_modified', 'content'})


class _InvalidEvidence(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if not isinstance(key, str) or key in result or key == '<<':
            raise _InvalidEvidence('duplicate/invalid field')
        result[key] = value
    return result


class _Loader(yaml.SafeLoader):
    pass


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                        lambda loader, node: _pairs(loader.construct_pairs(node, deep=True)))


def parse_structured(text, max_bytes=MAX_STRUCTURED_BYTES):
    """Strict JSON/YAML values; aliases, tags and duplicate fields are rejected."""
    if len(text.encode('utf-8')) > max_bytes:
        raise _InvalidEvidence('size')
    depth = 0
    try:
        for token in yaml.scan(text):
            if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken, yaml.tokens.TagToken)):
                raise _InvalidEvidence('YAML references/tags')
            if isinstance(token, (yaml.tokens.BlockMappingStartToken, yaml.tokens.BlockSequenceStartToken,
                                  yaml.tokens.FlowMappingStartToken, yaml.tokens.FlowSequenceStartToken)):
                depth += 1
                if depth > 16:
                    raise _InvalidEvidence('nesting')
            elif isinstance(token, (yaml.tokens.BlockEndToken, yaml.tokens.FlowMappingEndToken,
                                    yaml.tokens.FlowSequenceEndToken)):
                depth -= 1
        return (json.loads(text, object_pairs_hook=_pairs) if text.lstrip().startswith(('[', '{'))
                else yaml.load(text, Loader=_Loader))
    except (RecursionError, OverflowError) as exc:
        raise _InvalidEvidence('parser depth/size') from exc


def _file_metadata(text, name, query):
    """Only size-comparison tasks may omit free document bodies, keeping all rows."""
    if name not in {'list_files', 'search_files', 'search_files_by_filename', 'get_file_by_id'}:
        return None
    if not re.search(r'\b(?:largest|smallest|biggest)\s+files?\b|\bfile\s+sizes?\b|最大.*文件|最小.*文件', query, re.I):
        return None
    if re.search(r'\b(?:summari[sz]e|summary|contents?|read|quote|analy[sz]e)\b|摘要|总结|正文|内容|引用|分析', query, re.I):
        return None
    if len(text.encode('utf-8')) > MAX_STRUCTURED_BYTES:
        return None
    try:
        rows = parse_structured(text)
        rows = [rows] if isinstance(rows, dict) else rows
        if not isinstance(rows, list) or not rows or len(rows) > 512:
            return None
        identities = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != FILE_FIELDS:
                return None
            if (not isinstance(row['id_'], str) or not row['id_'] or row['id_'] in identities
                    or type(row['size']) is not int or row['size'] < 0
                    or not all(isinstance(row[k], str) for k in ('filename', 'owner', 'content'))
                    or not isinstance(row['shared_with'], dict)
                    or not all(isinstance(k, str) and isinstance(v, str) for k, v in row['shared_with'].items())):
                return None
            identities.add(row['id_'])
        return json.dumps([{k: v for k, v in row.items() if k != 'content'} for row in rows],
                          ensure_ascii=False, separators=(',', ':'), default=str)
    except (ValueError, TypeError, yaml.YAMLError):
        return None


def _value(call, name, default=None):
    return call.get(name, default) if isinstance(call, dict) else getattr(call, name, default)


def _anchors(value, key='', depth=0):
    if depth > 4 or key in {'body', 'content', 'message'}:
        return set()
    if isinstance(value, str):
        return {unicodedata.normalize('NFKC', value).casefold()} if 1 <= len(value) <= 256 else set()
    if isinstance(value, dict):
        return set().union(*(_anchors(v, k, depth + 1) for k, v in list(value.items())[:64])) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(_anchors(v, key, depth + 1) for v in value[:64])) if value else set()
    return set()


def _share_budget(lengths, budget):
    sizes = [0] * len(lengths)
    active = list(range(len(lengths)))
    while active and budget:
        share = max(1, budget // len(active))
        for i in active:
            amount = min(lengths[i] - sizes[i], share, budget)
            sizes[i] += amount
            budget -= amount
        active = [i for i in active if sizes[i] < lengths[i]]
    return sizes


def select_tool_evidence(messages, query, calls, normalize_text, normalize_value, argument_flags, *, preserve_complete=True):
    current = []
    found_user = False
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        if message.get('role') == 'user':
            current = []
            found_user = True
        elif found_user and message.get('role') == 'tool':
            current.append(message)
    anchors = set().union(*(_anchors(_value(c, 'args', {})) for c in calls)) if calls else set()
    anchors.update(unicodedata.normalize('NFKC', x).casefold() for x in
                   re.findall(r'[\w.+-]+@[\w.-]+|[\w.-]+\.(?:docx?|xlsx?|txt|md)|https?://[^\s\"\']+', query))
    prepared = []
    metadata_only_action = bool(calls) and all(_value(c, 'function') == 'delete_file' for c in calls)
    for index, message in enumerate(current[-MAX_SOURCE_RETURNS:]):
        call = message.get('tool_call')
        name = _value(call, 'function', message.get('name', '')) or ''
        content = message.get('content') or []
        text = content if isinstance(content, str) else ''.join(
            b.get('content', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
        projected = (_file_metadata(text, name, query) if metadata_only_action and not message.get('error') else None)
        evidence_text = normalize_text(projected if projected is not None else text, MAX_STRUCTURED_BYTES)
        raw_args = _value(call, 'args', {})
        loss_flags = argument_flags(raw_args)
        arguments = normalize_value(raw_args)
        encoded = json.dumps(arguments, ensure_ascii=False, default=str)
        bounded_error = normalize_text(message['error']) if message.get('error') else ''
        error = bounded_error[:512] or None
        argument_budget = MAX_CALL_ARGUMENTS - len(error or '')
        args_truncated = len(encoded) > argument_budget or loss_flags['arguments_truncated']
        if len(encoded) > argument_budget:
            # The bound applies after the preview has been JSON-escaped again.
            arguments = {'truncated_preview': encoded[:128]}
            encoded = json.dumps(arguments, ensure_ascii=False)
        searchable = unicodedata.normalize('NFKC', evidence_text + '\n' + encoded).casefold()
        relevance = sum(anchor in searchable for anchor in anchors)
        prepared.append((relevance, index, {
            'trust': 'untrusted', 'tool_name': normalize_text(name, 128),
            'tool_call_id': normalize_text(message.get('tool_call_id') or '', 96),
            'call_arguments': arguments, 'call_arguments_truncated': args_truncated,
            'call_arguments_nonfinite_or_unsupported': (call is None or not isinstance(raw_args, dict)
                                                       or loss_flags['arguments_nonfinite_or_unsupported']),
            'content': evidence_text, 'content_truncated': False,
            'representation': 'file_metadata' if projected is not None else 'raw',
            'omitted_fields': ['content'] if projected is not None else [],
            'error': error,
            'error_truncated': len(bounded_error) > 512,
        }, len(encoded), len(error or '')))
    # Evidence ranking is presentation only. It cannot grant a capability or certify a fact.
    # Always retain recent corrections; candidate matches must not hide new contradictions.
    selected = prepared[-RECENT_RESULTS:] + sorted(
        prepared[:-RECENT_RESULTS], key=lambda r: (r[0], r[1]), reverse=True
    )[:MAX_RESULTS - min(RECENT_RESULTS, len(prepared))]
    selected.sort(key=lambda r: r[1])
    remaining = max(0, FACT_BUDGET - sum(row[3] + row[4] for row in selected))
    lengths = [len(row[2]['content']) for row in selected]
    sizes = _share_budget(lengths, remaining)
    if preserve_complete:
        # Candidate matches must not shrink the former coverage of recent corrections.
        recent_start = len(selected) - min(RECENT_RESULTS, len(prepared))
        sizes = [size if i >= recent_start else min(512, size) for i, size in enumerate(sizes)]
        remaining -= sum(sizes)
        for i in sorted(range(len(selected)), key=lambda i: (selected[i][0], selected[i][1]), reverse=True):
            needed = lengths[i] - sizes[i]
            if needed <= remaining:
                sizes[i] += needed
                remaining -= needed
        extra = _share_budget([length - size for length, size in zip(lengths, sizes)], remaining)
        sizes = [size + addition for size, addition in zip(sizes, extra)]
    results = []
    for row, limit in zip(selected, sizes):
        item = row[2]
        item['content_truncated'] = len(item['content']) > limit
        item['content'] = item['content'][:limit]
        results.append(item)
    omitted = len(current) - len(results)
    return results, bool(omitted), {
        'version': EVIDENCE_VERSION if preserve_complete else 'task-evidence-v1', 'available_results': len(current),
        'selected_results': len(results), 'omitted_results': omitted,
        'content_characters': sum(len(r['content']) for r in results),
        'call_argument_characters': sum(row[3] for row in selected),
        'error_characters': sum(row[4] for row in selected),
        'fact_budget': FACT_BUDGET,
    }
