"""Sequential benchmark binding checks and result-directory lock."""
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
from uuid import uuid4
import shutil

from experiments.common.partial_controls import RunConfigurationError, guard_run
from experiments.common.benchmark_reuse import _compatible_binding


@contextmanager
def run_lock(base):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    with (base / '.benchmark.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RunConfigurationError('another benchmark invocation is using this run directory') from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class PreparedBindings:
    """Validate a complete fresh/cache plan without partially writing bindings."""
    def __init__(self):
        self.checked, self.pending, self.evidence = {}, {}, {}
        self.transitions = []
        self.committed = False

    def check(self, path, expected):
        path = Path(path)
        if path in self.checked and self.checked[path] != expected:
            raise RunConfigurationError('inconsistent prepared run identity')
        if path.exists():
            previous = json.loads(path.read_text())
            if not _compatible_binding(previous, expected):
                raise RunConfigurationError(f'run configuration changed: {path}; use a new --name')
            if previous != expected:
                self.transitions.append((path, previous, expected))
            self.evidence[path] = path.read_bytes()
        else:
            if path.parent.exists() and ((path.parent / 'summary.json').exists()
                    or any(path.parent.rglob('injection_task_*.json')) or any(path.parent.rglob('none.json'))):
                raise RunConfigurationError('unbound historical cache; use a new --name')
            self.pending[path] = expected
        self.checked[path] = expected
        return expected

    def commit(self):
        if any(p.read_bytes() != h for p, h in self.evidence.items()):
            raise RunConfigurationError('run evidence changed during preparation')
        if self.transitions:
            root = next(path.parent for path in self.checked
                        if path.name in {'screened_run_manifest.json', 'benchmark_plan.json', 'suite_manifest.json'})
            destination = root / 'validation' / uuid4().hex
            destination.mkdir(parents=True)
            snapshots = []
            for path in root.rglob('*'):
                if (not path.is_file() or path.is_relative_to(root / 'validation')
                        or path.is_relative_to(root / 'reuse')):
                    continue
                if path.name in {'summary.json', 'summary.md', 'attack_manifest.json', 'report.txt',
                                 'all_report.txt', 'failure_cases.jsonl', 'detailed_results.csv', 'preflight_report.json'}:
                    target = destination / 'snapshot' / path.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
                    snapshots.append(str(path.relative_to(root)))
            record = {'verification_mode': 'configuration_only', 'source_equivalence_verified': False,
                      'transitions': [{'path':str(p.relative_to(root)), 'original_binding':old, 'current_binding':new}
                                      for p, old, new in self.transitions],
                      'previous_aggregate_snapshots': snapshots}
            (destination / 'configuration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        for path, value in self.pending.items():
            guard_run(path, value)
        self.committed = True

    def guard(self, path, expected):
        path = Path(path)
        if not self.committed or self.checked.get(path) != expected:
            raise RunConfigurationError('execution differs from validated plan')
        recorded = json.loads(path.read_text())
        if not _compatible_binding(recorded, expected):
            raise RunConfigurationError('run evidence changed after preparation')
        return recorded


class ApprovedBindings:
    """Read-only, prevalidated bindings for sequential execution."""
    def __init__(self, plan):
        self.checked = plan.checked
        self.recorded = {p: json.loads(p.read_text()) for p in self.checked}

    def guard(self, path, expected):
        path = Path(path)
        if (self.checked.get(path) != expected or
                json.loads(path.read_text()) != self.recorded[path]):
            raise RunConfigurationError('execution configuration/evidence differs from approved plan')
        return self.recorded[path]
