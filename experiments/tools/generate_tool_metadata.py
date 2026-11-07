"""Generate a validated backend-specific local P0.5 risk catalog."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import Mapping

from dscg import benchmark_catalog

from dscg.tool_metadata import (
    PROJECT_ROOT,
    ToolMetadataError,
    ToolRiskMetadata,
    load_tool_metadata,
)


def registered_tools() -> dict[str, set[str]]:
    """Read the validated active backend's tools without making API calls."""

    try:
        backend = benchmark_catalog.get_backend()
    except benchmark_catalog.BenchmarkConfigurationError as exc:
        raise ToolMetadataError(str(exc)) from exc
    return {
        suite_name: {tool.name for tool in benchmark_catalog.get_suite(backend.suite_version, suite_name).tools}
        for suite_name in backend.suites
    }


def validate_catalog(
    path: str | Path | None = None,
    *,
    suites: Mapping[str, set[str]] | None = None,
) -> dict[str, ToolRiskMetadata]:
    """Reject missing, stale, or malformed classifications before a benchmark."""

    current_suites = registered_tools() if suites is None else suites
    expected = set().union(*current_suites.values())
    source = benchmark_catalog.get_backend().tool_metadata_path if path is None else path
    raw = load_tool_metadata(source)
    missing = sorted(expected - raw.keys())
    extra = sorted(raw.keys() - expected)
    if missing or extra:
        raise ToolMetadataError(
            f"catalog coverage mismatch: missing={missing}; unregistered={extra}"
        )

    validated: dict[str, ToolRiskMetadata] = {}
    for name, fields in raw.items():
        if not isinstance(fields, Mapping):
            raise ToolMetadataError(f"{name}: metadata must be a TOML table")
        try:
            validated[name] = ToolRiskMetadata(**fields)
        except (TypeError, ToolMetadataError) as exc:
            raise ToolMetadataError(f"{name}: {exc}") from exc
    return validated


def generate(output: str | Path | None = None, *, force: bool = False) -> Path:
    """Copy the reviewed catalog only after validating installed suite coverage."""

    try:
        backend = benchmark_catalog.get_backend()
    except benchmark_catalog.BenchmarkConfigurationError as exc:
        raise ToolMetadataError(str(exc)) from exc
    source = Path(backend.tool_metadata_path)
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    validated = validate_catalog(source)
    destination = Path(output).expanduser() if output is not None else PROJECT_ROOT / "config" / f"tools.{backend.id}.local.toml"
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    if destination.resolve() in {
        (PROJECT_ROOT / "config" / f"tools.{name}-v1.2.toml").resolve()
        for name in ("agentdojo", "agentdyn")
    }:
        raise ToolMetadataError("output must differ from the reviewed source catalog")
    if destination.resolve() == (PROJECT_ROOT / "config" / "tools.local.toml").resolve():
        raise ToolMetadataError("generic tools.local.toml is protected; choose a backend-specific output")
    if destination.exists() and not force:
        raise ToolMetadataError(f"output already exists: {destination}; use --force to replace it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    print(f"Generated {destination} with {len(validated)} classified tools")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate active benchmark tools and generate backend-specific P0.5 metadata TOML."
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="destination TOML (default: config/tools.<active-backend>.local.toml)",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    args = parser.parse_args()
    try:
        generate(args.output, force=args.force)
    except ToolMetadataError as exc:
        parser.exit(2, f"Tool metadata error: {exc}\n")


if __name__ == "__main__":
    main()
