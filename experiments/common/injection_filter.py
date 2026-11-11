"""Minimal, backend-bound injection exclusions (the CLI spelling is --fliter)."""
import hashlib
import json
from pathlib import Path

from dscg.benchmark_catalog import benchmark_identity, get_backend, get_suite

SCHEMA = 'dscg.fliter.v1'


def benchmark_header():
    identity = benchmark_identity()
    return {key: identity[key] for key in ('id', 'suite_version', 'revision')}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f'duplicate JSON key: {key}')
        value[key] = item
    return value


def load_fliter(path):
    """Read once and reject stale backend identities, unknown IDs and old cohorts."""
    data = json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'benchmark', 'excluded'}
            or data['schema_version'] != SCHEMA):
        raise ValueError('expected minimal dscg.fliter.v1 exclusion file')
    if data['benchmark'] != benchmark_header():
        raise ValueError('fliter benchmark id/suite_version/revision mismatch')
    excluded = data['excluded']
    if not isinstance(excluded, dict):
        raise ValueError('fliter excluded must be a suite-to-ID-list object')
    backend = get_backend()
    for suite, ids in excluded.items():
        if suite not in backend.suites:
            raise ValueError(f'unknown fliter suite: {suite}')
        if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
            raise ValueError(f'fliter {suite} requires injection task IDs')
        if len(ids) != len(set(ids)):
            raise ValueError(f'duplicate injection task IDs in fliter {suite}')
        registered = get_suite(data['benchmark']['suite_version'], suite).injection_tasks
        if any(item not in registered for item in ids):
            raise ValueError(f'unknown injection task ID in fliter {suite}')
    return {**data, 'excluded': {suite: sorted(ids) for suite, ids in sorted(excluded.items())}}


def filter_digest(data):
    canonical = {**data, 'excluded': {suite: sorted(ids) for suite, ids in data['excluded'].items()}}
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def excluded_ids(data, suite):
    return list(data['excluded'].get(suite, []))
