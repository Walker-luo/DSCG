"""Matched benchmark controls, explicit task scopes and cache configuration binding."""
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path
from dscg.benchmark_catalog import get_backend, get_suites, SUITE_VERSION, get_suite, benchmark_identity


class RunConfigurationError(ValueError):
    """A rejected cache binding must never rewrite the previous run reports."""


def validate_controls(*, origin=False,use_security_checker=True,audit_retries=0,completion_prompt=False):
    if origin and (not use_security_checker or audit_retries or completion_prompt):
        raise ValueError('native baseline cannot use DSCG ablation options')
    if audit_retries not in (0,1) or (not use_security_checker and audit_retries):
        raise ValueError('audit retries require checker and must be 0 or 1')


def make_task_manifest(task_scope='partial'):
    if task_scope not in {'partial', 'full'}:
        raise ValueError('task scope must be partial or full')
    identity = benchmark_identity()
    if task_scope == 'full':
        return {'schema_version': 'dscg.full-tasks.v2', 'benchmark': identity, 'suite_version': SUITE_VERSION, 'seed': None,
                'selection_rule': 'all-registered-tasks (DoS uses first injection per user)',
                'suites': {name: {'user_task_ids': list(get_suite('v1.2', name).user_tasks),
                                  'injection_task_ids': list(get_suite('v1.2', name).injection_tasks)} for name in get_suites()}}
    return {'schema_version':'dscg.partial-tasks.v2','benchmark': identity,'suite_version':SUITE_VERSION,'seed':7,
            'selection_rule':'registration-order-prefix (seed is metadata, not API determinism)',
            'suites':{name:{'user_task_ids':list(get_suite('v1.2',name).user_tasks)[:3],
                            'injection_task_ids':list(get_suite('v1.2',name).injection_tasks)[:3]} for name in get_suites()}}


def load_task_manifest(path):
    if path is None:return None
    result=json.loads(Path(path).read_text())
    if not isinstance(result,dict) or result.get('suite_version')!='v1.2' or not isinstance(result.get('suites'),dict):
        raise ValueError('invalid v1.2 task manifest')
    if result.get('benchmark') != benchmark_identity() or result.get('schema_version') not in {
            'dscg.partial-tasks.v2', 'dscg.full-tasks.v2', 'dscg.injection-screen.v2'}:
        raise ValueError('task manifest benchmark identity/protocol differs; export a new manifest for the current backend')
    return result


def select_tasks(manifest,suite_name,users,injections,run_attack,is_dos,*,task_scope='partial'):
    if task_scope not in {'partial', 'full', 'screened', 'partial_screened'}:
        raise ValueError('unknown task scope')
    if task_scope in {'screened', 'partial_screened'} and (manifest is None or not run_attack or is_dos):
        raise ValueError('screened measurements require a frozen targeted-attack cohort')
    if manifest is None:
        selected_users = list(users) if task_scope == 'full' else users[:3]
        selected_injections = injections[:1] if is_dos else list(injections) if task_scope == 'full' else injections[:3]
        return selected_users, selected_injections if run_attack else []
    if manifest.get('benchmark') != benchmark_identity():
        raise ValueError('frozen manifest benchmark identity differs')
    if manifest.get('suite_version')!='v1.2' or suite_name not in manifest.get('suites',{}):
        raise ValueError('frozen manifest lacks current v1.2 suite')
    entry=manifest['suites'][suite_name]
    def check(key,catalog):
        ids=entry.get(key)
        if not isinstance(ids,list) or not ids or not all(isinstance(x,str) for x in ids) or len(set(ids))!=len(ids) or not set(ids)<=set(catalog):
            raise ValueError(f'invalid frozen {key} for {suite_name}')
        return list(ids)
    selected_users=check('user_task_ids',users)
    selected_injections=check('injection_task_ids',injections) if run_attack else []
    if task_scope == 'full':
        if selected_users != list(users) or (run_attack and selected_injections != list(injections)):
            raise ValueError('full benchmark requires all registered task IDs in registration order; partial manifests cannot reduce it')
        return selected_users, selected_injections[:1] if is_dos and run_attack else selected_injections
    if task_scope in {'screened', 'partial_screened'}:
        if (manifest.get('schema_version') != 'dscg.injection-screen.v2' or not manifest.get('cohort_sha256')
                or selected_users != list(users)
                or selected_injections != [i for i in injections if i in selected_injections]):
            raise ValueError('screened cohort must retain all user tasks and registered injection order')
        if task_scope == 'partial_screened':
            # Filter the existing prefix; do not backfill with later easy goals.
            return list(users[:3]), [i for i in injections[:3] if i in selected_injections]
    if is_dos and selected_injections!=injections[:1]:
        raise ValueError('AgentDojo DoS uses first injection ID; supply a separate matching manifest')
    return selected_users,selected_injections


def guard_run(path,manifest):
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text())!=manifest:
            raise RunConfigurationError('run configuration changed; use a new --name (old results preserved)')
        return
    # Historical traces without a binding cannot be certified as a matching cache.
    if path.parent.exists() and ((path.parent/'summary.json').exists() or any(path.parent.rglob('injection_task_*.json')) or any(path.parent.rglob('none.json'))):
        raise ValueError('unbound historical cache; use a new --name')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


def source_revision():
    root=Path(__file__).resolve().parents[2]
    paths=sorted((root/'dscg').rglob('*.py'))+[Path(__file__),root/'experiments/run_partial_benchmark.py',root/'experiments/run_benchmark.py']
    paths += [root / 'experiments' / name for name in (
        'run_injection_precheck.py', 'common/injection_cohort.py', 'common/injection_cohort_compatibility.json',
        'common/benchmark_reuse.py', 'common/benchmark_reuse_compatibility.json',
        'common/partial_reporting.py', 'common/benchmark_outcomes.py', 'common/benchmark_execution.py', 'diagnostics/harness_audit.py')
        if (root / 'experiments' / name).exists()]
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit=None
    return {'commit':commit,'source_sha256':hashes,'python':platform.python_version(),'agentdojo':version('agentdojo'), 'benchmark':benchmark_identity()}


def preserve_cached_cost(summary,path,force_rerun):
    """Do not replace recorded costs with zero when all tasks used native cache.

    Mixed cache executions describe only new API calls. They cannot establish a
    cohort cost; matched cost comparisons should use force-rerun in fresh names.
    """
    from copy import deepcopy
    fields=('overhead','sec_overhead','api_accounting')
    summary['invocation_cost']={k:deepcopy(summary[k]) for k in fields if k in summary}
    summary['cost_scope']='new_api_calls_this_invocation'
    summary['cost_comparison_ready']=bool(force_rerun)
    calls=sum(phase.get('api_calls',0) for model in summary.get('api_accounting',{}).values() for phase in model.values())
    if force_rerun or calls or summary.get('overhead',{}).get('total_tokens',0) or summary.get('sec_overhead',{}).get('total_tokens',0) or not Path(path).exists():return
    previous=json.loads(Path(path).read_text())
    for field in fields:
        if field in previous:summary[field]=deepcopy(previous[field])
    summary['cost_scope']='retained_previous_invocation'
    summary['cost_comparison_ready']=previous.get('cost_comparison_ready',False)
