"""Portable history comparisons with explicit metric units and record denominators."""

import csv
import json
import zipfile
from collections import Counter
from io import BytesIO, StringIO


def _record_statistics(records):
    statuses = Counter(record["sample_status"] for record in records)
    observed = [row for row in records if row["sample_status"] in ("valid", "unknown")]

    def metric(key):
        values = [row[key] for row in observed if isinstance(row[key], bool)]
        numerator = sum(values)
        denominator = len(values)
        return {
            "numerator": numerator,
            "denominator": denominator,
            "percent": round(numerator * 100 / denominator, 2) if denominator else None,
        }

    return {
        "total": len(records),
        "sample_status_counts": dict(statuses),
        "tsr": metric("utility_success"),
        "asr": metric("attack_success"),
    }


def _suite_warnings(suite):
    records = suite["task_records"]
    warnings = []
    if suite["task_records_truncated"]:
        warnings.append("task_records_truncated")
    if not records:
        warnings.append("no_task_records")
    if any(row["sample_status"] == "unknown" for row in records):
        warnings.append("sample_status_unknown")
    if any(row["sample_status"] not in ("valid", "unknown") for row in records):
        warnings.append("reported_sample_errors_or_exclusions")
    if suite["task_counts"]["total_tasks"] != len(records):
        warnings.append("summary_record_count_mismatch")
    for metric, key in (("tsr", "utility_rate"), ("asr", "attack_success_rate")):
        reported = suite["metrics"][key]
        observed = suite["record_statistics"][metric]["percent"]
        if reported is not None and observed is not None and abs(reported - observed) > 0.01:
            warnings.append(f"summary_record_{metric}_mismatch")
    return warnings


def _csv_bytes(fieldnames, rows):
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        # Text originating in result files must remain text in spreadsheet readers.
        safe = {}
        for key, value in row.items():
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
                value = "'" + value
            safe[key] = value
        writer.writerow(safe)
    return output.getvalue().encode("utf-8-sig")


README = """# 历史对比分析数据

本下载按点击下载时勾选的实验和场景生成，同时包含 ASR 与 TSR，不受当前图表类型或指标选择影响。

- `analysis.json`：推荐交给 agent 的入口，包含实验来源、场景汇总、逐任务结果、分子/分母、缺失与截断标记；schema_version 为 2。
- `summary.csv`：每个实验 × 场景一行，可在 Excel 中查看。
- `task_records.csv`：带实验 ID 的逐任务结果，可按场景、user_task_id、injection_task_id、model_id、attack_type 对齐对比。

实验身份保留 result_folder、model_group、model_suffix、attack_name 和已记录的 benchmark 身份（仓库、版本、实现及任务目录哈希），可按原结果目录、模型/运行名称和攻击分组。缺失的 benchmark 身份保留 unknown，不能用当前安装的基准补写历史。unknown 表示没有记录攻击；mixed 表示旧汇总含多种攻击，不能据此拆分汇总分母。

## 指标口径

所有百分比均为 0–100，JSON 缺失值为 null，CSV 对应空单元格。布尔 False 是一次未成功的结果，与缺失值不同。

`metrics.utility_rate`（CSV 的 tsr_percent）是原汇总中的 TSR / 任务可用性，越高越好。
`metrics.attack_success_rate`（CSV 的 asr_percent）是原汇总中的 ASR / 攻击成功率，越低越好。
benchmark 汇总中的 0–1 比率已换算为百分比；dashboard 汇总使用原百分比。没有把缺失指标替换为零。

`record_statistics.tsr/asr` 单独报告从已导出明细算出的 numerator、denominator、percent。
TSR 使用 utility_success；ASR 使用 attack_success。只计入对应结果为布尔值且 sample_status 为 valid 或 unknown 的记录；明确的错误、无效、跳过记录不计入这两个明细分母。
分母为零时 percent 为 null。sample_status_counts 包含全部导出记录的状态计数。
旧记录无 sample_status 时标为 unknown，其布尔结果只用于观察性统计，不证明样本已通过 harness 审计；valid 也仅保留源文件的状态。

`task_counts` 是原汇总记录的任务数；旧格式缺失的 total_tasks、utility_passed、attacked_tasks 沿用历史分析的默认零值。
不能直接用 attacked_tasks 或 total_tasks 推定有效安全分母。原汇总可能含默认零值或使用不同样本口径，下载保留原值；分析时结合明细和 warnings，不能仅凭 ASR=0 宣称防御成功。

## 数据完整性与告警

- task_records_truncated：整个下载最多包含 50,000 条明细，当前场景有明细未导出；明细统计只代表已导出部分。
- no_task_records：此场景没有导出明细，可能是源文件缺失、不可读或下载上限已耗尽。
- sample_status_unknown：旧记录缺少可识别的样本状态，不能假定已通过有效性审计。
- reported_sample_errors_or_exclusions：源文件含错误、无效或跳过样本，查看状态计数和逐任务结果。
- summary_record_count_mismatch：原汇总任务数与导出的明细数不同。
- summary_record_tsr_mismatch / summary_record_asr_mismatch：原汇总与明细计算的百分比不同，不能混用两种分母。

paired_comparison_ready 和 comparison_warnings 标记已记录的基准及任务选择是否对齐。不同基准、不同任务目录或未知身份的结果独立展示，不合并分母或计算配对增益；身份匹配本身也不证明攻击、模型或独立 oracle 对齐。

部分实验没有当前选定场景时保留空 suites，不能将它视为零分。比较时先确认任务组合、攻击类型、模型和实验配置是否一致，缺失场景和未覆盖任务不算失败。
CSV 使用 UTF-8 BOM；可能被表格软件当作公式的文本会加单引号，JSON 保留原文本。

## 交给 agent 的建议

先读取 analysis.json 的 selection、metric_definitions 与 warnings；按场景比较各实验 ASR、TSR，再对齐逐任务结果定位“攻击成功”“合法任务失败”和“二者同时发生”的案例，提出有证据支持的框架改进建议。
这是结果摘要与任务 outcome 导出，不含完整 prompt、工具轨迹、API 凭据，也不自动补充源文件未保存的攻击投递或宿主 oracle 证据。需要归因时回到 source 指向的原实验目录检查轨迹。
现有历史 smoke 数据不能直接作为正式 benchmark、防御保证或论文结论。
"""


def build_history_export(experiments, suites_filter, exported_at, comparison=None):
    """Build a fixed-name ZIP from the already validated, normalized selection."""
    summary_rows = []
    task_rows = []
    for run in experiments:
        identity = {
            "experiment_id": run["id"], "label": run["label"],
            "source": run["source"], "result_type": run["result_type"],
            **{key: run.get(key, "") for key in ("result_folder", "model_group", "model_suffix", "attack_name")},
        }
        for suite in run["suites"]:
            benchmark = suite.get("benchmark") or {}
            identity.update({f"benchmark_{key}": benchmark.get(key, "") for key in
                ("id", "repository", "revision", "suite_version", "implementation_sha256", "catalog_sha256", "tasks_sha256", "environments_sha256", "attacks_sha256", "tools_sha256", "package_version", "runtime_variant", "source_kind", "release_sha256")})
            identity["benchmark_id"] = benchmark.get("id", "unknown")
            suite["record_statistics"] = _record_statistics(suite["task_records"])
            suite["warnings"] = _suite_warnings(suite)
            stats = suite["record_statistics"]
            statuses = stats["sample_status_counts"]
            summary_rows.append({
                **identity,
                "suite_name": suite["suite_name"], "pipeline_name": suite["pipeline_name"],
                "tsr_percent": suite["metrics"]["utility_rate"],
                "asr_percent": suite["metrics"]["attack_success_rate"],
                "defense_success_percent": suite["metrics"]["defense_success_rate"],
                "total_tasks": suite["task_counts"]["total_tasks"],
                "utility_passed": suite["task_counts"]["utility_passed"],
                "utility_valid": suite["task_counts"].get("utility_valid"),
                "execution_errors": suite["task_counts"].get("execution_errors"),
                "attacked_tasks": suite["task_counts"]["attacked_tasks"],
                "security_missing": suite["task_counts"].get("security_missing"),
                "total_tokens": suite["overhead"]["total_tokens"],
                "main_tokens": suite.get("main_overhead", suite["overhead"])["total_tokens"],
                "security_tokens": suite.get("sec_overhead", {}).get("total_tokens", 0),
                "security_usage_recorded": suite.get("security_usage_recorded", False),
                "exported_task_records": stats["total"],
                "observed_tsr_numerator": stats["tsr"]["numerator"],
                "observed_tsr_denominator": stats["tsr"]["denominator"],
                "observed_tsr_percent": stats["tsr"]["percent"],
                "observed_asr_numerator": stats["asr"]["numerator"],
                "observed_asr_denominator": stats["asr"]["denominator"],
                "observed_asr_percent": stats["asr"]["percent"],
                "reported_valid_records": statuses.get("valid", 0),
                "unknown_status_records": statuses.get("unknown", 0),
                "excluded_records": sum(n for status, n in statuses.items() if status not in ("valid", "unknown")),
                "task_records_truncated": suite["task_records_truncated"],
                "warnings": ";".join(suite["warnings"]),
            })
            task_rows.extend({**identity, **row} for row in suite["task_records"])

    data = {
        "schema_version": 2,
        "exported_at": exported_at,
        **(comparison or {}),
        "selection": {"run_ids": [run["id"] for run in experiments], "suites": suites_filter},
        "metric_definitions": {
            "unit": "percent (0-100)", "missing_value": None,
            "summary_metrics": "Original summaries normalized to percent; denominators are not inferred.",
            "tsr": {"summary_key": "utility_rate", "outcome_key": "utility_success", "preferred_direction": "higher"},
            "asr": {"summary_key": "attack_success_rate", "outcome_key": "attack_success", "preferred_direction": "lower"},
            "record_statistics": "Observed exported boolean outcomes with status valid/unknown; excludes reported errors, invalid and skipped records. Unknown status is not validated harness evidence. A zero denominator yields null percent.",
        },
        "counts": {"experiments": len(experiments), "suites": len(summary_rows), "task_records": len(task_rows)},
        "limitations": [
            "Statistics use recorded outcomes, not an independent replay of the harness oracle.",
            "Task records may be missing or truncated; check each suite's warnings before comparison.",
            "Runs may cover different task sets. Align task IDs, attack types and model IDs before attributing changes.",
            "This export contains outcomes, not complete agent/tool traces or unsaved experiment configuration.",
        ],
        "experiments": experiments,
    }
    task_fields = [
        "experiment_id", "label", "source", "result_type", "result_folder", "model_group",
        "model_suffix", "attack_name", "benchmark_id", "benchmark_repository", "benchmark_revision",
        "benchmark_suite_version", "benchmark_implementation_sha256", "benchmark_catalog_sha256",
        "benchmark_tasks_sha256", "benchmark_environments_sha256", "benchmark_attacks_sha256", "benchmark_tools_sha256",
        "benchmark_package_version", "benchmark_runtime_variant", "benchmark_source_kind", "benchmark_release_sha256", "suite_name", "model_id",
        "attack_type", "user_task_id", "injection_task_id", "sample_status",
        "utility_success", "attack_success", "defense_success",
    ]
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("analysis.json", json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8"))
        archive.writestr("summary.csv", _csv_bytes(list(summary_rows[0]), summary_rows))
        archive.writestr("task_records.csv", _csv_bytes(task_fields, task_rows))
        archive.writestr("README.md", README.encode("utf-8"))
    output.seek(0)
    return output
