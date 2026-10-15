"""Full AgentDojo entry point sharing execution, controls and reports with partial.

Only task scope and the default result root differ. The partial entry retains its
three-task prefix; this entry always selects all registered v1.2 tasks.
"""
from pathlib import Path

from dscg.paths import BENCHMARK_RESULTS_DIR
from experiments import run_partial_benchmark as runner
from experiments.partial_controls import SUITES

# Preserve helpers imported by older local callers.
_safe_result_component = runner._safe_result_component
_apply_run_name = runner._apply_run_name


def main(
    model_id: str | None = None,
    sec_model_id: str | None = None,
    suites=SUITES,
    run_attack: bool = True,
    origin=False,
    defense: str | None = None,
    use_sandbox: bool = True,
    use_security_checker: bool = True,
    **options,
) -> int:
    """Run every task; retain legacy positional arguments and shared keyword controls."""
    if 'task_scope' in options:
        raise ValueError('full benchmark task scope cannot be overridden')
    results_dir = options.pop('results_dir', None)
    return runner.main(
        model_id=model_id, sec_model_id=sec_model_id, suites=list(suites),
        run_attack=run_attack, origin=origin, defense=defense,
        use_sandbox=use_sandbox, use_security_checker=use_security_checker,
        task_scope='full',
        results_dir=Path(results_dir) if results_dir is not None else BENCHMARK_RESULTS_DIR,
        **options,
    )


def cli(argv: list[str] | None = None) -> int:
    return runner.cli(argv, task_scope='full')


if __name__ == '__main__':
    raise SystemExit(cli())
