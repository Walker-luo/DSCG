"""Typed, bounded records emitted by the harness audit runners.

The compact form is the default interchange format for summaries.  It keeps
identifiers and aggregate outcomes while deliberately omitting prompts,
complete environments, and tool arguments.  The full form is an explicit
trace opt-in and applies the same size bounds to its additional details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping


_MAX_TEXT_LENGTH = 256
_MAX_KEY_LENGTH = 64
_MAX_ITEMS = 32
_MAX_DEPTH = 4
_MAX_INTEGER = 1_000_000

_SENSITIVE_FINAL_STATE_KEYS = {
    "arguments",
    "complete_environment",
    "environment",
    "env",
    "message",
    "messages",
    "payload",
    "prompt",
    "raw_prompt",
    "tool_args",
    "tool_arguments",
}


class SampleStatus(str, Enum):
    VALID = "valid"
    MODEL_ERROR = "model_error"
    POLICY_ERROR = "policy_error"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    SKIPPED = "skipped"


def _bounded_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:_MAX_TEXT_LENGTH]


def _bounded_scalar(value: Any) -> Any:
    """Keep JSON-like scalar values finite and within a predictable size."""

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return max(-_MAX_INTEGER, min(_MAX_INTEGER, value))
    if isinstance(value, float):
        return value if isfinite(value) else None
    return _bounded_text(value)


def _is_sensitive_final_state_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _SENSITIVE_FINAL_STATE_KEYS or any(
        token in normalized for token in ("prompt", "message", "environment")
    )


def _bounded(
    value: Any,
    *,
    depth: int = 0,
    drop_sensitive_keys: bool = False,
) -> Any:
    """Recursively bound an arbitrary trace value.

    ``drop_sensitive_keys`` is used only for the compact final-state summary;
    the full serializer never computes hashes and simply bounds caller-supplied
    trace details.
    """

    if depth >= _MAX_DEPTH:
        if isinstance(value, (Mapping, list, tuple)):
            return "[truncated]"
        return _bounded_scalar(value)
    if value is None or isinstance(value, (bool, int, float)):
        return _bounded_scalar(value)
    if isinstance(value, str):
        return value[:_MAX_TEXT_LENGTH]
    if isinstance(value, Mapping):
        bounded: dict[str, Any] = {}
        for raw_key, raw_value in list(value.items())[:_MAX_ITEMS]:
            key = str(raw_key)[:_MAX_KEY_LENGTH]
            normalized_key = key.lower().replace("-", "_")
            if drop_sensitive_keys and _is_sensitive_final_state_key(normalized_key):
                continue
            bounded[key] = _bounded(
                raw_value,
                depth=depth + 1,
                drop_sensitive_keys=drop_sensitive_keys,
            )
        return bounded
    if isinstance(value, (list, tuple)):
        return [
            _bounded(
                item,
                depth=depth + 1,
                drop_sensitive_keys=drop_sensitive_keys,
            )
            for item in list(value)[:_MAX_ITEMS]
        ]
    return _bounded_text(value)


def _bounded_action_counts(value: Mapping[str, int] | None) -> dict[str, int]:
    if not isinstance(value, Mapping):
        return {}
    counts: dict[str, int] = {}
    for raw_key, raw_value in list(value.items())[:_MAX_ITEMS]:
        key = str(raw_key)[:_MAX_KEY_LENGTH]
        try:
            count = int(raw_value)
        except (TypeError, ValueError, OverflowError):
            count = 0
        counts[key] = max(0, min(_MAX_INTEGER, count))
    return counts


def _bounded_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    return None


@dataclass(frozen=True)
class SampleRecord:
    run_id: str
    suite_name: str
    task_id: str
    sample_status: SampleStatus | str = SampleStatus.VALID
    error_type: str | None = None
    payload_delivered: bool | None = None
    payload_hash: str | None = None
    predicate_result: bool | None = None
    utility_result: bool | None = None
    action_counts: Mapping[str, int] = field(default_factory=dict)
    final_state: Mapping[str, Any] = field(default_factory=dict)
    payload: Any = None
    candidate_details: Any = None
    action_details: Any = None

    def __post_init__(self) -> None:
        try:
            status = SampleStatus(self.sample_status)
        except ValueError as exc:
            raise ValueError(f"unknown sample status: {self.sample_status!r}") from exc
        object.__setattr__(self, "sample_status", status)

    def compact_dict(self) -> dict[str, Any]:
        return {
            "run_id": _bounded_text(self.run_id),
            "suite_name": _bounded_text(self.suite_name),
            "task_id": _bounded_text(self.task_id),
            "sample_status": self.sample_status.value,
            "error_type": _bounded_text(self.error_type),
            "payload_delivered": _bounded_bool(self.payload_delivered),
            "payload_hash": _bounded_text(self.payload_hash),
            "predicate_result": _bounded_bool(self.predicate_result),
            "utility_result": _bounded_bool(self.utility_result),
            "action_counts": _bounded_action_counts(self.action_counts),
            "final_state": _bounded(self.final_state, drop_sensitive_keys=True),
        }

    def full_dict(self) -> dict[str, Any]:
        record = self.compact_dict()
        record.update({
            "payload": _bounded(self.payload),
            "candidate_details": _bounded(self.candidate_details),
            "action_details": _bounded(self.action_details),
        })
        return record


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    records: list[SampleRecord] = field(default_factory=list)
    seed: int | str | None = None

    def compact_dict(self) -> dict[str, Any]:
        counts = {status.value: 0 for status in SampleStatus}
        for record in self.records:
            counts[record.sample_status.value] += 1
        return {
            "run_id": _bounded_text(self.run_id),
            "seed": _bounded(self.seed),
            "sample_counts": counts,
            "records": [record.compact_dict() for record in self.records],
        }

    def full_dict(self) -> dict[str, Any]:
        result = self.compact_dict()
        result["records"] = [record.full_dict() for record in self.records]
        return result
