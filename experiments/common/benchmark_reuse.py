"""Explicit task-cache resume: validate everything before touching run evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from uuid import uuid4

from agentdojo.benchmark import load_task_results
from pydantic import ValidationError

from experiments.common.partial_controls import RunConfigurationError
from dscg.benchmark_catalog import benchmark_identity, same_backend


def _read(path):
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict): raise ValueError('expected an object')
        return value
    except (OSError, ValueError) as exc:
        raise RunConfigurationError(f'invalid resume metadata: {path}') from exc


def compatible_source(old, current):
    """Source bytes and Python patch versions are informational only."""
    return (isinstance(old, dict) and isinstance(current, dict)
            and same_backend(old.get('benchmark'), current.get('benchmark'))
            and same_backend(current.get('benchmark'), benchmark_identity())
            and old.get('agentdojo') == current.get('agentdojo'))


_PROVENANCE_FIELDS = {'source', 'screening_script_sha256', 'verification_mode', 'tool_metadata_selection'}


def configuration(value):
    """Normalize provenance out, retaining every effective configuration field."""
    if not isinstance(value, dict):
        return value
    result = {key: item for key, item in value.items() if key not in _PROVENANCE_FIELDS}
    if value.get('schema_version') == 'dscg.screened-run.v2':
        # Effective tool contents are checked in every group binding.
        result.pop('tool_metadata_sha256', None)
        result.pop('tool_metadata_path', None)
    if isinstance(value.get('benchmark'), dict):
        result['benchmark'] = {key: value['benchmark'].get(key) for key in
                               ('id', 'repository', 'revision', 'suite_version', 'package_version', 'source_kind')}
    return result


def _compatible_binding(old, current):
    return old == current or (same_backend(old.get('benchmark'), current.get('benchmark'))
            and configuration(old) == configuration(current))


def execution_plan(task_scope, suites, attacks, cohort_sha256=None):
    result = {'schema_version': 'dscg.benchmark-plan.v2', 'benchmark': benchmark_identity(), 'task_scope': task_scope,
              'suites': list(suites), 'attacks': list(attacks)}
    if cohort_sha256 is not None: result['cohort_sha256'] = cohort_sha256
    return result


class ReusePlan:
    """Read/validate, then snapshot/commit, then delegate to the native cache."""
    def __init__(self, base, *, suites, attack, run_attack, task_scope, resolve_attacks):
        self.base = Path(base)
        if not self.base.is_dir():
            raise RunConfigurationError('--reuse directory does not exist; use the original --name/results directory')
        self.existing_runs = set(self.base.glob('*/*/run_manifest.json'))
        if not self.existing_runs:
            raise RunConfigurationError('--reuse requires existing verifiable run manifests')
        self.checked = {}; self.pending = {}; self.evidence = {}; self.transitions = []
        self.committed = False
        roots = [self.base / p for p in ('benchmark_plan.json', 'screened_run_manifest.json', 'attack_manifest.json', 'suite_manifest.json')]
        metadata = [(p.name, _read(p)) for p in roots if p.exists()]
        screened = next((item for name, item in metadata if name == 'screened_run_manifest.json'), None)
        active = ([name for name, entry in screened['selected_tasks'].items() if entry['injection_task_ids']]
                  if screened is not None else None)
        recorded_attacks = []; recorded_suites = []
        for filename, item in metadata:
            if not same_backend(item.get('benchmark'), benchmark_identity()):
                raise RunConfigurationError('recorded benchmark identity differs; use a new run for the current backend')
            if 'task_scope' in item and item['task_scope'] != task_scope:
                raise RunConfigurationError('--reuse task scope differs from original run')
            if 'attacks' in item:
                names = item['attacks'] or ['none']
                recorded_attacks.append(names)
            names = item.get('requested_suites', item.get('suites'))
            # Screened root identity stores the requested plan; native summaries
            # and partial suite bindings store only nonempty, active suites.
            if names is not None:
                if screened is not None and filename in {'attack_manifest.json', 'suite_manifest.json'}:
                    if names != active:
                        raise RunConfigurationError('recorded active suites differ from screened selection')
                else:
                    recorded_suites.append(names)
        if any(v != recorded_attacks[0] for v in recorded_attacks):
            raise RunConfigurationError('inconsistent recorded attack lists')
        if any(v != recorded_suites[0] for v in recorded_suites):
            raise RunConfigurationError('inconsistent recorded suite lists')
        if not recorded_attacks and attack is None and run_attack:
            raise RunConfigurationError('old run lacks attack plan; provide the complete original --attack list')
        if not recorded_suites and suites is None:
            raise RunConfigurationError('old run lacks suite plan; provide the complete original --suites list')
        self.attacks = (resolve_attacks(attack) if attack is not None else recorded_attacks[0]) if run_attack else ['none']
        self.suites = list(suites) if suites is not None else recorded_suites[0]
        if recorded_attacks and self.attacks != recorded_attacks[0]:
            raise RunConfigurationError('--reuse must keep the original attacks (old typical may include injecagent)')
        if recorded_suites and self.suites != recorded_suites[0]:
            raise RunConfigurationError('--reuse must keep the original suites')
        if not self.suites or not self.attacks or not all(isinstance(v, str) for v in self.suites + self.attacks):
            raise RunConfigurationError('invalid recorded run plan')
        if run_attack: resolve_attacks(self.attacks)  # Reject unknown, removed or interactive attacks.
        elif recorded_attacks and recorded_attacks[0] != ['none']:
            raise RunConfigurationError('--clean differs from the original run')
        print(f'显式续跑: {self.base}；场景: {", ".join(self.suites)}；攻击: {", ".join(self.attacks)}；沿用原生缓存，不自动重试错误。', flush=True)

    def check(self, path, expected):
        """Queue new bindings; keep original existing manifests byte-identical."""
        path = Path(path)
        if path.exists():
            previous = _read(path)
            comparison = previous
            if 'agentdojo_defense' in expected and 'agentdojo_defense' not in previous:
                comparison = dict(previous)
                if previous.get('profile') == 'baseline':
                    evidence = []
                    summary = path.with_name('summary.json')
                    if summary.exists():
                        recorded = _read(summary)
                        if recorded.get('run_manifest') == previous and 'defense' in recorded:
                            evidence.append(recorded['defense']); self.evidence[summary] = summary.read_bytes()
                    screened = self.base / 'screened_run_manifest.json'
                    if screened in self.checked:
                        recorded = _read(screened)
                        if recorded.get('baseline') is True and 'defense' in recorded:
                            evidence.append(recorded['defense'])
                    if not evidence or any(v != expected['agentdojo_defense'] for v in evidence):
                        raise RunConfigurationError('legacy baseline lacks matching explicit native-defense evidence; use its original code or a new name')
                    comparison['agentdojo_defense'] = evidence[0]
                else:
                    comparison['agentdojo_defense'] = None  # This option is unused by the defended factory.
            if previous != expected and not _compatible_binding(comparison, expected):
                raise RunConfigurationError(f'run configuration changed: {path}; use a new --name')
            self.evidence[path] = path.read_bytes()
            if previous != expected:
                self.transitions.append({'path': str(path.relative_to(self.base)),
                                         'original_binding': previous, 'current_binding': expected})
        else:
            if path.name == 'run_manifest.json' and (any(path.parent.rglob('none.json'))
                or any(path.parent.rglob('injection_task_*.json')) or (path.parent / 'summary.json').exists()):
                raise RunConfigurationError(f'unbound historical task cache: {path.parent}')
            previous = expected
            self.pending[path] = expected
        self.checked[path] = expected
        return previous

    def guard(self, path, expected):
        path = Path(path)
        if not self.committed or self.checked.get(path) != expected:
            raise RunConfigurationError('execution differs from validated resume plan')
        return _read(path)

    def commit(self):
        if not self.existing_runs <= self.checked.keys():
            raise RunConfigurationError('existing task bindings fall outside the requested complete run plan')
        if any(p.read_bytes() != h for p, h in self.evidence.items()):
            raise RunConfigurationError('run evidence changed during resume validation')
        identity = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
        destination = self.base / 'reuse' / identity
        destination.mkdir(parents=True)
        aggregate_names = {'attack_manifest.json', 'summary.json', 'summary.md', 'failure_cases.jsonl',
                           'detailed_results.csv', 'report.txt', 'all_report.txt', 'preflight_report.json'}
        snapshots = []
        def snapshot(path):
            target = destination / 'snapshot' / path.relative_to(self.base)
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
            snapshots.append({'path': str(path.relative_to(self.base)), 'size_bytes': target.stat().st_size})
        for path in self.base.rglob('*'):
            if (not path.is_file() or path.is_relative_to(self.base / 'reuse')
                    or path.is_relative_to(self.base / 'validation')): continue
            if path.name not in aggregate_names and not path.name.endswith('_error.txt'): continue
            snapshot(path)
        # The native loader decides what is incomplete. Keep those original
        # bytes (and any trace sidecar) before its normal fallback reruns them.
        for path in self.base.glob('*/*/*/*/*.json'):
            storage, suite, task, attack, filename = path.relative_to(self.base).parts
            if storage == 'reuse' or not task.startswith(('user_task_', 'injection_task_')):
                continue
            try:
                load_task_results(storage, suite, task, attack, Path(filename).stem, self.base)
            except ValidationError:
                snapshot(path)
                sidecar = path.with_suffix('.dscg_trace.jsonl.gz')
                if sidecar.is_file(): snapshot(sidecar)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # Preserve the native error path, including malformed JSON.
        record = {'scope': 'explicit native task-cache resume; errors are not automatically retried',
                  'attacks': self.attacks, 'suites': self.suites, 'transitions': self.transitions,
                  'previous_aggregate_snapshots': snapshots,
                  'verification_mode': 'configuration_only',
                  'source_equivalence_verified': False,
                  'original_evidence_paths': [str(p.relative_to(self.base)) for p in self.evidence]}
        (destination / 'compatibility.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        for path, value in self.pending.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x') as stream:
                stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        self.committed = True
