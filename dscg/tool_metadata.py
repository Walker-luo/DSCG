"""Explicit risk metadata for tools crossing the DSCG execution boundary.

The registry is attached to a trusted ``FunctionsRuntime`` by the host.  Tool
names and docstrings are never used to infer effects.  Missing metadata is
represented as an invalid high-risk entry so callers can fail closed without
silently treating an unclassified tool as a read-only operation.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping
from pathlib import Path
import os


TOOL_METADATA_SCHEMA_VERSION = "dscg.tool-risk.v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOOL_METADATA_PATH = PROJECT_ROOT / "config" / "tools.local.toml"
EFFECTS = frozenset({"read", "write", "delete", "financial", "external_send"})
SOURCES = frozenset({"calendar", "email", "cloud", "web", "local"})
SINKS = frozenset({"none", "external_recipient", "public_output"})
SENSITIVITIES = frozenset({"public", "internal", "personal", "secret"})
_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class ToolMetadataError(ValueError):
    """Raised when explicit tool metadata does not match the schema."""


def load_tool_metadata(
    config_path: str | os.PathLike[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Mapping[str, Any]]:
    """Load ``[tools.<name>]`` metadata from an optional local TOML file."""

    environ = os.environ if env is None else env
    configured = config_path or environ.get("DSCG_TOOL_METADATA")
    path = Path(configured).expanduser() if configured else DEFAULT_TOOL_METADATA_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        if configured:
            raise ToolMetadataError(f"tool metadata file does not exist: {path}")
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except Exception as exc:
        raise ToolMetadataError(f"failed to load tool metadata {path}: {exc}") from exc
    tools = document.get("tools") if isinstance(document, Mapping) else None
    if not isinstance(tools, Mapping):
        raise ToolMetadataError(f"tool metadata {path} must contain a [tools] table")
    return {str(name): value for name, value in tools.items()}


@dataclass(frozen=True)
class ToolRiskMetadata:
    effect: str
    source: str
    sink: str
    sensitivity: str
    idempotent: bool
    reversible: bool
    schema_version: str = TOOL_METADATA_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != TOOL_METADATA_SCHEMA_VERSION:
            raise ToolMetadataError(
                f"unsupported tool metadata schema: {self.schema_version!r}"
            )
        for field, allowed in (
            ("effect", EFFECTS),
            ("source", SOURCES),
            ("sink", SINKS),
            ("sensitivity", SENSITIVITIES),
        ):
            value = getattr(self, field)
            if value not in allowed:
                raise ToolMetadataError(
                    f"invalid {field}={value!r}; expected one of {sorted(allowed)}"
                )
        if not isinstance(self.idempotent, bool) or not isinstance(self.reversible, bool):
            raise ToolMetadataError("idempotent and reversible must be booleans")
        if self.effect == "external_send" and self.sink == "none":
            raise ToolMetadataError("external_send requires a non-none sink")
        if self.effect == "delete" and self.reversible:
            raise ToolMetadataError("delete actions cannot be marked reversible")

    @property
    def risk_level(self) -> str:
        if self.effect in {"financial", "external_send"}:
            return "critical"
        # A sink is an explicit data-flow destination.  Even a read operation
        # becomes high risk when it can publish data or address an external
        # recipient; the deterministic read fast path must never treat that
        # metadata as a harmless lookup.
        if self.sink == "external_recipient":
            return "critical"
        if self.sink == "public_output":
            return "high"
        if self.effect == "delete" or self.sensitivity in {"personal", "secret"}:
            return "high"
        if self.effect == "write":
            return "medium"
        return "low"

    @property
    def deterministic_read(self) -> bool:
        """Whether the tool may use the no-LLM public-read fast path."""

        return (
            self.effect == "read"
            and self.sensitivity == "public"
            and self.sink == "none"
            and self.risk_level == "low"
        )

    @property
    def confirmation_required(self) -> bool:
        return self.effect in {"write", "delete", "financial", "external_send"} or self.risk_level in {
            "high",
            "critical",
        }

    @property
    def audit_required(self) -> bool:
        return self.risk_level != "low" or self.sensitivity != "public"

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "effect": self.effect,
            "source": self.source,
            "sink": self.sink,
            "sensitivity": self.sensitivity,
            "idempotent": self.idempotent,
            "reversible": self.reversible,
            "risk_level": self.risk_level,
            "deterministic_read": self.deterministic_read,
            "confirmation_required": self.confirmation_required,
            "audit_required": self.audit_required,
        }


@dataclass(frozen=True)
class ToolMetadataStatus:
    """Validated view of one runtime tool's classification."""

    tool_name: str
    metadata: ToolRiskMetadata | None
    error_code: str | None = None
    error_detail: str | None = None

    @property
    def registered(self) -> bool:
        return self.metadata is not None and self.error_code is None

    @property
    def risk_level(self) -> str:
        return self.metadata.risk_level if self.metadata else "critical"

    @property
    def confirmation_required(self) -> bool:
        return self.metadata.confirmation_required if self.metadata else True

    @property
    def audit_required(self) -> bool:
        return self.metadata.audit_required if self.metadata else True

    def public_dict(self) -> dict[str, Any]:
        if self.metadata is None:
            return {
                "tool_name": self.tool_name,
                "metadata_state": "missing_or_invalid",
                "error_code": self.error_code or "METADATA_MISSING",
                "risk_level": "critical",
                "deterministic_read": False,
                "confirmation_required": True,
                "audit_required": True,
            }
        return {
            "tool_name": self.tool_name,
            "metadata_state": "valid",
            **self.metadata.public_dict(),
        }


def _coerce_metadata(value: ToolRiskMetadata | Mapping[str, Any]) -> ToolRiskMetadata:
    if isinstance(value, ToolRiskMetadata):
        return value
    if not isinstance(value, Mapping):
        raise ToolMetadataError("tool metadata must be a mapping or ToolRiskMetadata")
    required = {
        "effect",
        "source",
        "sink",
        "sensitivity",
        "idempotent",
        "reversible",
    }
    unknown = set(value) - required - {"schema_version"}
    missing = required - set(value)
    if unknown:
        raise ToolMetadataError(f"unknown metadata fields: {sorted(unknown)}")
    if missing:
        raise ToolMetadataError(f"missing metadata fields: {sorted(missing)}")
    return ToolRiskMetadata(**{key: value[key] for key in set(value) & (required | {"schema_version"})})


def set_tool_metadata(runtime: Any, metadata: Mapping[str, ToolRiskMetadata | Mapping[str, Any]]) -> None:
    """Attach a validated metadata catalog to a trusted FunctionsRuntime."""

    functions = getattr(runtime, "functions", None)
    if not isinstance(functions, Mapping):
        raise ToolMetadataError("runtime must expose a functions mapping")
    catalog: dict[str, ToolRiskMetadata] = {}
    for tool_name, value in metadata.items():
        if tool_name not in functions:
            raise ToolMetadataError(f"metadata references unregistered tool: {tool_name}")
        catalog[str(tool_name)] = _coerce_metadata(value)
    runtime._dscg_tool_metadata = catalog


def register_tool_metadata(runtime: Any, tool_name: str, metadata: ToolRiskMetadata | Mapping[str, Any]) -> None:
    """Register one tool after the runtime function has been installed."""

    existing = dict(getattr(runtime, "_dscg_tool_metadata", {}))
    existing[tool_name] = _coerce_metadata(metadata)
    set_tool_metadata(runtime, existing)


def metadata_for_runtime(runtime: Any) -> dict[str, ToolMetadataStatus]:
    """Validate a complete runtime catalog; omissions become critical entries."""

    functions = getattr(runtime, "functions", {})
    raw_catalog = getattr(runtime, "_dscg_tool_metadata", {})
    if not isinstance(raw_catalog, Mapping):
        raw_catalog = {}
    statuses: dict[str, ToolMetadataStatus] = {}
    for tool_name in functions:
        value = raw_catalog.get(tool_name)
        if value is None:
            statuses[tool_name] = ToolMetadataStatus(
                str(tool_name), None, "METADATA_MISSING", "no explicit metadata registered"
            )
            continue
        try:
            statuses[tool_name] = ToolMetadataStatus(str(tool_name), _coerce_metadata(value))
        except ToolMetadataError as exc:
            statuses[tool_name] = ToolMetadataStatus(
                str(tool_name), None, "METADATA_INVALID", str(exc)
            )
    return statuses


def metadata_catalog_hash(statuses: Mapping[str, ToolMetadataStatus]) -> str:
    payload = {
        name: status.public_dict()
        for name, status in sorted(statuses.items())
    }
    return sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def risk_counts(statuses: Mapping[str, ToolMetadataStatus]) -> dict[str, int]:
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for status in statuses.values():
        counts[status.risk_level] += 1
    return counts


def highest_risk(statuses: Mapping[str, ToolMetadataStatus], tool_names: list[str]) -> str:
    level = "low"
    for name in tool_names:
        candidate = statuses.get(name)
        candidate_level = candidate.risk_level if candidate else "critical"
        if _RISK_ORDER[candidate_level] > _RISK_ORDER[level]:
            level = candidate_level
    return level
