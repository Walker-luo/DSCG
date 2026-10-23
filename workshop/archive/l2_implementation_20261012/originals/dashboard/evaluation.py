"""Dashboard configuration and observation summaries; no defense decisions here."""

import json
from copy import deepcopy
from pathlib import Path

from dscg.input_isolation import FRAMEWORK_VERSION

SUITES = {"workspace", "travel", "banking", "slack"}
ROUTING_KEYS = ("candidate_batches", "precheck_allowed_batches", "precheck_rejected_batches",
                "public_read_bypass_batches", "semantic_audit_calls")
ISOLATION_KEYS = ("model_requests", "tool_results_rendered", "escaped_results_rendered",
                  "added_characters_total")


def normalize_config(payload):
    config = dict(payload)
    suites = config.get("suites", [])
    if not isinstance(suites, list) or not suites or any(s not in SUITES for s in suites):
        raise ValueError("请选择有效的评测场景")
    config["suites"] = list(dict.fromkeys(suites))
    for key, default in (("origin", False), ("run_attack", True), ("use_sandbox", True),
                         ("use_security_checker", True), ("input_isolation", True),
                         ("authorization_precheck", True)):
        value = config.get(key, default)
        if not isinstance(value, bool):
            raise ValueError(f"{key} 必须为布尔值")
        config[key] = value
    for key in ("max_user_tasks", "max_injection_tasks", "selection_seed"):
        value = config.get(key, 20260927 if key == "selection_seed" else 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} 必须为非负整数")
        config[key] = value
    config.setdefault("trace_level", "summary")
    if config["trace_level"] not in ("summary", "standard", "full"):
        raise ValueError("请选择有效的日志级别")
    if config["origin"]:
        for key in ("use_sandbox", "use_security_checker", "input_isolation", "authorization_precheck"):
            config[key] = False
        for key in ("sec_model_id", "sec_provider", "sec_api_key", "sec_base_url", "tool_metadata_path"):
            config[key] = None
    elif not config["use_security_checker"]:
        for key in ("sec_model_id", "sec_provider", "sec_api_key", "sec_base_url"):
            config[key] = None
    config["input_isolation"] &= config["use_sandbox"] or config["use_security_checker"]
    config["authorization_precheck"] &= config["use_sandbox"]
    config["framework_version"] = None if config["origin"] else FRAMEWORK_VERSION
    return config


def aggregate(summaries):
    """Pool task counts (rather than equally weighting suites) and both model roles."""
    total = sum(s.get("task_counts", {}).get("total_tasks", 0) for s in summaries)
    passed = sum(s.get("task_counts", {}).get("utility_passed", 0) for s in summaries)
    denominator = 0
    successes = 0
    security_known = True
    for summary in summaries:
        counts = summary.get("task_counts", {})
        rate = summary.get("metrics", {}).get("attack_success_rate")
        valid = counts.get("security_valid")
        if valid is None:
            security_known = False
            continue
        if rate is not None and valid:
            denominator += valid
            successes += counts.get("attack_successes", rate * valid / 100)
    asr = round(successes / denominator * 100, 2) if denominator and security_known else None
    main = {key: sum(s.get("overhead", {}).get(key, 0) for s in summaries)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    security = {key: sum(s.get("sec_overhead", {}).get(key, 0) for s in summaries)
                for key in main}
    return {
        "avg_utility_rate": round(passed / total * 100, 2) if total else None,
        "avg_attack_success_rate": asr,
        "avg_defense_success_rate": round(100 - asr, 2) if asr is not None else None,
        "total_tasks": total, "utility_passed": passed,
        "security_denominator": denominator if security_known else None,
        "security_missing": (sum(s["task_counts"]["security_missing"] for s in summaries)
                             if all("security_missing" in s.get("task_counts", {}) for s in summaries) else None),
        "main_total_tokens": main["total_tokens"], "security_total_tokens": security["total_tokens"],
        "security_cost_complete": all("sec_overhead" in s for s in summaries),
        "total_tokens": main["total_tokens"] + security["total_tokens"],
        **{f"total_{key}": main[key] + security[key] for key in ("prompt_tokens", "completion_tokens")},
    }


def display_metrics(run):
    """Recover old dashboard denominators only from complete, unique task records."""
    summaries = deepcopy(run.get("suites", []))
    for summary in summaries:
        counts = summary.setdefault("task_counts", {})
        if run.get("config", {}).get("run_attack") is False:
            counts.update(security_valid=0, attack_successes=0, security_missing=0)
            summary.setdefault("metrics", {})["attack_success_rate"] = None
            continue
        records = [r for r in run.get("structured_records", [])
                   if r.get("suite_name") == summary.get("suite_name")]
        keys = {(r.get("user_task_id"), r.get("injection_task_id")) for r in records}
        if "security_valid" not in counts and records and len(records) == counts.get("total_tasks") and len(keys) == len(records):
            outcomes = [r.get("attack_success") for r in records]
            valid = [outcome for outcome in outcomes if isinstance(outcome, bool)]
            counts.update(security_valid=len(valid), attack_successes=sum(valid),
                          security_missing=len(outcomes) - len(valid))
    return aggregate(summaries)


def trace_stats(root, pipeline_name, suite, attack, task_keys):
    """Read only scored native task traces, excluding attack-generation preflights."""
    root = Path(root).resolve()
    stats = {"expected_records": len(task_keys), "trace_records": 0, "routing_records": 0,
             "isolation_records": 0, "routing": dict.fromkeys(ROUTING_KEYS, 0),
             "isolation": dict.fromkeys(ISOLATION_KEYS, 0)}
    for task_key in task_keys:
        injection = task_key[1] if len(task_key) > 1 else None
        path = root / pipeline_name.replace("/", "_") / suite / task_key[0] / attack / f"{injection or 'none'}.json"
        try:
            path.resolve().relative_to(root)
            trace = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(trace, dict):
                continue
        except (OSError, ValueError):
            continue
        stats["trace_records"] += 1
        for source, target, coverage in (("dscg_layer_routing", "routing", "routing_records"),
                                          ("dscg_input_isolation", "isolation", "isolation_records")):
            recorded = trace.get(source)
            if not isinstance(recorded, dict):
                continue
            stats[coverage] += 1
            for key in stats[target]:
                value = recorded.get(key, 0)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    stats[target][key] += value
    return stats
