import os
from pathlib import Path
import csv

from agentdojo import logging, benchmark, attacks
from agentdojo.task_suite import get_suite
from models import make_qwen_newFrame_pipeline
import json
from qwen_origin import make_qwen_original_pipeline


def main(
    model_id: str = "qwen-flash-2025-07-28",
    sec_model_id: str = "qwen3.5-flash",
    # suites: list[str] = ["workspace", "banking"],
    suites: list[str] = ["workspace"],
    run_attack: bool = True,
    origin = False,
    defense: str = None
):
    """
        model_id: 执行的llm的id
        sec_model_id: 审计的模型id，可以使用小模型替代
        suites: 测试的场景
        run_attack: 是否进行攻击，测试安全性，默认true
        origin: 是否只使用原始模型
        defense: agentdojo自带的防御机制包括："tool_filter", "transformers_pi_detector", "spotlighting_with_delimiting"等
    """



    attack_name = "important_instructions"  # 使用 AgentDojo 预定义的注入攻击
    logdir = Path("./logs")
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}, 审计模型：{sec_model_id}, 攻击: {attack_name if run_attack else '无'}, 防御: {defense if defense else '无'}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        if origin:
            pipeline = make_qwen_original_pipeline(model_id, ad_defense=defense) if defense else make_qwen_original_pipeline(model_id)

        else:
            pipeline = make_qwen_newFrame_pipeline(model_id, sec_model_id)       
        
        # 加载套件和攻击
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks 数量: {len(user_task_ids)}")
        print(f"总计 Injection Tasks 数量: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, pipeline)

        # selected_users = user_task_ids[:3] 
        selected_injections = injection_task_ids[:6]
        
        # 运行基准测试并记录日志
        with logging.OutputLogger(str(logdir)):
            if run_attack:
                results = benchmark.benchmark_suite_with_injections(
                    pipeline,
                    suite,
                    attack,
                    logdir,
                    force_rerun=False,
                    # user_tasks = selected_users,
                    injection_tasks = selected_injections,
                    verbose= True
                )
            else:
                results = benchmark.benchmark_suite_without_injections(
                    pipeline,
                    suite,
                    logdir,
                    force_rerun=False,
                    # user_tasks = selected_users,
                    injection_tasks = selected_injections
                )

        # 结果分析
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
            }
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

    # 确保设置了环境变量
    if "DASHSCOPE_API_KEY" not in os.environ:
        print("错误: 请先设置 DASHSCOPE_API_KEY")
    else:
        # 使用 cyclopts 或直接运行
        # 这里演示直接调用
        main(model_id="qwen3-max", sec_model_id = "qwen3.5-plus", suites=["workspace"], run_attack=True,
        origin= True,
        defense="spotlighting_with_delimiting")

