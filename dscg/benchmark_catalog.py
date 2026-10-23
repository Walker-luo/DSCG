"""Runtime-selected AgentDojo and AgentDyn catalogues using installation metadata.

Importing this module never probes a backend or constructs a model. Conda names
are deliberately irrelevant: installed origin, version and revision decide.
"""
from copy import deepcopy
from dataclasses import dataclass
from importlib.metadata import distribution
from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import urlparse

SUITE_VERSION = 'v1.2'
_CONFIG = Path(__file__).resolve().parents[1] / 'config'


class BenchmarkConfigurationError(ValueError):
    """Installed backend is absent or has unsupported installation metadata."""


@dataclass(frozen=True)
class BackendProfile:
    id: str
    label: str
    repository: str
    suites: tuple[str, ...]
    labels: tuple[str, ...]
    lock_path: Path
    tool_metadata_path: Path
    suite_version: str = SUITE_VERSION


PROFILES = {
    'agentdojo': BackendProfile('agentdojo','AgentDojo','https://github.com/ethz-spylab/agentdojo',
        ('workspace','travel','banking','slack'),('Workspace','Travel','Banking','Slack'),
        _CONFIG/'agentdojo.lock.json',_CONFIG/'tools.agentdojo-v1.2.toml'),
    'agentdyn': BackendProfile('agentdyn','AgentDyn','https://github.com/SaFo-Lab/AgentDyn',
        ('shopping','github','dailylife'),('Shopping','GitHub','Daily Life'),
        _CONFIG/'agentdyn.lock.json',_CONFIG/'tools.agentdyn-v1.2.toml'),
}


def _package_root():
    import agentdojo
    return Path(agentdojo.__file__).resolve().parent


@lru_cache(maxsize=2)
def _load_lock(profile):
    try:
        return json.loads(profile.lock_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise BenchmarkConfigurationError(f'{profile.label} lock missing/invalid: {profile.lock_path.name}') from exc


def _inspect_backend():
    try:
        installed = distribution('agentdojo')
        origin = json.loads(installed.read_text('direct_url.json') or '{}')
        if not isinstance(origin,dict): raise ValueError('invalid origin')
    except Exception as exc:
        raise BenchmarkConfigurationError('benchmark installation source unavailable') from exc
    url = str(origin.get('url','')).removesuffix('.git')
    if url == PROFILES['agentdyn'].repository:
        profile = PROFILES['agentdyn']
    elif not origin or ('archive_info' in origin and not origin.get('vcs_info')):
        profile = PROFILES['agentdojo']
    else:
        raise BenchmarkConfigurationError('unknown benchmark installation source/origin; use reviewed AgentDojo or AgentDyn')
    lock = _load_lock(profile)
    if (not isinstance(lock,dict) or lock.get('schema_version') != f'dscg.{profile.id}-lock.v1'
            or lock.get('repository') != profile.repository or lock.get('suite_version') != SUITE_VERSION
            or installed.version != lock.get('package_version') or installed.version != '0.1.35'):
        raise BenchmarkConfigurationError(f'invalid {profile.label} lock/version identity')
    if profile.id == 'agentdyn':
        if (not re.fullmatch(r'[a-f0-9]{40}',str(lock.get('revision','')))
                or origin.get('vcs_info',{}).get('vcs') != 'git'
                or origin.get('vcs_info',{}).get('commit_id') != lock['revision']):
            raise BenchmarkConfigurationError('AgentDyn source/revision mismatch; use pinned ipi-agentdyn')
    else:
        if lock.get('revision') != 'pypi:agentdojo==0.1.35' or not re.fullmatch(r'[a-f0-9]{64}',str(lock.get('release_sha256',''))):
            raise BenchmarkConfigurationError('invalid AgentDojo release identity')
        if origin:
            archive_url = urlparse(str(origin.get('url', '')))
            # The declared source is checked; archive/source contents are not.
            official_remote = (archive_url.scheme == 'https'
                               and archive_url.hostname == 'files.pythonhosted.org'
                               and Path(archive_url.path).name == lock.get('release_filename'))
            local_release = (archive_url.scheme == 'file'
                             and Path(archive_url.path).name == lock.get('release_filename'))
            if not (official_remote or local_release):
                raise BenchmarkConfigurationError('unknown AgentDojo archive source/origin')
    # Resolve the actual imported location for diagnostics without traversing it.
    root = _package_root().resolve()
    if hasattr(installed, 'locate_file') and root != Path(installed.locate_file('agentdojo')).resolve():
        raise BenchmarkConfigurationError('imported agentdojo path differs from installed distribution')
    identity = {'id': profile.id, 'repository': profile.repository, 'revision': lock['revision'],
                'suite_version': SUITE_VERSION, 'package_version': installed.version,
                'source_kind': 'pypi-release' if profile.id == 'agentdojo' else 'git',
                'verification_mode': 'metadata_only', 'runtime_variant': 'unverified'}
    return profile,identity


_BACKEND_FIELDS = ('id', 'repository', 'revision', 'suite_version', 'package_version', 'source_kind')


def same_backend(recorded, current):
    """Compare declared backend identity, including old hash-bearing records."""
    if not isinstance(recorded, dict) or not isinstance(current, dict):
        return False
    required = ('id', 'repository', 'revision', 'suite_version')
    if any(not isinstance(recorded.get(k), str) or not isinstance(current.get(k), str) for k in required):
        return False
    return all(recorded.get(k) == current.get(k) for k in _BACKEND_FIELDS)


def get_backend():
    return _inspect_backend()[0]


def get_suites():
    return get_backend().suites


def validate_backend():
    return _inspect_backend()[1]


def benchmark_identity():
    return deepcopy(validate_backend())


def get_suite(version, name):
    profile=get_backend()
    if version != profile.suite_version or name not in profile.suites:
        raise BenchmarkConfigurationError(f'{profile.label} execution supports {profile.suite_version}: {", ".join(profile.suites)}')
    from agentdojo.task_suite import get_suite as native_get_suite
    return native_get_suite(version,name)


def suite_catalog():
    profile=get_backend()
    from agentdojo.task_suite import get_suite as native_get_suite
    return [dict(id=name,label=label,user_tasks=len(native_get_suite(SUITE_VERSION,name).user_tasks),
        injection_tasks=len(native_get_suite(SUITE_VERSION,name).injection_tasks)) for name,label in zip(profile.suites,profile.labels)]


def main():
    print(json.dumps({'benchmark':benchmark_identity(), 'import_path':str(_package_root()),
                      'suites':suite_catalog()},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
