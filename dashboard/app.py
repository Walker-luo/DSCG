"""
间接提示词注入防御框架 - Web 可视化面板
Flask 后端: 测试管理 / 实时日志 / 结果存储 / 报告生成
"""

import os
import sys
import json
import csv
import hashlib
import math
import time
import queue
import threading
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path

from flask import (
    Flask, render_template, request, jsonify, Response,
    send_file, stream_with_context
)

from agentdojo import logging as ad_logging, benchmark, attacks
from agentdojo.task_suite import get_suite
from dscg.model_config import DEEPSEEK_MODEL_IDS
from dscg.paths import DASHBOARD_RESULTS_DIR, RESULTS_DIR
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from dscg.pipelines.defended import make_defended_pipeline
from dscg.tool_metadata import load_tool_metadata

app = Flask(__name__)
app.secret_key = "newframe_dashboard_2024"

# =============================================
# 全局状态管理
# =============================================
# 存储所有测试运行的元数据和结果
runs_store: dict[str, dict] = {}
# 每个运行 ID 对应一个消息队列（用于 SSE 推送）
run_queues: dict[str, queue.Queue] = {}
# Raw credentials are kept only while a run is executing so log redaction can
# catch provider/client exceptions that echo request data.
run_secrets: dict[str, tuple[str, ...]] = {}
# 全局锁
_store_lock = threading.Lock()


def _redact_run_config(config: dict | None) -> dict:
    """Return a serialisable run config without exposing client credentials.

    The dashboard accepts credentials for a single background run, but result
    files, run listings and log messages must never contain the raw values.
    """
    safe_config = dict(config or {})
    for key in ("api_key", "sec_api_key"):
        if key in safe_config:
            safe_config[key] = "[provided]" if safe_config[key] else None
    return safe_config

DASHBOARD_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================
# 可用配置选项
# =============================================
DEEPSEEK_MODELS = [
    {
        "id": model_id,
        "label": model_id.replace("deepseek-", "DeepSeek ").replace("-", " ").replace("v4", "V4").title().replace("Deepseek", "DeepSeek"),
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com",
    }
    for model_id in DEEPSEEK_MODEL_IDS
]

AVAILABLE_MODELS = [
    {"id": "", "label": "Local/Env 配置", "provider": None, "base_url": None},
    {"id": "qwen3-max", "label": "Qwen3-Max", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-flash-2025-07-28", "label": "Qwen-Flash", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-plus", "label": "Qwen-Plus", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-turbo", "label": "Qwen-Turbo", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    *DEEPSEEK_MODELS,
    {"id": "kimi-k2", "label": "Kimi K2", "provider": "moonshot", "base_url": "https://api.moonshot.cn/v1"},
    {"id": "glm-4.5", "label": "GLM-4.5", "provider": "zhipu", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    {"id": "gpt-4.1-mini", "label": "OpenAI GPT-4.1 Mini", "provider": "openai", "base_url": "https://api.openai.com/v1"},
    {"id": "llama3.1", "label": "Ollama llama3.1", "provider": "ollama", "base_url": "http://localhost:11434/v1"},
]

AVAILABLE_SEC_MODELS = [
    {"id": "", "label": "Local/Env 配置", "provider": None, "base_url": None},
    {"id": "qwen3.5-plus", "label": "Qwen3.5-Plus", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-flash-2025-07-28", "label": "Qwen-Flash", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-turbo", "label": "Qwen-Turbo (轻量)", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "qwen-plus", "label": "Qwen-Plus", "provider": "dashscope", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    *DEEPSEEK_MODELS,
]

AVAILABLE_SUITES = [
    {"id": "workspace", "label": "Workspace", "user_tasks": 40, "injection_tasks": 14},
    {"id": "travel", "label": "Travel", "user_tasks": 20, "injection_tasks": 7},
    {"id": "banking", "label": "Banking", "user_tasks": 16, "injection_tasks": 9},
    {"id": "slack", "label": "Slack", "user_tasks": 21, "injection_tasks": 5},
]

AVAILABLE_ATTACKS = [
    {"id": "important_instructions", "label": "重要指令注入"},
    {"id": "manual_system_prompt_extraction", "label": "系统提示词提取"},
    {"id": "data_leakage", "label": "数据泄露"},
    {"id": "injection_delimiters", "label": "分隔符注入"},
    {"id": "ignore_previous", "label": "忽略前文指令"},
    {"id": "malicious_sandbox", "label": "恶意沙箱"},
]

AVAILABLE_DEFENSES = [
    {"id": None, "label": "无防御 (Baseline)"},
    {"id": "tool_filter", "label": "工具过滤器"},
    {"id": "transformers_pi_detector", "label": "注入检测器"},
    {"id": "spotlighting_with_delimiting", "label": "定界高亮"},
    {"id": "repeat_user_prompt", "label": "重复用户提示"},
]

# =============================================
# 工具函数
# =============================================
def push_log(run_id: str, level: str, message: str):
    """向指定 run 的消息队列推送一条日志"""
    if run_id in run_queues:
        safe_message = str(message)
        with _store_lock:
            secrets = run_secrets.get(run_id, ())
        for secret in secrets:
            if secret:
                safe_message = safe_message.replace(secret, "[REDACTED]")
        run_queues[run_id].put({
            "type": "log",
            "level": level,
            "message": safe_message,
            "timestamp": datetime.now().isoformat()
        })

def push_progress(run_id: str, progress: dict):
    """推送进度更新"""
    if run_id in run_queues:
        run_queues[run_id].put({
            "type": "progress",
            **progress,
            "timestamp": datetime.now().isoformat()
        })

def push_done(run_id: str, summary: dict):
    """推送完成信号"""
    if run_id in run_queues:
        run_queues[run_id].put({
            "type": "done",
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        })

class QueueStream(StringIO):
    """自定义输出流，写入时同步推送到消息队列"""
    def __init__(self, run_id: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self._buffer = ""

    def write(self, s):
        super().write(s)
        self._buffer += s
        # 遇到换行时推送整行
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                push_log(self.run_id, "info", line.strip())

    def flush(self):
        if self._buffer.strip():
            push_log(self.run_id, "info", self._buffer.strip())
            self._buffer = ""
        super().flush()


def run_test_thread(run_id: str, config: dict):
    """
    在后台线程中执行安全测试。
    这是对 experiments.run_benchmark 中评测逻辑的 Web 封装。
    """
    with _store_lock:
        run_secrets[run_id] = tuple(
            value for key in ("api_key", "sec_api_key")
            if (value := config.get(key))
        )
    try:
        push_log(run_id, "info", f"🚀 开始测试运行 [{run_id}]")
        push_log(
            run_id,
            "info",
            f"配置: {json.dumps(_redact_run_config(config), ensure_ascii=False)}",
        )

        model_id = config.get("model_id")
        sec_model_id = config.get("sec_model_id")
        provider = config.get("provider")
        base_url = config.get("base_url")
        api_key = config.get("api_key") or None
        sec_provider = config.get("sec_provider")
        sec_base_url = config.get("sec_base_url")
        sec_api_key = config.get("sec_api_key") or None
        suites = config["suites"]
        run_attack = config.get("run_attack", True)
        is_origin = config.get("origin", False)
        defense = config.get("defense")
        attack_name = config.get("attack_name", "important_instructions")
        use_sandbox = config.get("use_sandbox", True)
        use_security_checker = config.get("use_security_checker", True)
        max_user_tasks = config.get("max_user_tasks", 0)   # 0 = all
        max_injection_tasks = config.get("max_injection_tasks", 0)
        tool_metadata_path = config.get("tool_metadata_path") or None
        tool_metadata = load_tool_metadata(tool_metadata_path)
        if tool_metadata_path:
            push_log(
                run_id,
                "info",
                f"工具风险元数据: {tool_metadata_path}（已加载 {len(tool_metadata)} 项）",
            )

        # 结果存放目录
        run_dir = DASHBOARD_RESULTS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 重定向 stdout 以捕获日志
        old_stdout = sys.stdout
        qstream = QueueStream(run_id)
        sys.stdout = qstream

        all_summaries = []
        all_structured_records = []

        try:
            for suite_name in suites:
                push_log(run_id, "info", f"\n📂 正在测试套件: {suite_name}")
                push_progress(run_id, {
                    "current_suite": suite_name,
                    "status": "running",
                    "phase": "setup"
                })

                # ---- 构建 Pipeline ----
                if is_origin:
                    pipeline, main_tracker = make_openai_compatible_pipeline(
                        model_id,
                        ad_defense=defense,
                        api_key=api_key,
                        provider=provider,
                        base_url=base_url,
                    )
                    sec_tracker = None
                else:
                    # An omitted security override may reuse the explicitly
                    # supplied main credentials when both roles use the same
                    # provider (or when no separate security model is chosen).
                    same_connection = (
                        not sec_model_id
                        or (sec_provider and sec_provider == provider)
                    )
                    pipeline, main_tracker, sec_tracker = make_defended_pipeline(
                        model_id, sec_model_id,
                        use_sandbox=use_sandbox,
                        use_security_checker=use_security_checker,
                        api_key=api_key,
                        provider=provider,
                        base_url=base_url,
                        sec_api_key=sec_api_key if sec_api_key else (api_key if same_connection else None),
                        sec_provider=sec_provider,
                        sec_base_url=sec_base_url if sec_base_url else (base_url if same_connection else None),
                        tool_metadata=tool_metadata,
                    )

                main_model_config = getattr(pipeline, "dscg_model_config", {})
                sec_model_config = getattr(pipeline, "dscg_security_model_config", {})
                resolved_model_id = main_model_config.get("model_id", model_id)
                resolved_sec_model_id = sec_model_config.get("model_id", sec_model_id)
                config["resolved_main_model"] = main_model_config
                if sec_model_config:
                    config["resolved_security_model"] = sec_model_config
                push_log(run_id, "info", f"已解析模型配置: main={resolved_model_id}, security={resolved_sec_model_id or '无'}")

                # ---- 加载套件 ----
                suite = get_suite("v1.2", suite_name)
                user_task_ids = list(suite.user_tasks.keys())
                injection_task_ids = list(suite.injection_tasks.keys())

                push_log(run_id, "info",
                    f"[{suite_name}] User Tasks: {len(user_task_ids)}, "
                    f"Injection Tasks: {len(injection_task_ids)}")

                # ---- 选择任务子集 ----
                if max_user_tasks > 0 and max_user_tasks < len(user_task_ids):
                    selected_users = user_task_ids[:max_user_tasks]
                else:
                    selected_users = user_task_ids

                if max_injection_tasks > 0 and max_injection_tasks < len(injection_task_ids):
                    selected_injections = injection_task_ids[:max_injection_tasks]
                else:
                    selected_injections = injection_task_ids

                push_log(run_id, "info",
                    f"[{suite_name}] 选中 {len(selected_users)} 个用户任务, "
                    f"{len(selected_injections)} 个注入任务")

                # ---- 加载攻击 ----
                attack = attacks.load_attack(attack_name, suite, pipeline)

                # ---- 运行基准测试 ----
                push_progress(run_id, {
                    "current_suite": suite_name,
                    "status": "running",
                    "phase": "benchmark"
                })

                with ad_logging.OutputLogger(str(run_dir)):
                    if run_attack:
                        results = benchmark.benchmark_suite_with_injections(
                            pipeline, suite, attack, run_dir,
                            force_rerun=True,
                            user_tasks=selected_users,
                            injection_tasks=selected_injections,
                            verbose=True
                        )
                    else:
                        results = benchmark.benchmark_suite_without_injections(
                            pipeline, suite, run_dir,
                            force_rerun=True,
                            user_tasks=selected_users,
                            injection_tasks=selected_injections
                        )

                # ---- 结果分析 ----
                utility_results = results["utility_results"]
                security_results = results.get("security_results", {})

                # 结构化记录
                for task_key, util_status in utility_results.items():
                    user_task_id = task_key[0]
                    injection_task_id = task_key[1] if len(task_key) > 1 else "None"
                    attack_success = security_results.get(task_key, False) if run_attack else None
                    defense_success = not attack_success if run_attack else None

                    all_structured_records.append({
                        "suite_name": suite_name,
                        "model_id": resolved_model_id,
                        "attack_type": attack_name if run_attack else "None",
                        "user_task_id": user_task_id,
                        "injection_task_id": injection_task_id,
                        "utility_success": bool(util_status),
                        "attack_success": attack_success,
                        "defense_success": defense_success
                    })

                # 指标计算
                utility_score = (
                    sum(utility_results.values()) / len(utility_results)
                    if utility_results else 0
                )
                security_score = (
                    sum(security_results.values()) / len(security_results)
                    if run_attack and security_results else 0
                )
                defense_score = 1.0 - security_score if run_attack else 1.0

                prompt_tokens = main_tracker.total_prompt_tokens
                completion_tokens = main_tracker.total_completion_tokens
                total_tokens = main_tracker.get_total_tokens()

                summary = {
                    "suite_name": suite_name,
                    "pipeline_name": pipeline.name,
                    "metrics": {
                        "utility_rate": round(utility_score * 100, 2),
                        "attack_success_rate": round(security_score * 100, 2),
                        "defense_success_rate": round(defense_score * 100, 2),
                    },
                    "task_counts": {
                        "total_tasks": len(utility_results),
                        "utility_passed": int(sum(utility_results.values())),
                        "attacked_tasks": len(security_results),
                    },
                    "overhead": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                    }
                }

                if sec_tracker and use_security_checker:
                    summary["sec_overhead"] = {
                        "prompt_tokens": sec_tracker.total_prompt_tokens,
                        "completion_tokens": sec_tracker.total_completion_tokens,
                        "total_tokens": sec_tracker.get_total_tokens(),
                    }

                all_summaries.append(summary)

                push_log(run_id, "info",
                    f"✅ [{suite_name}] 完成! "
                    f"TSR={utility_score:.1%}, ASR={security_score:.1%}, "
                    f"Defense={defense_score:.1%}")

                # ---- 保存结果文件 ----
                suite_output_dir = run_dir / suite_name
                suite_output_dir.mkdir(parents=True, exist_ok=True)

                # CSV
                if all_structured_records:
                    suite_records = [r for r in all_structured_records if r["suite_name"] == suite_name]
                    if suite_records:
                        with open(suite_output_dir / "detailed_results.csv", "w",
                                  encoding="utf-8", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=suite_records[0].keys())
                            writer.writeheader()
                            writer.writerows(suite_records)

                # JSON summary
                with open(suite_output_dir / "summary.json", "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=4, ensure_ascii=False)

        finally:
            sys.stdout = old_stdout

        # ---- 汇总所有套件结果 ----
        overall = {
            "run_id": run_id,
            "config": _redact_run_config(config),
            "completed_at": datetime.now().isoformat(),
            "num_suites": len(all_summaries),
            "suites": all_summaries,
            "total_tasks": sum(s["task_counts"]["total_tasks"] for s in all_summaries),
            "aggregate_metrics": _compute_aggregate(all_summaries),
            "structured_records": all_structured_records,
        }

        # 保存整体结果
        with open(run_dir / "overall_results.json", "w", encoding="utf-8") as f:
            json.dump(overall, f, indent=4, ensure_ascii=False, default=str)

        with _store_lock:
            runs_store[run_id] = overall

        push_done(run_id, overall["aggregate_metrics"])
        push_log(run_id, "info", f"🏁 测试全部完成! 结果已保存至 {run_dir}")

    except Exception as e:
        import traceback
        push_log(run_id, "error", f"❌ 测试异常: {str(e)}")
        push_log(run_id, "error", traceback.format_exc())
        push_done(run_id, {"error": str(e)})
    finally:
        # 清理队列（延迟，让 SSE 客户端有机会读取完）
        def _cleanup():
            time.sleep(10)
            run_queues.pop(run_id, None)
            with _store_lock:
                run_secrets.pop(run_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()


def _compute_aggregate(summaries: list[dict]) -> dict:
    """计算跨套件的聚合指标"""
    if not summaries:
        return {}
    n = len(summaries)
    return {
        "avg_utility_rate": round(sum(s["metrics"]["utility_rate"] for s in summaries) / n, 2),
        "avg_attack_success_rate": round(sum(s["metrics"]["attack_success_rate"] for s in summaries) / n, 2),
        "avg_defense_success_rate": round(sum(s["metrics"]["defense_success_rate"] for s in summaries) / n, 2),
        "total_prompt_tokens": int(sum(s["overhead"]["prompt_tokens"] for s in summaries)),
        "total_completion_tokens": int(sum(s["overhead"]["completion_tokens"] for s in summaries)),
        "total_tokens": int(sum(s["overhead"]["total_tokens"] for s in summaries)),
    }


# =============================================
# 历史结果目录
# =============================================
HISTORY_SUITES = ("workspace", "travel", "banking", "slack")
MAX_HISTORY_EXPERIMENTS = 100
MAX_HISTORY_TASK_RECORDS = 50000


def _iter_history_files(results_root: Path, filename: str):
    """Walk results without following symlinks or returning files outside results/."""
    for current, directories, filenames in os.walk(results_root, followlinks=False):
        current_path = Path(current)
        directories[:] = sorted(
            name for name in directories
            if not (current_path / name).is_symlink()
        )
        if filename not in filenames:
            continue
        path = current_path / filename
        if path.is_symlink():
            continue
        try:
            path.resolve(strict=True).relative_to(results_root)
        except (OSError, ValueError):
            continue
        yield path


def _read_history_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as result_file:
            data = json.load(result_file)
        return data if isinstance(data, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _history_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _history_percent(value, is_fraction: bool) -> float | None:
    number = _history_number(value)
    if number is None:
        return None
    if is_fraction and 0 <= number <= 1:
        number *= 100
    return round(number, 2)


def _history_int(value) -> int:
    number = _history_number(value)
    return int(number) if number is not None else 0


def _normalize_history_suite(summary: dict, suite_name: str, is_fraction: bool) -> dict:
    metrics = summary.get("metrics")
    task_counts = summary.get("task_counts")
    overhead = summary.get("overhead")
    metrics = metrics if isinstance(metrics, dict) else {}
    task_counts = task_counts if isinstance(task_counts, dict) else {}
    overhead = overhead if isinstance(overhead, dict) else {}
    prompt_tokens = _history_int(overhead.get("prompt_tokens"))
    completion_tokens = _history_int(overhead.get("completion_tokens"))
    total_tokens = _history_int(overhead.get("total_tokens")) or (
        prompt_tokens + completion_tokens
    )
    return {
        "suite_name": suite_name,
        "pipeline_name": str(summary.get("pipeline_name") or ""),
        "metrics": {
            "utility_rate": _history_percent(metrics.get("utility_rate"), is_fraction),
            "attack_success_rate": _history_percent(
                metrics.get("attack_success_rate"), is_fraction
            ),
            "defense_success_rate": _history_percent(
                metrics.get("defense_success_rate"), is_fraction
            ),
        },
        "task_counts": {
            "total_tasks": _history_int(task_counts.get("total_tasks")),
            "utility_passed": _history_int(task_counts.get("utility_passed")),
            "attacked_tasks": _history_int(task_counts.get("attacked_tasks")),
        },
        "overhead": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
    }


def _history_entry_id(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:20]


def _history_source_for_suite(results_root: Path, suite_dir: Path) -> str | None:
    parts = suite_dir.relative_to(results_root).parts
    if not parts:
        return None
    if parts[0] == "dashboard" and len(parts) > 1:
        return "/".join(parts[:2])
    return "/".join(parts[:-1]) if len(parts) > 1 else None


def _build_history_catalog(results_root: Path | None = None) -> list[dict]:
    """Index supported experiment summaries while keeping disk paths server-side."""
    root = Path(results_root or RESULTS_DIR).resolve()
    if not root.is_dir():
        return []

    entries: dict[str, dict] = {}

    def ensure_entry(source: str) -> dict:
        source = source.strip("/")
        entry_id = _history_entry_id(source)
        return entries.setdefault(entry_id, {
            "id": entry_id,
            "source": source,
            "result_type": source.split("/", 1)[0],
            "suites": {},
            "overall_records": [],
            "config": {},
            "pipeline_name": "",
            "updated_timestamp": 0.0,
        })

    def mark_updated(entry: dict, path: Path):
        try:
            entry["updated_timestamp"] = max(
                entry["updated_timestamp"], path.stat().st_mtime
            )
        except OSError:
            pass

    # Dashboard runs store suite summaries together in overall_results.json.
    for overall_path in _iter_history_files(root, "overall_results.json"):
        data = _read_history_json(overall_path)
        if data is None:
            continue
        source = overall_path.parent.relative_to(root).as_posix()
        if source == ".":
            continue
        entry = ensure_entry(source)
        entry["config"] = data.get("config") if isinstance(data.get("config"), dict) else {}
        entry["overall_records"] = (
            data.get("structured_records")
            if isinstance(data.get("structured_records"), list)
            else []
        )
        mark_updated(entry, overall_path)
        raw_suites = data.get("suites")
        for suite_summary in raw_suites if isinstance(raw_suites, list) else []:
            if not isinstance(suite_summary, dict):
                continue
            suite_name = suite_summary.get("suite_name")
            if suite_name not in HISTORY_SUITES:
                continue
            entry["pipeline_name"] = (
                entry["pipeline_name"] or str(suite_summary.get("pipeline_name") or "")
            )
            suite_entry = entry["suites"].setdefault(suite_name, {})
            suite_entry["summary"] = suite_summary

    # Benchmark and partial-benchmark output write one summary per suite.
    for summary_path in _iter_history_files(root, "summary.json"):
        suite_name = summary_path.parent.name
        if suite_name not in HISTORY_SUITES:
            continue
        source = _history_source_for_suite(root, summary_path.parent)
        if not source:
            continue

        summary = _read_history_json(summary_path)
        if summary is None:
            continue
        entry = ensure_entry(source)
        entry["pipeline_name"] = (
            entry["pipeline_name"] or str(summary.get("pipeline_name") or "")
        )
        suite_entry = entry["suites"].setdefault(suite_name, {})
        suite_entry.setdefault("summary", summary)
        csv_path = summary_path.parent / "detailed_results.csv"
        if csv_path.is_file() and not csv_path.is_symlink():
            suite_entry["csv_path"] = csv_path
            mark_updated(entry, csv_path)
        mark_updated(entry, summary_path)

    # Older or interrupted runs may have task-level CSV files without summaries.
    for csv_path in _iter_history_files(root, "detailed_results.csv"):
        suite_name = csv_path.parent.name
        if suite_name not in HISTORY_SUITES:
            continue
        source = _history_source_for_suite(root, csv_path.parent)
        if not source:
            continue
        entry = ensure_entry(source)
        suite_entry = entry["suites"].setdefault(suite_name, {})
        suite_entry.setdefault("csv_path", csv_path)
        mark_updated(entry, csv_path)

    catalog = []
    for entry in entries.values():
        if not entry["suites"]:
            continue
        config = entry.get("config") or {}
        first_summary = next(
            (
                suite_entry.get("summary", {})
                for suite_entry in entry["suites"].values()
                if suite_entry.get("summary")
            ),
            {},
        )
        label = (
            config.get("label")
            or entry["pipeline_name"]
            or first_summary.get("pipeline_name")
            or entry["source"].rsplit("/", 1)[-1]
        )
        is_fraction = entry["result_type"] != "dashboard"
        suites = []
        for suite_name in HISTORY_SUITES:
            suite_entry = entry["suites"].get(suite_name)
            if not suite_entry:
                continue
            summary = suite_entry.get("summary")
            if not isinstance(summary, dict) and suite_entry.get("csv_path"):
                summary = _history_csv_summary(suite_entry["csv_path"], suite_name)
                is_fraction = False
            else:
                is_fraction = entry["result_type"] != "dashboard"
            if not isinstance(summary, dict):
                continue
            suites.append(_normalize_history_suite(
                summary, suite_name, is_fraction
            ))
        if not suites:
            continue
        timestamp = entry["updated_timestamp"]
        catalog.append({
            "id": entry["id"],
            "label": str(label),
            "source": entry["source"],
            "result_type": entry["result_type"],
            "updated_at": (
                datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
                if timestamp
                else ""
            ),
            "suites": suites,
            "_internal": entry,
        })

    catalog.sort(key=lambda item: item["updated_at"], reverse=True)
    return catalog


def _history_bool(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, str):
        value = value.strip().lower()
    if value in (1, "1", "true", "yes"):
        return True
    if value in (0, "0", "false", "no"):
        return False
    return None


def _normalize_history_record(record: dict, suite_name: str) -> dict:
    return {
        "suite_name": suite_name,
        "user_task_id": str(record.get("user_task_id") or ""),
        "injection_task_id": str(record.get("injection_task_id") or ""),
        "utility_success": _history_bool(record.get("utility_success")),
        "attack_success": _history_bool(record.get("attack_success")),
        "defense_success": _history_bool(record.get("defense_success")),
    }


def _history_csv_summary(csv_path: Path, suite_name: str) -> dict | None:
    utility = []
    attacks = []
    defenses = []
    total = 0
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as result_file:
            for row in csv.DictReader(result_file):
                if row.get("suite_name") and row["suite_name"] != suite_name:
                    continue
                total += 1
                value = _history_bool(row.get("utility_success"))
                if value is not None:
                    utility.append(value)
                value = _history_bool(row.get("attack_success"))
                if value is not None:
                    attacks.append(value)
                value = _history_bool(row.get("defense_success"))
                if value is not None:
                    defenses.append(value)
    except (OSError, UnicodeError, csv.Error):
        return None
    if not total:
        return None

    def rate(values):
        return round(sum(value is True for value in values) * 100 / len(values), 2) if values else None

    return {
        "suite_name": suite_name,
        "metrics": {
            "utility_rate": rate(utility),
            "attack_success_rate": rate(attacks),
            "defense_success_rate": rate(defenses),
        },
        "task_counts": {
            "total_tasks": total,
            "utility_passed": sum(value is True for value in utility),
            "attacked_tasks": len(attacks),
        },
        "overhead": {},
    }


def _load_history_task_records(
    suite_entry: dict, fallback_records: list, suite_name: str, limit: int
) -> tuple[list[dict], bool]:
    csv_path = suite_entry.get("csv_path")
    records = []
    truncated = False
    if csv_path:
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as result_file:
                for row in csv.DictReader(result_file):
                    row_suite = row.get("suite_name")
                    if row_suite and row_suite != suite_name:
                        continue
                    if len(records) >= limit:
                        truncated = True
                        break
                    records.append(_normalize_history_record(row, suite_name))
        except (OSError, UnicodeError, csv.Error):
            records = []
    if not records:
        for row in fallback_records:
            if not isinstance(row, dict) or row.get("suite_name") != suite_name:
                continue
            if len(records) >= limit:
                truncated = True
                break
            records.append(_normalize_history_record(row, suite_name))
    return records, truncated


# =============================================
# API 路由
# =============================================

@app.route("/")
def index():
    """主页面"""
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    """返回所有可用的配置选项"""
    return jsonify({
        "models": AVAILABLE_MODELS,
        "sec_models": AVAILABLE_SEC_MODELS,
        "suites": AVAILABLE_SUITES,
        "attacks": AVAILABLE_ATTACKS,
        "defenses": AVAILABLE_DEFENSES,
    })


@app.route("/api/history/catalog", methods=["GET"])
def history_catalog():
    """List results under results/ without exposing arbitrary filesystem paths."""
    catalog = _build_history_catalog()
    return jsonify([
        {key: value for key, value in entry.items() if key != "_internal"}
        for entry in catalog
    ])


@app.route("/api/history/analyze", methods=["POST"])
def analyze_history_results():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Invalid analysis request"}), 400
    run_ids = payload.get("run_ids")
    if (
        not isinstance(run_ids, list)
        or not run_ids
        or len(run_ids) > MAX_HISTORY_EXPERIMENTS
        or any(not isinstance(run_id, str) for run_id in run_ids)
    ):
        return jsonify({"error": "Select between 1 and 100 result sets"}), 400
    run_ids = list(dict.fromkeys(run_ids))

    suites_filter = payload.get("suites", [])
    if not isinstance(suites_filter, list) or any(
        suite not in HISTORY_SUITES for suite in suites_filter
    ):
        return jsonify({"error": "Invalid suite selection"}), 400

    catalog = _build_history_catalog()
    by_id = {entry["id"]: entry for entry in catalog}
    if any(run_id not in by_id for run_id in run_ids):
        return jsonify({"error": "One or more result sets were not found"}), 404

    include_task_records = payload.get("include_task_records") is True
    remaining_records = MAX_HISTORY_TASK_RECORDS
    experiments = []
    for run_id in run_ids:
        entry = by_id[run_id]
        internal = entry["_internal"]
        experiment = {
            "id": entry["id"],
            "label": entry["label"],
            "source": entry["source"],
            "result_type": entry["result_type"],
            "suites": [],
        }
        for suite_name in HISTORY_SUITES:
            if suites_filter and suite_name not in suites_filter:
                continue
            suite_entry = internal["suites"].get(suite_name)
            if not suite_entry:
                continue
            summary = suite_entry.get("summary")
            if not isinstance(summary, dict) and suite_entry.get("csv_path"):
                summary = _history_csv_summary(suite_entry["csv_path"], suite_name)
                is_fraction = False
            else:
                is_fraction = internal["result_type"] != "dashboard"
            if not isinstance(summary, dict):
                continue
            suite_result = _normalize_history_suite(
                summary,
                suite_name,
                is_fraction,
            )
            if include_task_records and remaining_records > 0:
                records, truncated = _load_history_task_records(
                    suite_entry,
                    internal["overall_records"],
                    suite_name,
                    remaining_records,
                )
                suite_result["task_records"] = records
                suite_result["task_records_truncated"] = truncated
                remaining_records -= len(records)
            experiment["suites"].append(suite_result)
        experiments.append(experiment)
    return jsonify({"experiments": experiments})


@app.route("/api/runs", methods=["GET"])
def list_runs():
    """列出所有已完成的测试运行"""
    with _store_lock:
        runs = [
            {
                "run_id": rid,
                "config": r["config"],
                "completed_at": r.get("completed_at", ""),
                "num_suites": r.get("num_suites", 0),
                "aggregate_metrics": r.get("aggregate_metrics", {}),
            }
            for rid, r in runs_store.items()
        ]
    # 同时扫描磁盘上保存的结果
    if DASHBOARD_RESULTS_DIR.exists():
        for d in sorted(DASHBOARD_RESULTS_DIR.iterdir(), reverse=True):
            if d.is_dir():
                result_file = d / "overall_results.json"
                if result_file.exists() and d.name not in runs_store:
                    try:
                        with open(result_file, "r") as f:
                            data = json.load(f)
                        runs.append({
                            "run_id": d.name,
                            "config": _redact_run_config(data.get("config", {})),
                            "completed_at": data.get("completed_at", ""),
                            "num_suites": data.get("num_suites", 0),
                            "aggregate_metrics": data.get("aggregate_metrics", {}),
                        })
                    except Exception:
                        pass
    return jsonify(runs)


@app.route("/api/runs/<run_id>", methods=["GET"])
def get_run(run_id: str):
    """获取单个运行的完整结果"""
    with _store_lock:
        run = runs_store.get(run_id)

    if not run:
        # 尝试从磁盘加载
        result_file = DASHBOARD_RESULTS_DIR / run_id / "overall_results.json"
        if result_file.exists():
            with open(result_file, "r") as f:
                run = json.load(f)
            if isinstance(run, dict):
                run["config"] = _redact_run_config(run.get("config", {}))

    if not run:
        return jsonify({"error": "Run not found"}), 404

    return jsonify(run)


@app.route("/api/runs/<run_id>/suite/<suite_name>", methods=["GET"])
def get_suite_result(run_id: str, suite_name: str):
    """获取某个 suite 的详细结果"""
    suite_dir = DASHBOARD_RESULTS_DIR / run_id / suite_name
    result = {}
    csv_path = suite_dir / "detailed_results.csv"
    summary_path = suite_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            result["summary"] = json.load(f)
    if csv_path.exists():
        records = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        result["records"] = records
    return jsonify(result)


@app.route("/api/run", methods=["POST"])
def start_run():
    """启动一个新的测试运行"""
    config = request.get_json(silent=True) or {}
    if not isinstance(config, dict):
        return jsonify({"error": "Invalid JSON configuration"}), 400

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    run_queues[run_id] = queue.Queue()

    with _store_lock:
        runs_store[run_id] = {
            "run_id": run_id,
            "config": _redact_run_config(config),
            "status": "running",
            "started_at": datetime.now().isoformat(),
        }

    # 在后台线程中运行测试
    thread = threading.Thread(
        target=run_test_thread,
        args=(run_id, config),
        daemon=True
    )
    thread.start()

    return jsonify({"run_id": run_id, "status": "started"})


@app.route("/api/stream/<run_id>")
def stream_logs(run_id: str):
    """SSE 端点：实时推送测试日志"""
    if run_id not in run_queues:
        run_queues[run_id] = queue.Queue()

    q = run_queues[run_id]

    def generate():
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg, ensure_ascii=False, default=str)}\n\n"
                if msg.get("type") == "done":
                    break
            except queue.Empty:
                # 发送心跳保持连接
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/compare", methods=["POST"])
def compare_runs():
    """对比多次运行的结果"""
    data = request.get_json()
    run_ids = data.get("run_ids", [])

    runs_data = []
    for rid in run_ids:
        with _store_lock:
            run = runs_store.get(rid)
        if not run:
            result_file = DASHBOARD_RESULTS_DIR / rid / "overall_results.json"
            if result_file.exists():
                with open(result_file, "r") as f:
                    run = json.load(f)
        if run:
            runs_data.append(run)

    # 构建对比数据结构
    comparison = {
        "run_ids": run_ids,
        "labels": [
            r.get("config", {}).get("label", f"Run {r['run_id'][:12]}")
            for r in runs_data
        ],
        "metrics": [],
        "per_suite": {},
    }

    metric_names = ["avg_utility_rate", "avg_attack_success_rate", "avg_defense_success_rate"]
    metric_labels = ["可用性 TSR (%)", "攻击成功率 ASR (%)", "防御成功率 (%)"]

    for name, label in zip(metric_names, metric_labels):
        values = []
        for r in runs_data:
            agg = r.get("aggregate_metrics", {})
            values.append(agg.get(name, 0))
        comparison["metrics"].append({
            "name": name,
            "label": label,
            "values": values,
        })

    # Token 对比
    comparison["token_metrics"] = {
        "labels": comparison["labels"],
        "prompt_tokens": [r.get("aggregate_metrics", {}).get("total_prompt_tokens", 0) for r in runs_data],
        "completion_tokens": [r.get("aggregate_metrics", {}).get("total_completion_tokens", 0) for r in runs_data],
        "total_tokens": [r.get("aggregate_metrics", {}).get("total_tokens", 0) for r in runs_data],
    }

    # 按套件对比
    all_suites = set()
    for r in runs_data:
        for s in r.get("suites", []):
            all_suites.add(s["suite_name"])
    for suite_name in sorted(all_suites):
        comparison["per_suite"][suite_name] = {
            "labels": comparison["labels"],
            "utility_rates": [],
            "attack_rates": [],
            "defense_rates": [],
        }
        for r in runs_data:
            suite_data = next(
                (s for s in r.get("suites", []) if s["suite_name"] == suite_name),
                None
            )
            if suite_data:
                m = suite_data["metrics"]
                comparison["per_suite"][suite_name]["utility_rates"].append(m["utility_rate"])
                comparison["per_suite"][suite_name]["attack_rates"].append(m["attack_success_rate"])
                comparison["per_suite"][suite_name]["defense_rates"].append(m["defense_success_rate"])
            else:
                comparison["per_suite"][suite_name]["utility_rates"].append(None)
                comparison["per_suite"][suite_name]["attack_rates"].append(None)
                comparison["per_suite"][suite_name]["defense_rates"].append(None)

    return jsonify(comparison)


@app.route("/api/report/<run_id>")
def download_report(run_id: str):
    """生成并下载文本报告"""
    with _store_lock:
        run = runs_store.get(run_id)
    if not run:
        result_file = DASHBOARD_RESULTS_DIR / run_id / "overall_results.json"
        if result_file.exists():
            with open(result_file, "r") as f:
                run = json.load(f)
    if not run:
        return jsonify({"error": "Run not found"}), 404

    # 生成文本报告
    lines = []
    lines.append("=" * 60)
    lines.append("  间接提示词注入防御框架 - 安全测试报告")
    lines.append("=" * 60)
    lines.append(f"运行 ID: {run_id}")
    lines.append(f"完成时间: {run.get('completed_at', 'N/A')}")
    lines.append("")

    config = run.get("config", {})
    lines.append("【测试配置】")
    lines.append(f"  主模型: {config.get('model_id', 'N/A')}")
    lines.append(f"  审计模型: {config.get('sec_model_id', 'None')}")
    lines.append(f"  测试套件: {', '.join(config.get('suites', []))}")
    lines.append(f"  执行攻击: {config.get('run_attack', True)}")
    lines.append(f"  攻击类型: {config.get('attack_name', 'N/A')}")
    lines.append(f"  框架类型: {'原始模型' if config.get('origin') else 'DSCG'}")
    if config.get("defense"):
        lines.append(f"  AgentDojo 防御: {config.get('defense')}")
    if not config.get("origin"):
        lines.append(f"  沙箱: {'启用' if config.get('use_sandbox', True) else '禁用'}")
        lines.append(f"  安全校验器: {'启用' if config.get('use_security_checker', True) else '禁用'}")
    lines.append("")

    agg = run.get("aggregate_metrics", {})
    lines.append("【聚合指标】")
    lines.append(f"  平均可用性 (TSR): {agg.get('avg_utility_rate', 0):.2f}%")
    lines.append(f"  平均攻击成功率 (ASR): {agg.get('avg_attack_success_rate', 0):.2f}%")
    lines.append(f"  平均防御成功率: {agg.get('avg_defense_success_rate', 0):.2f}%")
    lines.append(f"  总 Prompt Tokens: {agg.get('total_prompt_tokens', 0):,}")
    lines.append(f"  总 Completion Tokens: {agg.get('total_completion_tokens', 0):,}")
    lines.append(f"  总 Token 消耗: {agg.get('total_tokens', 0):,}")
    lines.append("")

    for suite in run.get("suites", []):
        lines.append(f"--- {suite['suite_name']} ---")
        m = suite["metrics"]
        lines.append(f"  TSR: {m['utility_rate']:.2f}%  ASR: {m['attack_success_rate']:.2f}%  "
                     f"Defense: {m['defense_success_rate']:.2f}%")
        o = suite["overhead"]
        lines.append(f"  Tokens: Prompt={o['prompt_tokens']:,}  Completion={o['completion_tokens']:,}  "
                     f"Total={o['total_tokens']:,}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("  报告由 DSCG Web Dashboard 自动生成")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    return Response(
        report_text,
        mimetype="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=report_{run_id}.txt"
        }
    )


@app.route("/api/report/<run_id>/html")
def get_html_report(run_id: str):
    """返回 HTML 格式报告"""
    with _store_lock:
        run = runs_store.get(run_id)
    if not run:
        result_file = DASHBOARD_RESULTS_DIR / run_id / "overall_results.json"
        if result_file.exists():
            with open(result_file, "r") as f:
                run = json.load(f)
    if not run:
        return jsonify({"error": "Run not found"}), 404

    return jsonify(run)


# =============================================
# 启动
# =============================================
if __name__ == "__main__":
    import socket

    port = int(os.environ.get("PORT", 8888))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    # ---- 检测容器网络环境 ----
    is_docker = os.path.exists("/.dockerenv")
    container_hostname = socket.gethostname()

    # 尝试获取容器 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        container_ip = s.getsockname()[0]
        s.close()
    except Exception:
        container_ip = "127.0.0.1"

    # ---- 打印启动信息 ----
    print("=" * 60)
    print("  🔐 DSCG - Agent 安全评测台")
    print("=" * 60)

    if is_docker:
        print(f"\n  📦 检测到 Docker 容器环境")
        print(f"     容器 ID: {container_hostname}")
        print(f"     容器 IP: {container_ip}")
        print(f"     服务端口: {port}")
        print()
        print("  ⚠️  Docker 环境访问说明:")
        print("  " + "-" * 52)
        print()
        print("  方式 1 - VSCode Ports 面板 (推荐):")
        print(f"    1. 打开 VSCode 底部面板: Ctrl+J")
        print(f"    2. 切换到 'PORTS' 标签页")
        print(f"    3. 点击 'Forward a Port' 按钮")
        print(f"    4. 输入端口号: {port}")
        print(f"    5. 确保该端口的 'Visibility' 设为 'Public'")
        print(f"    6. 在本地浏览器访问: http://localhost:{port}")
        print()
        print(f"    如果仍然报 403，说明你本地 {port} 端口被占用,")
        print("    在 PORTS 面板中右键该端口 → Change Port → 换一个本地端口")
        print()
        print("  方式 2 - 命令行直接测试 (容器内):")
        print(f"    python3 -c \"import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:{port}').status)\"")
        print()
        print("  方式 3 - 命令行 SSH 隧道:")
        print(f"    ssh -L {port}:localhost:{port} user@<容器宿主机>")
    else:
        print(f"\n  🌐 访问地址: http://localhost:{port}")
        print(f"  🌐 网络访问: http://{container_ip}:{port}")

    print(f"  📁 结果目录: {DASHBOARD_RESULTS_DIR}")
    print(f"  🐛 Debug 模式: {'开启' if debug else '关闭'}")
    print()
    print("  按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
