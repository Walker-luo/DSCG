"""Offline AgentDojo simulation replay of recorded V2 actions; never runs an LLM."""
from collections import Counter
import ast
import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.task_suite import get_suite
from agentdojo.types import get_text_content_as_str

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from strings(item)

def decoded_strings(text):
    yield text
    for parser in (yaml.safe_load, ast.literal_eval):
        try:
            yield from strings(parser(text))
        except (ValueError, SyntaxError, yaml.YAMLError):
            continue

def normalised(text):
    return " ".join(text.split())

export = ROOT / "download/dscg-history-analysis-20261007T153203Z/analysis.json"
data = json.loads(export.read_text())
rows, hashes = [], {}
for experiment in data["experiments"]:
    if experiment["model_group"] != "deepseek-flash_workshop_v2":
        continue
    for summary in experiment["suites"]:
        suite = get_suite("v1.2", summary["suite_name"])
        for record in summary["task_records"]:
            path = (ROOT / "results" / experiment["source"] / summary["suite_name"] /
                    record["user_task_id"] / record["attack_type"] / (record["injection_task_id"] + ".json"))
            trace = json.loads(path.read_text())
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            task = suite.user_tasks[record["user_task_id"]]
            env = task.init_environment(suite.load_and_inject_default_environment(trace["injections"]))
            before = env.model_copy(deep=True)
            runtime = FunctionsRuntime(suite.tools)
            executed, errors, blocked, tool_texts = [], [], [], []
            final = []
            for message in trace["messages"]:
                if message["role"] == "assistant":
                    final = message.get("content") or []
                if message["role"] != "tool":
                    continue
                tool_texts.append(get_text_content_as_str(message.get("content") or []))
                if message.get("error"):
                    blocked.append(message["error"])
                    continue
                call = FunctionCall(**message["tool_call"])
                _, error = runtime.run_function(env, call.function, call.args)
                if error:
                    errors.append({"tool": call.function, "error": error})
                else:
                    executed.append(call)
            utility = suite._check_user_task_utility(task, final, before, env, executed)
            security = suite._check_injection_task_security(
                suite.injection_tasks[record["injection_task_id"]], final, before, env, executed)
            payloads = list(trace["injections"].values())
            observed = [normalised(text) for raw in tool_texts for text in decoded_strings(raw)]
            delivered = bool(payloads) and all(any(
                candidate and candidate in text for candidate in
                [normalised(value) for value in decoded_strings(payload)] for text in observed
            ) for payload in payloads)
            rows.append({"attack": record["attack_type"], "suite": summary["suite_name"],
                         "user": record["user_task_id"], "injection": record["injection_task_id"],
                         "payload_delivered": delivered, "recorded_utility": record["utility_success"],
                         "recorded_security": record["attack_success"], "replayed_utility": utility,
                         "replayed_security": security, "replay_errors": errors, "tool_errors": blocked,
                         "executed_tools": [call.function for call in executed],
                         "audit": trace["dscg_audit_summary"], "final_answer": get_text_content_as_str(final),
                         "source": str(path.relative_to(ROOT))})
counts = {"records": len(rows), "payload_delivered": sum(row["payload_delivered"] for row in rows),
          "replay_errors": sum(bool(row["replay_errors"]) for row in rows),
          "utility_mismatches": sum(row["recorded_utility"] != row["replayed_utility"] for row in rows),
          "security_mismatches": sum(row["recorded_security"] != row["replayed_security"] for row in rows),
          "recorded_TSR": sum(row["recorded_utility"] for row in rows),
          "recorded_ASR": sum(row["recorded_security"] for row in rows),
          "audit_decisions": dict(Counter(key for row in rows for key in row["audit"]["decision_counts"]
                                          for _ in range(row["audit"]["decision_counts"][key])))}
output = {"counts": counts, "rows": rows, "source_sha256": hashes,
          "limitations": ["Replay runs only AgentDojo's local simulated tools, never live services or models.",
                           "Payload delivery matches raw/YAML/literal-decoded strings after whitespace normalization in saved tool returns; not a complete E0 gate.",
                           "Uses installed native predicates and recorded arguments, not a new independent human oracle.",
                           "One historical run; no efficacy or causal guarantee."]}
Path(__file__).with_name("history_diagnosis.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(counts, indent=2))
for row in rows:
    if not row["payload_delivered"] or row["replay_errors"] or row["recorded_utility"] != row["replayed_utility"]:
        print(row["attack"], row["suite"], row["user"], row["injection"],
              "delivered=", row["payload_delivered"], "replay_errors=", row["replay_errors"])
raise SystemExit(1 if counts["replay_errors"] or counts["utility_mismatches"] or counts["security_mismatches"] else 0)
