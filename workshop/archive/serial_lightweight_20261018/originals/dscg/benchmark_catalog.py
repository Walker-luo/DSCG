"""Runtime-selected, byte-verified AgentDojo and AgentDyn benchmark catalogues.

Importing this module never probes a backend or constructs a model. Conda names
are deliberately irrelevant: installed origin and reviewed source bytes decide.
"""
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import re

SUITE_VERSION = 'v1.2'
_CONFIG = Path(__file__).resolve().parents[1] / 'config'


class BenchmarkConfigurationError(ValueError):
    """Installed backend is absent, unknown, or differs from reviewed bytes."""


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


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _package_root():
    import agentdojo
    return Path(agentdojo.__file__).resolve().parent


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
            or installed.version != lock.get('package_version') or installed.version != '0.1.35'
            or not isinstance(lock.get('source_sha256'),dict) or not lock['source_sha256']):
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
            archive = origin.get('archive_info',{})
            release_hash = archive.get('hashes',{}).get('sha256') or str(archive.get('hash','')).removeprefix('sha256=')
            if release_hash != lock['release_sha256']:
                raise BenchmarkConfigurationError('AgentDojo archive source hash differs from reviewed official release')
    root = _package_root().resolve()
    suffixes={'.py','.yaml','.yml','.json','.txt','.jinja','.jinja2'}
    source_files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.suffix in suffixes}
    if source_files != set(lock['source_sha256']):
        raise BenchmarkConfigurationError(f'{profile.label} source file set differs from reviewed lock')
    actual = {}
    for relative in lock['source_sha256']:
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise BenchmarkConfigurationError(f'{profile.label} locked file missing: {relative}')
        actual[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    variant = 'official-release' if profile.id == 'agentdojo' else 'pinned-git'
    if actual != lock['source_sha256']:
        matched = []
        # Variants are exact whole-runtime identities, never per-file alternatives
        # that could admit an unreviewed mixture of independently allowed files.
        for name, overrides in lock.get('runtime_variants',{}).items():
            if isinstance(overrides,dict) and set(overrides) <= set(lock['source_sha256']):
                expected = {**lock['source_sha256'],**overrides}
                if actual == expected: matched.append(name)
        if profile.id != 'agentdojo' or len(matched) != 1:
            mismatch = next((key for key in actual if actual[key] != lock['source_sha256'][key]),'unknown')
            raise BenchmarkConfigurationError(f'{profile.label} source hash mismatch: {mismatch}')
        variant = matched[0]
    active = {k:v for k,v in actual.items() if any(f'/{name}/' in '/'+k for name in profile.suites)}
    roles = {
        'tasks': {k:v for k,v in active.items() if k.endswith(('/user_tasks.py','/injection_tasks.py'))},
        'environments': {k:v for k,v in active.items() if k.startswith('data/') or k.endswith('/task_suite.py')},
        'attacks': {k:v for k,v in actual.items() if k.startswith('attacks/')},
        'tools': {k:v for k,v in actual.items() if k.startswith('default_suites/v1/tools/') or
                  (k in active and k.endswith('/task_suite.py'))},
    }
    identity = {'id':profile.id,'repository':profile.repository,'revision':lock['revision'],
        'suite_version':SUITE_VERSION,'implementation_sha256':_digest(actual),
        'catalog_sha256':_digest({**active,**roles['attacks']}),
        **{role+'_sha256':_digest(files) for role,files in roles.items()},
        'package_version':installed.version,'runtime_variant':variant,
        'source_kind':'pypi-release' if profile.id=='agentdojo' else 'git'}
    if profile.id=='agentdojo': identity['release_sha256']=lock['release_sha256']
    return profile,identity


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
    print(json.dumps({'benchmark':benchmark_identity(),'suites':suite_catalog()},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
