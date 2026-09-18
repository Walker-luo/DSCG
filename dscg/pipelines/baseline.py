import os
from pathlib import Path
# import cyclopts
import json
import csv
from pathlib import Path

#统计token
from dscg.paths import RESULTS_DIR
from dscg.model_config import (
    ModelConfig,
    create_openai_client,
    resolve_model_config,
)
from dscg.token_tracking import TokenTrackerClient

from agentdojo import agent_pipeline, functions_runtime, logging, benchmark, attacks
from agentdojo.task_suite import get_suite
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.models import MODEL_NAMES

from agentdojo.benchmark import TaskResults
from agentdojo.functions_runtime import FunctionCall, FunctionReturnType
# 核心：手动触发 Pydantic 模型的重新构建，解析内部引用
try:
    TaskResults.model_rebuild()
except Exception as e:
    print(f"提醒：TaskResults 重构过程中出现小插曲（可能已处理）: {e}")




def make_openai_compatible_pipeline(
    model_id: str | None = None,
    ad_defense=None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key_env: str | None = None,
    config_path: str | Path | None = None,
    model_config: ModelConfig | None = None,
):
    """
    构建一个原始的 AgentDojo Pipeline，支持任意 OpenAI-compatible 模型。

    API key 和 base URL 可直接传入，也可通过 DSCG_MAIN_* 环境变量配置。
    """
    config = model_config or resolve_model_config(
        model_id,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        api_key_env=api_key_env,
        config_path=config_path,
        prefix="DSCG_MAIN",
    )
    client = create_openai_client(config)

    tracked_client = TokenTrackerClient(client)

    MODEL_NAMES.update({config.model_id: config.model_id})
    
    #! 非openai模型  reasoning_effort=None 查看README
    llm = agent_pipeline.OpenAILLM(
        tracked_client, config.model_id, temperature=0.0, reasoning_effort=None
    )
    llm.name = config.model_id


    if ad_defense:
        pipeline = agent_pipeline.AgentPipeline.from_config(
            agent_pipeline.PipelineConfig(
                llm=llm,
                model_id=config.model_id,
                defense=ad_defense,
                system_message_name=None,
                system_message=None,
            )
        )

    else:
        # 构建标准的 AgentDojo 循环
        # InitQuery -> LLM -> ToolsExecutionLoop (ToolsExecutor + LLM)
        tools_loop = agent_pipeline.ToolsExecutionLoop([
            agent_pipeline.ToolsExecutor(), 
            llm
        ])

        pipeline = agent_pipeline.AgentPipeline([
            agent_pipeline.SystemMessage(load_system_message(None)), # 标准系统提示词
            agent_pipeline.InitQuery(),
            llm,
            tools_loop
        ])
    
    # 给 pipeline 命名，方便日志记录
    pipeline.name = f"{llm.name}_{ad_defense}" if ad_defense else llm.name
    pipeline.dscg_model_config = config.public_dict()
    return pipeline, tracked_client


# Backwards-compatible name retained for existing callers.
make_qwen_original_pipeline = make_openai_compatible_pipeline


def main(
    model_id: str | None = None,
    # suites: list[str] = ["workspace", "banking"],
    suites: list[str] = ["workspace"],
    run_attack: bool = True,
    defense: str = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    provider: str | None = None,
    api_key_env: str | None = None,
    config_path: str | Path | None = None,
):
    """
    针对千问 Agent 的安全性实验脚本
    """
    attack_name = "important_instructions"  # 使用 AgentDojo 预定义的注入攻击
    logdir = RESULTS_DIR / "baseline"
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}, 攻击: {attack_name if run_attack else '无'}, 防御：{defense if defense else None}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        # A. 构建 Pipeline
        pipeline, tracked_client = make_openai_compatible_pipeline(
            model_id,
            ad_defense=defense,
            api_key=api_key,
            base_url=base_url,
            provider=provider,
            api_key_env=api_key_env,
            config_path=config_path,
        )


        
        # B. 加载套件和攻击载荷
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks 数量: {len(user_task_ids)}")
        print(f"总计 Injection Tasks 数量: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, pipeline)

        selected_users = user_task_ids[:2] 
        # selected_injections = injection_task_ids[:6]
        selected_injections = injection_task_ids[:2]
        
        # C. 运行基准测试并记录日志
        with logging.OutputLogger(str(logdir)):
            if run_attack:
                # 运行包含注入攻击的测试
                results = benchmark.benchmark_suite_with_injections(
                    pipeline,
                    suite,
                    attack,
                    logdir,
                    force_rerun=True,
                    user_tasks = selected_users,
                    injection_tasks = selected_injections
                )
            else:
                # 仅运行基础能力测试
                results = benchmark.benchmark_suite_without_injections(
                    pipeline,
                    suite,
                    logdir,
                    force_rerun=True,
                    user_tasks = selected_users,
                )


        # D. 输出结果分析
        utility_results = results["utility_results"]
        security_results = results.get("security_results", {})

        # 1. 确保目录存在 (避免 FileNotFoundError)
        output_dir = logdir / pipeline.name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义各类文件保存路径
        report_file_path = output_dir / f"{suite_name}_report.txt"
        csv_file_path = output_dir / f"{suite_name}_detailed_results.csv"
        summary_file_path = output_dir / f"{suite_name}_summary.json"

        # ==========================================
        # 2. 构造结构化数据列表 (用于画图)
        # ==========================================
        structured_records = []
        for task_key, util_status in utility_results.items():
            user_task_id = task_key[0]
            injection_task_id = task_key[1] if len(task_key) > 1 else "None"
            
            # AgentDojo 原生定义: True 代表执行了恶意指令(攻击成功)，False 代表安全
            attack_success = security_results.get(task_key, False) if run_attack else None
            defense_success = not attack_success if run_attack else None

            structured_records.append({
                "suite_name": suite_name,
                "model_id": model_id,
                "attack_type": attack_name if run_attack else "None",
                "user_task_id": user_task_id,
                "injection_task_id": injection_task_id,
                "utility_success": bool(util_status),        # 是否完成用户任务
                "attack_success": attack_success,            # 是否被黑客攻破
                "defense_success": defense_success           # 是否防御成功 (画图常用)
            })

        # 3. 计算聚合得分 (Summary)
        utility_score = sum(utility_results.values()) / len(utility_results) if utility_results else 0
        security_score = sum(security_results.values()) / len(security_results) if run_attack and security_results else 0
        defense_score = 1.0 - security_score if run_attack else 1.0

        prompt_tokens = tracked_client.total_prompt_tokens 
        completion_tokens = tracked_client.total_completion_tokens
        total_tokens = tracked_client.get_total_tokens()

        # ...
        # 💡 修改 3：在你的 summary_data 中加入 Token 统计节点



        summary_data = {
            "suite_name": suite_name,
            "pipeline_name": pipeline.name,
            "metrics": {
                "utility_rate": utility_score,
                "attack_success_rate": security_score,
                "defense_success_rate": defense_score
            },
            "task_counts": {
                "total_tasks": len(utility_results),
                "utility_passed": sum(utility_results.values()),
                "attacked_tasks": len(security_results)
            },
            "overhead": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
        }

        # 4. 写入文件 (TXT, CSV, JSON)
        # 4.1 保存供人类阅读的 TXT 报告
        with open(report_file_path, "w", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"Pipeline: {pipeline.name} | Model: {model_id}\n")
            f.write(f"📊 [{suite_name}] 任务详细执行报告\n")
            f.write("="*50 + "\n")

            for record in structured_records:
                util_str = "✅ 成功 (True)" if record["utility_success"] else "❌ 失败 (False)"
                
                if run_attack:
                    sec_str = "🛡️ 防御成功 (True)" if record["defense_success"] else "⚠️ 被攻破 (False)"
                    f.write(f"📌 [用户任务]: {record['user_task_id']:<25} | [注入攻击]: {record['injection_task_id']:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str:<15} | 安全性 (Security): {sec_str}\n")
                else:
                    f.write(f"📌 [用户任务]: {record['user_task_id']:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str}\n")
                f.write("-" * 50 + "\n")

            f.write("\n🏆 总体评测得分汇总:\n")
            f.write(f"👉 [{suite_name}] 整体可用性 (Utility): {utility_score:.2%}\n")
            if run_attack:
                f.write(f"👉 [{suite_name}] 攻击成功率 (ASR): {security_score:.2%}\n")
                f.write(f"👉 [{suite_name}] 整体安全性 (Defense Rate): {defense_score:.2%}\n")
            f.write("\n💰 系统开销评估 (Overhead):\n")
            f.write(f"👉 任务 Input Tokens: {prompt_tokens:.1f}\n")
            f.write(f"👉 任务 Output Tokens: {completion_tokens:.1f}\n")
            f.write(f"👉 任务总计 Tokens: {total_tokens:.1f}\n")
            f.write("="*50 + "\n\n")

        # 4.2 保存用于画图和数据分析的 CSV 详细表格
        if structured_records:
            with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=structured_records[0].keys())
                writer.writeheader()
                writer.writerows(structured_records)

        # 4.3 保存聚合数据的 JSON (方便后续写脚本对比多模型的表现)
        with open(summary_file_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=4, ensure_ascii=False)

        # 写完文件后，在控制台给个提示
        print(f"✅ [{suite_name}] 测试完成！")
        print(f"📄 文本报告: {report_file_path}")
        print(f"📊 数据表格(用于画图): {csv_file_path}")
        print(f"📈 得分汇总: {summary_file_path}\n")



if __name__ == "__main__":
    main(
        model_id=os.getenv("DSCG_MAIN_MODEL_ID", "qwen3-max"),
        suites=["workspace"],
        run_attack=True,
        defense="spotlighting_with_delimiting",
    )
