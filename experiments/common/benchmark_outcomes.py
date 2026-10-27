"""Derived efficacy labels exclude native caught errors; raw traces stay intact."""
from pathlib import Path

from experiments.diagnostics.harness_audit import security_result_fields
from baseintent.task_diagnostics import load_task_trace


def project_outcomes(utility_results, security_results, suite_dir, attack, *, run_attack, task_errors=()):
    root = Path(suite_dir).resolve()
    records = {}
    current_errors = {(e["user_task_id"], e["injection_task_id"] or ""): e for e in task_errors
                      if e["stage"] != "goal_preflight"}
    for key, utility in utility_results.items():
        injection = key[1] if run_attack and len(key) > 1 else None
        trace = root / str(key[0]) / attack / f'{injection or "none"}.json'
        error = False
        termination = None
        if not trace.resolve().is_relative_to(root):
            error = True
        elif trace.exists():
            try:
                raw = load_task_trace(trace)
                error = (not isinstance(raw, dict) or bool(raw.get('error'))
                         or bool(raw.get('baseintent_infrastructure_failure'))
                         or ('baseintent_diagnostics' in raw and raw.get('baseintent_diagnostics_status') != 'complete'))
                termination = raw.get('baseintent_termination') if isinstance(raw,dict) else None
            except (OSError, ValueError):
                error = True
        attack_success, defense_success, status = security_result_fields(security_results, key, run_attack=run_attack)
        records[key] = dict(utility_success=utility if isinstance(utility, bool) else None,
            attack_success=attack_success, defense_success=defense_success, sample_status=status,
            native_utility_success=utility if isinstance(utility, bool) else None,
            native_attack_success=security_results.get(key) if run_attack else None, execution_error=error,
            framework_termination=termination if isinstance(termination,dict) else {})
        if key in current_errors:
            error = True
            records[key].update(execution_error=True)
        if error:
            records[key].update(utility_success=None, attack_success=None, defense_success=None,
                                sample_status='infrastructure_error')
    return records
