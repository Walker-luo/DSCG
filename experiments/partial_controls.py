"""Matched partial-run controls, frozen IDs and cache configuration binding."""
import hashlib
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path
from agentdojo.task_suite import get_suite

SUITES=('workspace','travel','banking','slack')


def validate_controls(*, origin=False,use_security_checker=True,audit_retries=0,completion_prompt=False):
    if origin and (not use_security_checker or audit_retries or completion_prompt):
        raise ValueError('native baseline cannot use DSCG ablation options')
    if audit_retries not in (0,1) or (not use_security_checker and audit_retries):
        raise ValueError('audit retries require checker and must be 0 or 1')


def make_task_manifest():
    return {'schema_version':'dscg.partial-tasks.v1','suite_version':'v1.2','seed':7,
            'selection_rule':'registration-order-prefix (seed is metadata, not API determinism)',
            'suites':{name:{'user_task_ids':list(get_suite('v1.2',name).user_tasks)[:3],
                            'injection_task_ids':list(get_suite('v1.2',name).injection_tasks)[:3]} for name in SUITES}}


def load_task_manifest(path):
    if path is None:return None
    result=json.loads(Path(path).read_text())
    if not isinstance(result,dict) or result.get('suite_version')!='v1.2' or not isinstance(result.get('suites'),dict):
        raise ValueError('invalid v1.2 task manifest')
    return result


def select_tasks(manifest,suite_name,users,injections,run_attack,is_dos):
    if manifest is None:return users[:3],injections[:1 if is_dos else 3] if run_attack else []
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
    if is_dos and selected_injections!=injections[:1]:
        raise ValueError('AgentDojo DoS uses first injection ID; supply a separate matching manifest')
    return selected_users,selected_injections


def guard_run(path,manifest):
    path=Path(path)
    if path.exists():
        if json.loads(path.read_text())!=manifest:
            raise ValueError('run configuration changed; use a new --name (old results preserved)')
        return
    # Historical traces without a binding cannot be certified as a matching cache.
    if path.parent.exists() and ((path.parent/'summary.json').exists() or any(path.parent.rglob('injection_task_*.json')) or any(path.parent.rglob('none.json'))):
        raise ValueError('unbound historical cache; use a new --name')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


def source_revision():
    root=Path(__file__).resolve().parents[1]
    paths=sorted((root/'dscg').rglob('*.py'))+[Path(__file__),root/'experiments/run_partial_benchmark.py']
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    except (OSError,subprocess.CalledProcessError):commit=None
    return {'commit':commit,'source_sha256':hashes,'python':platform.python_version(),'agentdojo':version('agentdojo')}


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
