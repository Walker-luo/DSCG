"""Full benchmark entry point sharing execution, controls and reports with partial.

Defaults select all current backend suites; --suites selects complete suite catalogues.
Explicit --cohort retains all users in selected suites and frozen kept targets.
"""
from pathlib import Path

from dscg.paths import BENCHMARK_RESULTS_DIR
from experiments import run_partial_benchmark as runner
from dscg.benchmark_catalog import get_suites

# Preserve helpers imported by older local callers.
_safe_result_component = runner._safe_result_component
_apply_run_name = runner._apply_run_name


def main(
    model_id: str | None = None,
    sec_model_id: str | None = None,
    suites=None,
    run_attack: bool = True,
    origin=False,
    defense: str | None = None,
    use_sandbox: bool = True,
    use_security_checker: bool = True,
    cohort_path: str | Path | None = None,
    reuse: bool = False,
    progress: bool = False,
    **options,
) -> int:
    """Run all tasks within selected suites, retaining shared controls and defaults."""
    if 'task_scope' in options:
        raise ValueError('full benchmark task scope cannot be overridden')
    suites = list(get_suites()) if suites is None and not reuse else suites
    if cohort_path is not None:
        if not run_attack or options.get('task_manifest_path'):
            raise ValueError('--cohort cannot be combined with clean or another task manifest')
        options.pop('task_manifest_path', None)
        from experiments.common.injection_cohort import run_screened
        return run_screened(cohort_path, model_id=model_id, sec_model_id=sec_model_id,
                            origin=origin, defense=defense, use_sandbox=use_sandbox,
                            use_security_checker=use_security_checker, suites=suites, reuse=reuse,
                            progress=progress, **options)
    results_dir = options.pop('results_dir', None)
    return runner.main(
        model_id=model_id, sec_model_id=sec_model_id, suites=suites,
        run_attack=run_attack, origin=origin, defense=defense,
        use_sandbox=use_sandbox, use_security_checker=use_security_checker,
        task_scope='full',
        reuse=reuse,
        progress=progress,
        results_dir=results_dir if results_dir is not None else BENCHMARK_RESULTS_DIR,
        **options,
    )


def cli(argv: list[str] | None = None, *, require_cohort=False) -> int:
    return runner.cli(argv, task_scope='full', entrypoint=main, require_cohort=require_cohort)


if __name__ == '__main__':
    raise SystemExit(cli())
