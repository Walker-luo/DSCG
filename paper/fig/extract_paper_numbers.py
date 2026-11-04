#!/usr/bin/env python3
"""Recompute the paper's paired results from the recorded result trees.

Reads only files under results/workshop/agentdojo and writes:
  paper/fig/paper_numbers.json
  paper/fig/results-tradeoff.csv

The script deliberately excludes keys recorded as infrastructure errors in
failure_cases.jsonl, because the task JSON of a failed attempt can still carry
stale utility/security fields.  It also asserts the headline numbers so a
silent data change cannot propagate into the paper.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "workshop" / "agentdojo"
OUT_JSON = ROOT / "paper" / "fig" / "paper_numbers.json"
OUT_CSV = ROOT / "paper" / "fig" / "results-tradeoff.csv"

MODELS = {
    "qwen35": ("qwen3.5-flash", "v3.7"),
    "qwen": ("qwen3.7-flash", "v3.6.3"),
    "deepseek": ("deepseek-flash", "v3.6.3"),
}
SUITES = ("workspace", "travel", "banking", "slack")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided binomial McNemar p-value, assuming independent paired keys."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def error_keys(model: str, arm: str) -> set[tuple[str, str, str, str]]:
    path = RESULTS / model / arm / "failure_cases.jsonl"
    keys: set[tuple[str, str, str, str]] = set()
    if not path.exists():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("sample_status") != "valid":
            keys.add(
                (
                    rec["suite"],
                    rec["attack"],
                    rec["user_task_id"],
                    rec["injection_task_id"],
                )
            )
    return keys


def load_attack(model: str, arm: str) -> dict[tuple[str, str, str, str], dict]:
    root = RESULTS / model / arm
    records: dict[tuple[str, str, str, str], dict] = {}
    for path in root.glob("*/*/*/*.json"):
        attack, suite, user, inj_file = (p for p in path.parts[-4:])
        key = (suite, attack, user, inj_file[:-5])
        records[key] = json.loads(path.read_text(encoding="utf-8"))
    return records


def load_clean(model: str, arm: str) -> dict[tuple[str, str], bool]:
    root = RESULTS / model / arm
    records: dict[tuple[str, str], bool] = {}
    for path in root.glob("none/*/*/none.json"):
        suite = path.parts[-3]
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("utility") is not None:
            records[(suite, rec["user_task_id"])] = bool(rec["utility"])
    return records


def summary_cost(model: str, arm: str) -> dict:
    data = json.loads((RESULTS / model / arm / "summary.json").read_text(encoding="utf-8"))
    total = audit = calls = 0
    for report in data.get("suite_reports", []):
        summary = report.get("summary") or {}
        total += (summary.get("overhead") or {}).get("total_tokens", 0) or 0
        audit += (summary.get("sec_overhead") or {}).get("total_tokens", 0) or 0
        router = summary.get("audit_router") or {}
        calls += router.get("semantic_audit_calls", 0) or 0
    recorded = data["cost_summary"]["scored"]
    assert total + audit == recorded["known_total_tokens"]
    return {"tokens": total + audit, "main_tokens": total, "audit_tokens": audit,
            "audit_calls": calls, "unknown_usage_records": recorded["unknown_usage_records"]}


def arm_stats(records: dict, key: tuple) -> tuple[bool, bool]:
    rec = records[key]
    return bool(rec["utility"]), bool(rec["security"])


def paired_stats(model: str, defense_arm: str) -> dict:
    base = load_attack(model, "baseline")
    dscg = load_attack(model, defense_arm)
    bad = error_keys(model, "baseline") | error_keys(model, defense_arm)
    common = [
        k
        for k in set(base) & set(dscg)
        if k not in bad
        and base[k].get("utility") is not None
        and base[k].get("security") is not None
        and dscg[k].get("utility") is not None
        and dscg[k].get("security") is not None
    ]
    suites: dict[str, dict] = {}
    for suite in SUITES:
        keys = [k for k in common if k[0] == suite]
        bu = sum(1 for k in keys if base[k]["utility"])
        du = sum(1 for k in keys if dscg[k]["utility"])
        ba = sum(1 for k in keys if base[k]["security"])
        da = sum(1 for k in keys if dscg[k]["security"])
        b = sum(1 for k in keys if base[k]["utility"] and not dscg[k]["utility"])
        c = sum(1 for k in keys if dscg[k]["utility"] and not base[k]["utility"])
        suites[suite] = {
            "n": len(keys),
            "base_tsr": bu,
            "dscg_tsr": du,
            "base_asr": ba,
            "dscg_asr": da,
            "base_tsr_pct": round(100 * bu / len(keys), 2),
            "dscg_tsr_pct": round(100 * du / len(keys), 2),
            "base_asr_pct": round(100 * ba / len(keys), 2),
            "dscg_asr_pct": round(100 * da / len(keys), 2),
            "delta_tsr_pp": round(100 * (du - bu) / len(keys), 2),
            "mcnemar_p": round(mcnemar_exact(b, c), 4),
        }
    total = {k: sum(v[k] for v in suites.values()) for k in
             ("n", "base_tsr", "dscg_tsr", "base_asr", "dscg_asr")}
    total["base_tsr_pct"] = round(100 * total["base_tsr"] / total["n"], 2)
    total["dscg_tsr_pct"] = round(100 * total["dscg_tsr"] / total["n"], 2)
    total["base_asr_pct"] = round(100 * total["base_asr"] / total["n"], 2)
    total["dscg_asr_pct"] = round(100 * total["dscg_asr"] / total["n"], 2)
    b = sum(1 for k in common if base[k]["utility"] and not dscg[k]["utility"])
    c = sum(1 for k in common if dscg[k]["utility"] and not base[k]["utility"])
    total["utility_discordant"] = [b, c]
    total["mcnemar_p"] = round(mcnemar_exact(b, c), 4)
    total["asr_upper95"] = round(100 * wilson(total["dscg_asr"], total["n"])[1], 2)
    return {"suites": suites, "total": total}


def main() -> int:
    payload = {
        "source": str(RESULTS.relative_to(ROOT)),
        "models": {},
    }
    for short, (model, defense_arm) in MODELS.items():
        paired = paired_stats(model, defense_arm)
        # Full-run counts (before pairing) for prose.
        full = {}
        for arm in ("baseline", defense_arm):
            records = load_attack(model, arm)
            bad = error_keys(model, arm)
            valid = [
                k for k in records
                if k not in bad
                and records[k].get("utility") is not None
                and records[k].get("security") is not None
            ]
            full[arm] = {
                "valid": len(valid),
                "tsr": sum(1 for k in valid if records[k]["utility"]),
                "asr": sum(1 for k in valid if records[k]["security"]),
                "errors": len(bad),
            }
        clean_base = load_clean(model, "baseline_clean")
        clean_dscg = load_clean(model, f"{defense_arm}_clean")
        clean = {
            "baseline": {
                "n": len(clean_base),
                "tsr": sum(clean_base.values()),
            },
            "dscg": {
                "n": len(clean_dscg),
                "tsr": sum(clean_dscg.values()),
            },
        }
        shared_clean = set(clean_base) & set(clean_dscg)
        if shared_clean:
            b = sum(1 for k in shared_clean if clean_base[k] and not clean_dscg[k])
            c = sum(1 for k in shared_clean if clean_dscg[k] and not clean_base[k])
            clean["paired_n"] = len(shared_clean)
            clean["mcnemar_p"] = round(mcnemar_exact(b, c), 4)
        cost = {
            "baseline": summary_cost(model, "baseline"),
            "dscg": summary_cost(model, defense_arm),
        }
        payload["models"][short] = {
            "model_id": model,
            "defense_run": defense_arm,
            "full": full,
            "paired": paired,
            "clean": clean,
            "cost": cost,
        }

    # Headline assertions: fail loudly if the result trees change.
    q = payload["models"]["qwen"]["paired"]["total"]
    d = payload["models"]["deepseek"]["paired"]["total"]
    q35 = payload["models"]["qwen35"]["paired"]["total"]
    assert (q["n"], q["base_tsr"], q["dscg_tsr"], q["base_asr"], q["dscg_asr"]) == (1943, 1425, 1540, 438, 0), q
    assert (d["n"], d["base_tsr"], d["dscg_tsr"], d["base_asr"], d["dscg_asr"]) == (1836, 1535, 1512, 38, 5), d
    assert (q35["n"], q35["base_tsr"], q35["dscg_tsr"], q35["base_asr"], q35["dscg_asr"]) == (2139, 1805, 1175, 221, 2), q35
    assert payload["models"]["qwen"]["clean"]["dscg"]["tsr"] == 83
    assert payload["models"]["deepseek"]["clean"]["baseline"]["tsr"] == 88
    assert payload["models"]["deepseek"]["clean"]["dscg"]["tsr"] == 84
    assert payload["models"]["qwen35"]["clean"]["baseline"]["tsr"] == 90
    assert payload["models"]["qwen35"]["clean"]["dscg"]["tsr"] == 53

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["model", "suite", "n", "base_tsr", "dscg_tsr", "base_asr", "dscg_asr", "delta_tsr_pp"]
        )
        for short in MODELS:
            for suite in SUITES:
                row = payload["models"][short]["paired"]["suites"][suite]
                writer.writerow(
                    [
                        short,
                        suite,
                        row["n"],
                        f"{100 * row['base_tsr'] / row['n']:.4f}",
                        f"{100 * row['dscg_tsr'] / row['n']:.4f}",
                        f"{100 * row['base_asr'] / row['n']:.4f}",
                        f"{100 * row['dscg_asr'] / row['n']:.4f}",
                        f"{100 * (row['dscg_tsr'] - row['base_tsr']) / row['n']:+.4f}",
                    ]
                )

    for short in MODELS:
        m = payload["models"][short]
        print(f"== {short} ({m['model_id']})")
        print("  full:", m["full"])
        print("  clean:", m["clean"])
        print("  cost:", m["cost"])
        for suite in SUITES:
            r = m["paired"]["suites"][suite]
            print(
                f"  {suite:9s} n={r['n']:4d} TSR {r['base_tsr_pct']:5.2f}->{r['dscg_tsr_pct']:5.2f} "
                f"ASR {r['base_asr_pct']:5.2f}->{r['dscg_asr_pct']:5.2f} p={r['mcnemar_p']:.4f}"
            )
        print("  total:", m["paired"]["total"])
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
