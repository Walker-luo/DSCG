"""Generate a validated local P0.5 catalog for AgentDojo v1.2."""

from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path
import shutil
from typing import Mapping

from agentdojo.task_suite import get_suite

from dscg.tool_metadata import (
    PROJECT_ROOT,
    ToolMetadataError,
    ToolRiskMetadata,
    load_tool_metadata,
)


SUITE_NAMES = ("workspace", "travel", "banking", "slack")
AGENTDOJO_PACKAGE_VERSION = "0.1.35"
CATALOG_PATH = PROJECT_ROOT / "config" / "tools.agentdojo-v1.2.toml"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "config" / "tools.local.toml"


def registered_tools() -> dict[str, set[str]]:
    """Read the installed AgentDojo suite registry, without making API calls."""

    installed_version = version("agentdojo")
    if installed_version != AGENTDOJO_PACKAGE_VERSION:
        raise ToolMetadataError(
            f"expected agentdojo {AGENTDOJO_PACKAGE_VERSION}, found {installed_version}; "
            "review the catalog before using a different package version"
        )
    return {
        suite_name: {tool.name for tool in get_suite("v1.2", suite_name).tools}
        for suite_name in SUITE_NAMES
    }


def validate_catalog(
    path: str | Path = CATALOG_PATH,
    *,
    suites: Mapping[str, set[str]] | None = None,
) -> dict[str, ToolRiskMetadata]:
    """Reject missing, stale, or malformed classifications before a benchmark."""

    current_suites = registered_tools() if suites is None else suites
    expected = set().union(*current_suites.values())
    raw = load_tool_metadata(path)
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


def generate(output: str | Path = DEFAULT_OUTPUT_PATH, *, force: bool = False) -> Path:
    """Copy the reviewed catalog only after validating installed suite coverage."""

    validated = validate_catalog()
    destination = Path(output).expanduser()
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    if destination.resolve() == CATALOG_PATH.resolve():
        raise ToolMetadataError("output must differ from the reviewed source catalog")
    if destination.exists() and not force:
        raise ToolMetadataError(f"output already exists: {destination}; use --force to replace it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CATALOG_PATH, destination)
    print(f"Generated {destination} with {len(validated)} classified tools")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate AgentDojo v1.2 tools and generate a local P0.5 metadata TOML."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        metavar="PATH",
        help="destination TOML (default: config/tools.local.toml)",
    )
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    args = parser.parse_args()
    try:
        generate(args.output, force=args.force)
    except ToolMetadataError as exc:
        parser.exit(2, f"Tool metadata error: {exc}\n")


if __name__ == "__main__":
    main()
