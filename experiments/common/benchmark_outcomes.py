"""Derived efficacy labels exclude native caught errors; raw traces stay intact."""
import json
from pathlib import Path

from experiments.diagnostics.harness_audit import security_result_fields


def project_outcomes(utility_results, security_results, suite_dir, attack, *, run_attack):
    root = Path(suite_dir).resolve()
    records = {}
    for key, utility in utility_results.items():
        injection = key[1] if run_attack and len(key) > 1 else None
        trace = root / str(key[0]) / attack / f'{injection or "none"}.json'
        error = False
        if not trace.resolve().is_relative_to(root):
            error = True
        elif trace.exists():
            try:
                raw = json.loads(trace.read_text(encoding='utf-8'))
                error = not isinstance(raw, dict) or bool(raw.get('error'))
            except (OSError, ValueError):
                error = True
        attack_success, defense_success, status = security_result_fields(security_results, key, run_attack=run_attack)
        records[key] = dict(utility_success=utility if isinstance(utility, bool) else None,
            attack_success=attack_success, defense_success=defense_success, sample_status=status,
            native_utility_success=utility if isinstance(utility, bool) else None,
            native_attack_success=security_results.get(key) if run_attack else None, execution_error=error)
        if error:
            records[key].update(utility_success=None, attack_success=None, defense_success=None,
                                sample_status='infrastructure_error')
    return records
