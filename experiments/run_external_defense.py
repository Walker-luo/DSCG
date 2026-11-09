"""Thin entry for AgentDojo built-in defense comparison arms.

Runs the native AgentDojo loop with one of the benchmark-provided defenses as
an independent comparison arm. It only forwards configuration to the shared
runner; it never changes the GrantBind default path or framework behavior.
"""
import argparse
import os

from dscg.paths import RESULTS_DIR
from experiments import run_partial_benchmark as benchmark_runner

DEFENSES = ("spotlighting_with_delimiting", "tool_filter")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Run an AgentDojo built-in defense arm (native loop) on the recorded comparison grid."
    )
    parser.add_argument("--defense", required=True, choices=DEFENSES)
    parser.add_argument("--suites", nargs="+", metavar="SUITE", default=None)
    parser.add_argument("--attack", nargs="+", action="extend", default=None,
                        help="默认 typical（3 种目标型攻击）；clean 模式忽略该参数。")
    parser.add_argument("--clean", action="store_true",
                        help="运行无攻击效用对照（忽略 --fliter/--attack）。")
    parser.add_argument("--fliter", dest="fliter_path", metavar="PATH")
    parser.add_argument("--task-manifest", dest="task_manifest_path", metavar="PATH")
    parser.add_argument("--name", dest="run_name", required=True, metavar="NAME")
    parser.add_argument("--results-dir", metavar="DIR",
                        default=os.path.join(str(RESULTS_DIR), "workshop"))
    parser.add_argument("--model-config", dest="config_path", metavar="PATH")
    parser.add_argument("--progress", action="store_true")
    policy = parser.add_mutually_exclusive_group()
    policy.add_argument("--reuse", action="store_true")
    policy.add_argument("--force-rerun", action="store_true")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.clean and (args.fliter_path or args.attack):
        parser.error("--clean cannot be combined with --fliter/--attack")
    return benchmark_runner.main(
        suites=args.suites,
        run_attack=not args.clean,
        origin=True,
        defense=args.defense,
        fliter_path=None if args.clean else args.fliter_path,
        reuse=args.reuse,
        progress=args.progress,
        run_name=args.run_name,
        results_dir=args.results_dir,
        task_manifest_path=args.task_manifest_path,
        attack=None if args.clean else args.attack,
        audit_router_mode="off",
        config_path=args.config_path,
        force_rerun=args.force_rerun,
        task_scope="partial",
    )


if __name__ == "__main__":
    raise SystemExit(main())
