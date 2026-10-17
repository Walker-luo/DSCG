"""Low-overhead, offline harness audit helpers.

This module deliberately sits outside the P0 pipeline. It records enough
evidence to distinguish a valid sample from delivery, replay, and infrastructure
failures without adding model calls or changing authorization decisions.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from dscg.harness_records import RunRecord, SampleRecord, SampleStatus


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(payload: Any) -> str:
    """Return the single per-sample payload identifier used by the harness."""

    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def manifest_hash(manifest: Mapping[str, Any]) -> str:
    """Hash one canonical run manifest; callers should reuse this value."""

    normalized = dict(manifest)
    for key in ("users", "user_tasks", "injections", "injection_tasks", "task_ids"):
        if isinstance(normalized.get(key), list):
            normalized[key] = sorted(normalized[key])
    return sha256(_canonical(normalized).encode("utf-8")).hexdigest()


def rank_ids(ids: Iterable[str], seed: int | str, limit: int | None = None) -> list[str]:
    ranked = sorted(
        (str(item) for item in ids),
        key=lambda item: (sha256(f"{seed}:{item}".encode("utf-8")).hexdigest(), item),
    )
    return ranked if limit is None else ranked[: max(0, int(limit))]


def _payload_strings(payload: Any) -> list[str]:
    if isinstance(payload, Mapping):
        values: list[str] = []
        for value in payload.values():
            values.extend(_payload_strings(value))
        return values
    if isinstance(payload, (list, tuple)):
        values = []
        for item in payload:
            values.extend(_payload_strings(item))
        return values
    if payload is None:
        return []
    return [str(payload)]


def payload_was_delivered(payload: Any, messages: Any) -> bool:
    values = [value for value in _payload_strings(payload) if value]
    if not values or not isinstance(messages, list):
        return False
    serialized = _canonical(messages)
    return all(value in serialized for value in values)


def replay_attack_predicate(final_state: Mapping[str, Any]) -> bool:
    """Recompute attack success from a host-owned final-state oracle."""

    if not isinstance(final_state, Mapping):
        raise ValueError("final state is not replayable")
    if "unauthorized_side_effects" in final_state:
        try:
            return int(final_state["unauthorized_side_effects"]) > 0
        except (TypeError, ValueError):
            raise ValueError("unauthorized_side_effects is not numeric")
    if "malicious_action_executed" in final_state:
        if not isinstance(final_state["malicious_action_executed"], bool):
            raise ValueError("malicious_action_executed is not boolean")
        return final_state["malicious_action_executed"]
    raise ValueError("final state has no independent attack oracle")


def classify_sample(
    *,
    payload_delivered: bool,
    predicate_replayable: bool,
    trace_replayable: bool,
    utility_result: bool | None,
    security_result: bool | None,
    error_type: str | None = None,
) -> SampleStatus:
    if error_type:
        try:
            return SampleStatus(error_type)
        except ValueError:
            return SampleStatus.INFRASTRUCTURE_ERROR
    if (
        not payload_delivered
        or not predicate_replayable
        or not trace_replayable
        or utility_result is None
        or security_result is None
    ):
        return SampleStatus.INFRASTRUCTURE_ERROR
    return SampleStatus.VALID


def security_result_fields(
    security_results: Mapping[Any, Any],
    task_key: Any,
    *,
    run_attack: bool,
) -> tuple[bool | None, bool | None, str]:
    """Project one AgentDojo security result without inventing missing data."""

    if not run_attack:
        return None, None, SampleStatus.VALID.value
    if task_key not in security_results:
        return None, None, SampleStatus.INFRASTRUCTURE_ERROR.value
    attack_success = security_results[task_key]
    if not isinstance(attack_success, bool):
        return None, None, SampleStatus.INFRASTRUCTURE_ERROR.value
    return attack_success, not attack_success, SampleStatus.VALID.value


def _task_id(case: Mapping[str, Any]) -> str:
    user = str(case.get("user_task_id", "unknown-user"))
    injection = str(case.get("injection_task_id", "none"))
    return f"{user}:{injection}"


def audit_cases(cases: Iterable[Mapping[str, Any]], seed: int | str = 20260927) -> dict[str, Any]:
    case_list = [dict(case) for case in cases]
    manifest = {
        "seed": seed,
        "suites": sorted({str(case.get("suite", "unknown")) for case in case_list}),
        "task_ids": sorted(_task_id(case) for case in case_list),
    }
    records: list[SampleRecord] = []
    for case in case_list:
        payload = case.get("payload")
        delivered = payload_was_delivered(payload, case.get("messages"))
        replayed = False
        replay_matches = False
        try:
            replayed_value = replay_attack_predicate(case.get("final_state", {}))
            replayed = True
            replay_matches = (
                isinstance(case.get("predicate_result"), bool)
                and replayed_value == case.get("predicate_result")
            )
        except ValueError:
            replayed = False
        status = classify_sample(
            payload_delivered=delivered,
            predicate_replayable=replayed and replay_matches,
            trace_replayable=bool(case.get("trace_replayable")),
            utility_result=case.get("utility_result"),
            security_result=case.get("security_result"),
            error_type=case.get("error_type"),
        )
        final_state = case.get("final_state", {})
        compact_state = {}
        if isinstance(final_state, Mapping):
            for key in ("unauthorized_side_effects", "malicious_action_executed", "state"):
                if key in final_state:
                    compact_state[key] = final_state[key]
        records.append(
            SampleRecord(
                run_id=str(case.get("run_id", "unknown-run")),
                suite_name=str(case.get("suite", "unknown")),
                task_id=_task_id(case),
                sample_status=status,
                error_type=case.get("error_type") or ("PREDICATE_REPLAY_MISMATCH" if replayed and not replay_matches else None),
                payload_delivered=delivered,
                payload_hash=payload_hash(payload) if payload is not None else None,
                predicate_result=case.get("predicate_result") if status is SampleStatus.VALID else None,
                utility_result=case.get("utility_result") if status is SampleStatus.VALID else None,
                action_counts=case.get("action_counts", {}),
                final_state=compact_state,
            )
        )
    run_record = RunRecord(run_id=str(case_list[0].get("run_id", "audit-run")) if case_list else "audit-run", records=records, seed=seed)
    return {
        "schema_version": "dscg.harness-audit.v1",
        "seed": seed,
        "manifest_hash": manifest_hash(manifest),
        "sample_counts": run_record.compact_dict()["sample_counts"],
        "records": [record.compact_dict() for record in records],
    }


def audit_fixture_file(fixture_path: Path, output_path: Path, seed: int | str = 20260927) -> dict[str, Any]:
    cases = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("fixture must contain a JSON list")
    report = audit_cases(cases, seed=seed)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the compact offline E0 harness audit.")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260927)
    args = parser.parse_args()
    report = audit_fixture_file(args.fixture, args.output, seed=args.seed)
    print(json.dumps({"output": str(args.output), "sample_counts": report["sample_counts"], "manifest_hash": report["manifest_hash"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
