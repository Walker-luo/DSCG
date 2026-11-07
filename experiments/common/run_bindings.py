"""One immutable run configuration, expanded into virtual native group bindings."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from experiments.common.partial_controls import RunConfigurationError
from experiments.common.benchmark_reuse import _compatible_binding, snapshot_run_evidence

SCHEMA = 'dscg.run.v3'
LAYOUT = 'flat-v1'


def load_run_bindings(base):
    raw = json.loads((Path(base) / 'run_manifest.json').read_text())
    if raw.get('schema_version') != SCHEMA or raw.get('task_layout') != LAYOUT:
        raise RunConfigurationError('unsupported run manifest/layout; use a new name')
    result = {key: dict(value) for key, value in raw.get('bindings', {}).items()}
    result.update({key + '/run_manifest.json': {**raw.get('common', {}), **value}
                   for key, value in raw.get('groups', {}).items()})
    return result


class RunBindings:
    def __init__(self, base, *, reuse=False):
        self.base = Path(base)
        self.checked = {}
        self.committed = False
        path = self.base / 'run_manifest.json'
        self.evidence = path.read_bytes() if path.exists() else None
        self.existing = load_run_bindings(base) if self.evidence is not None else {}
        if reuse and not self.existing:
            raise RunConfigurationError('new layout requires a matching run_manifest.json; use a new name')
        if not self.existing and (any(self.base.glob('*/*/run_manifest.json'))
                or (self.base / 'summary.json').exists() or any(self.base.rglob('injection_task_*.json'))
                or any(self.base.rglob('none.json'))):
            raise RunConfigurationError('unbound/legacy run layout; preserve it and use a new name')
        self.reuse = reuse

    def check(self, path, expected):
        path = Path(path)
        key = path.relative_to(self.base).as_posix()
        if self.existing and (key not in self.existing or not _compatible_binding(self.existing[key], expected)):
            raise RunConfigurationError('run configuration changed; use a new name')
        if path in self.checked and self.checked[path] != expected:
            raise RunConfigurationError('inconsistent prepared identity')
        self.checked[path] = expected
        return self.existing.get(key, expected)

    def commit(self):
        path = self.base / 'run_manifest.json'
        if self.evidence is not None and path.read_bytes() != self.evidence:
            raise RunConfigurationError('run evidence changed during preparation')
        if self.existing and set(self.existing) != {p.relative_to(self.base).as_posix() for p in self.checked}:
            raise RunConfigurationError('run scope changed')
        groups = {p.relative_to(self.base).parent.as_posix(): value
                  for p, value in self.checked.items() if p.name == 'run_manifest.json'}
        common = {key: value for key, value in next(iter(groups.values()), {}).items()
                  if all(key in group and group[key] == value for group in groups.values())}
        data = dict(schema_version=SCHEMA, task_layout=LAYOUT, common=common,
                    groups={name: {k: v for k, v in group.items() if k not in common}
                            for name, group in groups.items()},
                    bindings={p.relative_to(self.base).as_posix(): value
                              for p, value in self.checked.items() if p.name != 'run_manifest.json'})
        if not self.existing:
            self.base.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(mode='w', dir=self.base, prefix='.run-manifest-', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)  # exclusive publication; no partially written binding
            finally:
                temporary.unlink(missing_ok=True)
            self.evidence = path.read_bytes()
        if self.reuse:
            destination = self.base / 'reuse' / uuid4().hex
            destination.mkdir(parents=True)
            snapshots = snapshot_run_evidence(self.base, destination)
            (destination / 'compatibility.json').write_text(json.dumps({
                'verification_mode': 'configuration_only', 'source_equivalence_verified': False,
                'previous_aggregate_snapshots': snapshots}, ensure_ascii=False, indent=2)+'\n')
        self.committed = True

    def guard(self, path, expected):
        if not self.committed or self.checked.get(Path(path)) != expected:
            raise RunConfigurationError('execution differs from prepared run')
        if (self.base / 'run_manifest.json').read_bytes() != self.evidence:
            raise RunConfigurationError('run binding changed after preparation')
        return self.existing.get(Path(path).relative_to(self.base).as_posix(), expected)
