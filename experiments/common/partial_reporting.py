"""Compact run reports and bounded failure excerpts; no model calls or rescoring."""

import json
import os
from tempfile import NamedTemporaryFile
from pathlib import Path
from urllib.parse import quote

from dscg.benchmark_catalog import benchmark_identity, get_backend, get_suites
from dscg.task_diagnostics import load_task_trace
from experiments.common.task_paths import trace_path


MAX_EXCERPTS = 6
MAX_EXCERPT_CHARS = 800


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block["content"] for block in content
                         if isinstance(block, dict) and block.get("type") == "text"
                         and isinstance(block.get("content"), str))
    return ""


def _excerpt(kind: str, pointer: str, text: str, *, start: int = 0) -> dict:
    start = max(0, start)
    end = min(len(text), start + MAX_EXCERPT_CHARS)
    return {"kind": kind, "source_pointer": pointer, "text": text[start:end],
            "start_char": start, "end_char": end, "original_chars": len(text),
            "truncated": start > 0 or end < len(text)}


def _read_excerpts(path: Path) -> tuple[str, list[dict], bool]:
    try:
        raw = load_task_trace(path)
    except FileNotFoundError:
        return "trace_missing", [], False
    except (OSError, ValueError):
        return "trace_unreadable", [], False
    if not isinstance(raw, dict) or not isinstance(raw.get("messages"), list):
        return "trace_unreadable", [], False

    messages = [(i, message) for i, message in enumerate(raw["messages"])
                if isinstance(message, dict)]
    excerpts = []
    if raw.get('dscg_diagnostics_status') in ('missing','corrupt','invalid_reference','incomplete'):
        excerpts.append(_excerpt('diagnostic_error','/dscg_diagnostics',raw['dscg_diagnostics_status']))
    task_error = bool(raw.get("error"))
    if task_error:
        excerpts.append(_excerpt("task_error", "/error", str(raw["error"])))
    if isinstance(raw.get('dscg_termination'),dict):
        excerpts.append(_excerpt('framework_failure','/dscg_termination',
            json.dumps(raw['dscg_termination'],ensure_ascii=False)))
    for action in raw.get('dscg_action_ledger',[]):
        if action.get('blocked_by'):
            excerpts.append(_excerpt('module_block','/dscg_action_ledger',
                json.dumps({k:action[k] for k in ('call_id','tool_name','blocked_by','block_reason') if k in action},ensure_ascii=False)))
            break

    # Prefer actionable diagnostics. Selection is observational, not causal.
    errors = [(i, message) for i, message in messages
              if message.get("role") == "tool" and message.get("error")]
    for i, message in errors[-2:]:
        excerpts.append(_excerpt("tool_error", f"/messages/{i}/error", str(message["error"])))
    assistants = [(i, message) for i, message in messages if message.get("role") == "assistant"]
    final_text = [(i, _content_text(message.get("content"))) for i, message in assistants]
    final_text = [(i, text) for i, text in final_text if text]
    if final_text:
        i, text = final_text[-1]
        excerpts.append(_excerpt("last_assistant", f"/messages/{i}/content", text,
                                 start=max(0, len(text) - MAX_EXCERPT_CHARS)))
    calls = [(i, message["tool_calls"]) for i, message in assistants if message.get("tool_calls")]
    for i, tool_calls in calls[-2:]:
        excerpts.append(_excerpt("recent_tool_calls", f"/messages/{i}/tool_calls",
                                 json.dumps(tool_calls, ensure_ascii=False)))

    injections = raw.get("injections")
    payloads = [value for value in injections.values() if isinstance(value, str) and value.strip()] \
        if isinstance(injections, dict) else []
    # Match the entire payload, including common serialized string forms.
    # Never guess a malicious span from keywords or an auditor's opinion.
    for i, message in messages:
        if message.get("role") != "tool":
            continue
        text = _content_text(message.get("content"))
        match = next((pos for payload in payloads
                      for needle in (payload, json.dumps(payload, ensure_ascii=False)[1:-1], repr(payload)[1:-1])
                      if (pos := text.find(needle)) >= 0), None)
        if match is not None:
            excerpts.append(_excerpt("payload_overlap", f"/messages/{i}/content", text,
                                     start=max(0, match - 80)))
            break
    return "available" if excerpts else "no_relevant_messages", excerpts[:MAX_EXCERPTS], task_error


def collect_suite_report(base_dir: Path, suite_dir: Path, summary: dict, records: list[dict], suite) -> dict:
    """Use this invocation's completed suite data, never stale summaries on disk."""
    selection = summary["task_selection"]
    attack = selection["attack"] or "none"
    attacked = summary["attack_kind"] != "none"
    cases = []
    diagnostics = {(e['user_task_id'], e['injection_task_id']): e
                   for e in summary.get('task_error_diagnostics', []) if e['stage'] != 'goal_preflight'}
    preflight_errors = [e for e in summary.get('task_error_diagnostics', []) if e['stage'] == 'goal_preflight']

    def add_case(user, injection, utility, security, status, failure_types):
        trace = trace_path(suite_dir, str(user), attack, injection if attacked else None)
        case = {
            "attack": attack, "suite": summary["suite_name"], "model_id": summary["model_id"],
            "user_task_id": user, "injection_task_id": injection if attacked else None,
            "attack_kind": summary["attack_kind"], "security_definition": summary["security_definition"],
            "failure_types": failure_types, "utility_success": utility, "attack_success": security,
            "sample_status": status, "trace_path": trace.relative_to(base_dir).as_posix(),
            "trace_exists": trace.is_file(), "excerpts": [],
        }
        detail = diagnostics.get((user, injection if attacked else None))
        if detail is not None:
            case['tool_arguments_error'] = detail
        # Reporting must not read outside the run directory, including symlinks.
        if trace.resolve().is_relative_to(base_dir.resolve()):
            excerpt_status, excerpts, task_error = _read_excerpts(trace)
            case.update(excerpt_status=excerpt_status, excerpts=excerpts)
            if task_error:
                if "task_error" not in case["failure_types"]:
                    case["failure_types"].append("task_error")
        else:
            case["excerpt_status"] = "trace_outside_run"
        user_task = suite.user_tasks.get(user)
        injection_task = suite.injection_tasks.get(injection) if attacked else None
        for key, value in [("task_prompt", getattr(user_task, "PROMPT", "")),
                           ("attack_goal", getattr(injection_task, "GOAL", ""))]:
            text = str(value)
            case[key] = text[:400]
            case[f"{key}_truncated"] = len(text) > 400
        cases.append(case)

    seen = set()
    for record in records:
        user, injection = record["user_task_id"], record["injection_task_id"]
        seen.add((user, injection if attacked else None))
        failures = ["task_error"] if record.get("execution_error") else []
        if record["utility_success"] is False:
            failures.append("tsr_failure")
        if record.get('framework_termination',{}).get('kind') == 'framework_failure':
            failures.append('framework_failure')
        if record["attack_success"] is True:
            failures.append("asr_success")
        if attacked and record["attack_success"] is None:
            failures.append("asr_unavailable")
        if failures:
            add_case(user, injection, record["utility_success"], record["attack_success"],
                     record["sample_status"], failures)
    for user in selection["user_task_ids"]:
        for injection in (selection["injection_task_ids"] if attacked else [None]):
            if (user, injection) not in seen:
                add_case(user, injection, None, None, "infrastructure_error", ["result_missing"])

    for error in preflight_errors:
        trace = trace_path(suite_dir, error['user_task_id'], 'none', None, goal=True)
        cases.append({'attack': attack, 'suite': summary['suite_name'], 'model_id': summary['model_id'],
                      'user_task_id': None, 'injection_task_id': error['user_task_id'], 'phase': 'goal_preflight',
                      'failure_types': ['goal_preflight_error'], 'sample_status': 'infrastructure_error',
                      'utility_success': None, 'attack_success': None,
                      'trace_path': trace.relative_to(base_dir).as_posix(), 'trace_exists': trace.is_file(),
                      'excerpt_status': 'not_scored_preflight', 'excerpts': [], 'tool_arguments_error': error})

    unavailable = sum(record["attack_success"] is None for record in records) if attacked else 0
    missing = sum("result_missing" in case["failure_types"] for case in cases)
    return {
        "attack": attack, "suite": summary["suite_name"], "summary": summary,
        "summary_path": (suite_dir / "summary.json").relative_to(base_dir).as_posix(),
        "status": "partial" if missing or unavailable or preflight_errors or any(r.get("execution_error") for r in records) else "completed",
        "tsr_failures": sum("tsr_failure" in case["failure_types"] for case in cases),
        "asr_successes": sum("asr_success" in case["failure_types"] for case in cases),
        "metric_unavailable": unavailable + missing,
        "goal_preflight_errors": len(preflight_errors),
        "task_errors": sum("task_error" in case["failure_types"] for case in cases),
        "framework_failures": sum('framework_failure' in case['failure_types'] for case in cases),
        "cases": cases,
    }


def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _link(path: str) -> str:
    return f"[{_cell(path)}]({quote(path, safe='/')})"


def _rate(passed: int, denominator: int, *, enabled: bool = True) -> str:
    if not enabled:
        return "N/A（无攻击）"
    return f"{passed / denominator:.2%} ({passed}/{denominator})" if denominator else "N/A (0/0)"


def write_run_overview(base_dir: Path, attack_names: list[str], suites: list[str],
                       run_records: list[dict], suite_reports: list[dict], *, model_id=None,
                       task_scope='partial', routing_summary=None, selection_report=None) -> tuple[Path, Path]:
    """Write run summaries and failure index without altering native metrics."""
    backend = get_backend()
    summary_path = base_dir / "summary.md"
    detail_path = base_dir / "failure_cases.jsonl"
    metadata = ('overall_results.json' if task_scope == 'dashboard' else
                'run_manifest.json' if (base_dir/'run_manifest.json').exists() else
                'attack_manifest.json' if (base_dir/'attack_manifest.json').exists() else
                'screened_run_manifest.json' if (base_dir/'screened_run_manifest.json').exists() else
                'benchmark_plan.json')
    reports = {(report["attack"], report["suite"]): report for report in suite_reports}
    runs = {(record["attack"], record.get('failed_suite')): record for record in run_records}
    cases = [dict(case) for report in suite_reports for case in report["cases"]]
    for run in run_records:
        if run["status"] == "error":
            cases.append({"attack": run["attack"], "suite": run.get("failed_suite"),
                          "model_id": model_id, "user_task_id": None, "injection_task_id": None,
                          "failure_types": ["run_error"], "sample_status": "infrastructure_error",
                          "error_type": run["error_type"], "trace_path": None, "trace_exists": False,
                          "excerpt_status": "run_aborted", "excerpts": [],
                          "source_path": metadata,
                          **({'execution_error': run['execution_error']} if 'execution_error' in run else {}),
                          **({'api_error': run['api_error']} if 'api_error' in run else {})})
    for line, case in enumerate(cases, 1):
        case.update(schema_version="dscg.partial-failure.v2", benchmark=benchmark_identity(), case_id=f"F{line:04d}", detail_line=line)
    with detail_path.open("w", encoding="utf-8") as stream:
        for case in cases:
            stream.write(json.dumps(case, ensure_ascii=False) + "\n")

    title = {'full': '全量评测摘要', 'screened': '筛选目标评测摘要（全部用户任务）',
             'dashboard': '网页评测摘要',
             'partial_screened': '小批量筛选目标评测摘要（每场景前 3 个用户，原前 3 个注入目标内筛选）'}.get(task_scope, '小批量评测摘要')
    if task_scope == 'full' and set(suites) != set(backend.suites):
        title = '所选场景全任务评测摘要'
    lines = [f"# {title}", "", f"模型：{_cell(model_id)}；运行目录：{_cell(base_dir.name)}。", "",
             f"基准：{_cell(backend.label)}；revision={benchmark_identity()['revision']}。", "",
             f"本次场景：{', '.join(suites)}。", "",
             "TSR 失败 = utility=false；防御失败 = 原生 ASR=true。缺失指标和运行错误单列，不当作攻击成功或防御成功。",
             "ASR 为当前基准原生 predicate；DoS 的 ASR=not utility，不能和 targeted ASR 合并。",
             "TSR/ASR 分母分别是已返回效用结果数/有效布尔安全结果数；预检不计入这些分母。Token 含主模型和审计模型，沿用各场景 cost_scope。", "",
             "| Attack | 场景 | 状态 | 完成/计划 | TSR | ASR | 防御成功率 | Token 主/审计/合计 | TSR失败 | ASR成功 | 指标缺失 | 任务错误 | 框架失败 | 场景数据 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    if selection_report is not None:
        exclusions = selection_report.get('fliter_excluded', [])
        checks = selection_report.get('goal_checks', [])
        failures = [item for item in checks if item.get('status') == 'failed']
        errors = [item for item in checks if item.get('status') == 'error']
        selection_lines = ['',
            f"筛选：原有目标 {selection_report.get('targets_before', 0)}，fliter 排除 {len(exclusions)}，"
            f"GOAL 失败 {len(failures)}、错误 {len(errors)}，保留 {selection_report.get('targets_retained', 0)}，"
            f"移除任务对 {selection_report.get('removed_pairs', 0)}；GOAL {'开启' if selection_report.get('goal_enabled') else '关闭'}"
            f"（{_cell(selection_report.get('goal_pipeline') or 'none')}）。", '']
        excluded = [(item, 'fliter 排除') for item in exclusions]
        excluded += [(item, 'GOAL 失败（不计分）') for item in failures]
        excluded += [(item, 'GOAL预检错误跳过（不计分）') for item in errors]
        if selection_report.get('goal_enabled'):
            selection_lines += ['当前框架参与GOAL筛选，不同框架可能产生不同测试集合，不能直接比较不同分母原始成功率。', '']
        if excluded:
            selection_lines += ['| 场景 | 注入目标 | 排除原因 | 移除任务对 |', '| --- | --- | --- | --- |']
            for item, reason in excluded:
                if item.get('error_code'):
                    reason += ' / ' + str(item['error_code'])
                selection_lines.append('| ' + ' | '.join('**' + _cell(value) + '**' for value in
                    (item['suite'], item['injection_task_id'], reason, item.get('removed_pairs', '—'))) + ' |')
            selection_lines.append('')
        table_index = next(i for i, line in enumerate(lines) if line.startswith('| Attack |'))
        lines[table_index:table_index] = selection_lines
    for attack in attack_names:
        for suite in suites:
            report = reports.get((attack, suite))
            if report is None:
                run = runs.get((attack, suite), runs.get((attack, None), {}))
                if run.get('status') == 'unsupported':
                    status = f"unsupported ({run['reason_code']})"
                    completed = f"0/{run['planned_pairs']}"
                else:
                    status = f"run_error ({run.get('error_type', 'unknown')})" if run.get("status") == "error" else "not_reported"
                    completed = "N/A"
                row = [attack, suite, status, completed, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "—"]
            else:
                data = report["summary"]
                counts = data["task_counts"]
                total, valid = counts["total_tasks"], counts["attacked_tasks"]
                attacked = data["attack_kind"] != "none"
                main_tokens = data["overhead"].get("total_tokens", 0)
                sec_tokens = data.get("sec_overhead", {}).get("total_tokens", 0)
                status = report["status"] + (" (DoS)" if data["attack_kind"] == "dos" else "")
                task_errors = str(report['task_errors'])
                if report.get('goal_preflight_errors'):
                    task_errors += f" (GOAL预检错误={report['goal_preflight_errors']})"
                row = [attack, suite, status, f"{total}/{counts['planned_tasks']}",
                       _rate(counts["utility_passed"], counts.get("utility_valid", total)),
                       _rate(report["asr_successes"], valid, enabled=attacked),
                       _rate(valid - report["asr_successes"], valid, enabled=attacked),
                       f"{main_tokens}/{sec_tokens}/{main_tokens + sec_tokens}",
                       report["tsr_failures"], report["asr_successes"], report["metric_unavailable"],
                       task_errors, report.get('framework_failures',0), _link(report["summary_path"])]
            # Links are already Markdown-escaped.
            lines.append("| " + " | ".join(_cell(value) for value in row[:-1]) + " | " + row[-1] + " |")
    lines.extend(["", "各场景 Token 统计范围："])
    for report in suite_reports:
        data = report["summary"]
        new_cost = data.get("invocation_cost", {})
        new_tokens = (new_cost.get("overhead", {}).get("total_tokens", 0) + new_cost.get("sec_overhead", {}).get("total_tokens", 0)) if new_cost else 'unknown'
        lines.append(f"- {_cell(report['attack'])} / {_cell(report['suite'])}：{_cell(data.get('cost_scope', 'unknown'))}；本次新增 Token={new_tokens}。")
    lines.extend(["", "## 失败与缺失案例索引", "",
                  f"详情：{_link('failure_cases.jsonl')}（每行一个案例，最多 {MAX_EXCERPTS} 个片段，每片最多 {MAX_EXCERPT_CHARS} 字符）。",
                  "片段仅为排查线索，不证明失败原因或恶意动作执行；不复制完整轨迹、系统提示或注入字典。",
                  "source_pointer 定位原 JSON；content 片段的字符范围针对按顺序拼接的文本块。", ""])
    if not cases:
        lines.append("无失败或指标缺失案例。")
    else:
        lines.extend(["| 案例/详情行 | Attack | 场景 | 用户/注入任务 | 类型 | 原始位置 | 片段状态 |",
                      "| --- | --- | --- | --- | --- | --- | --- |"])
        labels = {"tsr_failure": "TSR失败", "asr_success": "ASR成功（防御失败）",
                  "asr_unavailable": "ASR缺失/无效", "result_missing": "结果缺失",
                  "task_error": "任务运行错误", "run_error": "运行中断", "framework_failure": "框架决策失败",
                  "goal_preflight_error": "GOAL预检错误（不计分）"}
        for case in cases[:10]:
            task = f"{case.get('user_task_id') or '—'} / {case.get('injection_task_id') or 'none'}"
            location = case.get("trace_path") or case.get("source_path")
            types = ", ".join(labels[kind] for kind in case["failure_types"])
            if case.get("error_type"):
                types += f" ({case['error_type']})"
            row = [f"{case['case_id']} / {case['detail_line']}", case["attack"], case.get("suite") or "—", task, types]
            lines.append("| " + " | ".join(_cell(value) for value in row) + " | " + _link(location) + " | " + case["excerpt_status"] + " |")
        if len(cases) > 10:
            lines.extend(['', f'仅展示前10个入口，共{len(cases)}个案例；其余请查看failure_cases.jsonl。'])
    lines.extend(['', '## L3路由', '',
                  '[查看运行级路由汇总](l3_router_summary.md) · [结构化统计](l3_router_summary.json)',
                  '路由汇总区分未校准、无候选与缺失记录；shadow不实际免审，selective实际节省Token仍未知。'])
    if routing_summary is not None:
        t = routing_summary['totals']
        modes = sorted({r['configuration']['mode'] for r in routing_summary['configurations']})
        savings = t['shadow_would_save_tokens']
        lines.extend(['', f"实际模式：{', '.join(modes) or '未知'}；已记录候选批次{t['candidate_batches']}，适用{t['eligible_batches']}，原公开免审{t['original_public_bypass_batches']}，新增实际免审{t['actual_bypass_batches']}；shadow有效模拟节省Token：{savings if savings is not None else '未知'}。"])
    lines.extend(['', f'完整运行配置与范围见 {_link(metadata)}；保留场景summary.json、CSV和原始任务JSON用于核查。'])
    goal_tokens = 0
    goal_unknown = 0
    for check in (selection_report or {}).get('goal_checks', []):
        cost = check.get('cost')
        models = cost.get('models') if isinstance(cost, dict) else None
        if not isinstance(models, list) or not models:
            goal_unknown += 1
            continue
        for phases in models:
            if not isinstance(phases, dict):
                goal_unknown += 1
                continue
            for counters in phases.values():
                if not isinstance(counters, dict):
                    goal_unknown += 1
                    continue
                tokens = counters.get('total_tokens')
                if type(tokens) is int:
                    goal_tokens += tokens
                else:
                    goal_unknown += 1
                if counters.get('missing_usage_calls') or counters.get('failed_calls'):
                    goal_unknown += 1
    scored_tokens = 0
    scored_unknown = 0
    for report in suite_reports:
        cost = report['summary']
        if not isinstance(cost, dict):
            scored_unknown += 1
            continue
        if not any(isinstance(cost.get(name), dict) and 'total_tokens' in cost[name]
                   for name in ('overhead', 'sec_overhead')):
            scored_unknown += 1
        for name in ('overhead', 'sec_overhead'):
            counters = cost.get(name, {})
            if not isinstance(counters, dict):
                scored_unknown += 1
                continue
            tokens = counters.get('total_tokens')
            if type(tokens) is int:
                scored_tokens += tokens
            elif counters:
                scored_unknown += 1
        for phases in cost.get('api_accounting', {}).values():
            if not isinstance(phases, dict):
                scored_unknown += 1
                continue
            for counters in phases.values():
                if not isinstance(counters, dict):
                    scored_unknown += 1
                    continue
                if counters.get('missing_usage_calls') or counters.get('failed_calls'):
                    scored_unknown += 1
    aborted_groups = {(run['attack'], run.get('failed_suite')) for run in run_records
                      if run.get('status') == 'error' and (run['attack'], run.get('failed_suite')) not in reports}
    scored_unknown += len(aborted_groups)
    cost_summary = dict(scope='recorded scored costs (per-suite cost_scope) plus all GOAL checkpoint costs', scored={'known_total_tokens': scored_tokens, 'unknown_usage_records': scored_unknown},
                        goal={'known_total_tokens': goal_tokens, 'unknown_usage_records': goal_unknown},
                        combined={'known_total_tokens': scored_tokens + goal_tokens,
                                  'unknown_usage_records': scored_unknown + goal_unknown})
    if (selection_report or {}).get('goal_enabled'):
        lines.extend(['', f'GOAL检查成本（不计分）：已知Token={goal_tokens}；未知usage记录={goal_unknown}。',
                      f'计分＋GOAL记录成本合计已知Token={scored_tokens + goal_tokens}；未知usage记录={scored_unknown + goal_unknown}。',
                      '计分成本沿用各场景cost_scope；GOAL包含已有checkpoint记录，续跑缓存与本次新增成本须分别核对。'])
    structured_path = base_dir / 'summary.json'
    # The GOAL stage checkpoints into this file before measurement begins.
    structured = json.loads(structured_path.read_text()) if structured_path.exists() else {}
    structured.update(schema_version='dscg.run-summary.v1', benchmark=benchmark_identity(),
                      model_id=model_id, task_scope=task_scope, attacks=list(attack_names), suites=list(suites),
                      run_records=run_records, suite_reports=[{k: v for k, v in report.items() if k != 'cases'}
                                                            for report in suite_reports],
                      configuration_path=metadata, failure_cases_path='failure_cases.jsonl', cost_summary=cost_summary,
                      routing_summary_path='l3_router_summary.json' if routing_summary is not None else None)
    if selection_report is not None:
        structured['selection_report'] = {**structured.get('selection_report', {}), **selection_report}
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=base_dir,
                                prefix='.run-summary-', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(structured, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, structured_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path, detail_path
