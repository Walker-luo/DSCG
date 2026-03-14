import os
from pathlib import Path

from agentdojo import logging, benchmark, attacks
from agentdojo.task_suite import get_suite
from models import make_qwen_json_pipeline


def main(
    model_id: str = "qwen-flash-2025-07-28",
    sec_model_id: str = "qwen3.5-flash",
    # suites: list[str] = ["workspace", "banking"],
    suites: list[str] = ["workspace"],
    run_attack: bool = True
):
    """
        model_id: 执行的llm的id
        sec_model_id: 审计的模型id，可以使用小模型替代
        suites: 测试的场景
        run_attack: 是否进行攻击，测试安全性，默认true
    """



    attack_name = "important_instructions"  # 使用 AgentDojo 预定义的注入攻击
    logdir = Path("./logs")
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}, 审计模型：{sec_model_id}, 攻击: {attack_name if run_attack else '无'}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        pipeline = make_qwen_json_pipeline(model_id, sec_model_id)       
        
        # 加载套件和攻击
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks 数量: {len(user_task_ids)}")
        print(f"总计 Injection Tasks 数量: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, pipeline)

        selected_users = user_task_ids[:3] 
        selected_injections = injection_task_ids[:3]
        
        # 运行基准测试并记录日志
        with logging.OutputLogger(str(logdir)):
            if run_attack:
                results = benchmark.benchmark_suite_with_injections(
                    pipeline,
                    suite,
                    attack,
                    logdir,
                    force_rerun=False,
                    user_tasks = selected_users,
                    injection_tasks = selected_injections,
                    verbose= True
                )
            else:
                results = benchmark.benchmark_suite_without_injections(
                    pipeline,
                    suite,
                    logdir,
                    force_rerun=False,
                    user_tasks = selected_users,
                    injection_tasks = selected_injections
                )

        # 结果分析
        utility_results = results["utility_results"]
        security_results = results.get("security_results", {})

        # 定义报告保存路径
        report_file_path =  f"{logdir}/{pipeline.name}/ourFrame.txt" 
        
        # 提前打开文件，在遍历过程中直接写入
        with open(report_file_path, "w", encoding="utf-8") as f:
            
            f.write("\n" + "="*50 + "\n")
            f.write(f"moddel_id:{model_id}, sec_model_id: {sec_model_id}\n")
            f.write(f"📊 [{suite_name}] 任务详细执行报告\n")
            f.write("="*50 + "\n")

            # 遍历输出每个具体任务的执行情况
            for task_key, util_status in utility_results.items():
                # task_key 是一个元组: (user_task_id, injection_task_id)
                user_task_id = task_key[0]
                injection_task_id = task_key[1] if len(task_key) > 1 else "None"
                
                # 格式化输出可用性
                util_str = "✅ 成功 (True)" if util_status else "❌ 失败 (False)"
                
                if run_attack:
                    # 获取对应的安全性结果
                    sec_status = security_results.get(task_key, False)
                    sec_str = "🛡️ 防御成功 (True)" if not sec_status else "⚠️ 被攻破 (False)"
                    
                    f.write(f"📌 [用户任务]: {user_task_id:<25} | [注入攻击]: {injection_task_id:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str:<15} | 安全性 (Security): {sec_str}\n")
                    f.write("-" * 50 + "\n")
                else:
                    f.write(f"📌 [用户任务]: {user_task_id:<25}\n")
                    f.write(f"   -> 功能性 (Utility): {util_str}\n")
                    f.write("-" * 50 + "\n")

            # 最后输出总体得分
            f.write("\n🏆 总体评测得分汇总:\n")
            utility_score = sum(utility_results.values()) / len(utility_results)
            f.write(f"👉 [{suite_name}] 整体可用性 (Utility): {utility_score:.2%}\n")

            if run_attack and len(security_results) > 0:
                security_score = sum(security_results.values()) / len(security_results)
                f.write(f"👉 [{suite_name}] 攻击成功率 (Security): {security_score:.2%}\n")
                f.write(f"👉 [{suite_name}] 整体安全性 (Security): {(1-security_score):.2%}\n")
                
            f.write("="*50 + "\n\n")
            
        # 写完文件后，在控制台给个提示
        print(f"✅ [{suite_name}] 测试完成！详细执行报告已保存至: {report_file_path}")





if __name__ == "__main__":

    # 确保设置了环境变量
    if "DASHSCOPE_API_KEY" not in os.environ:
        print("错误: 请先设置 DASHSCOPE_API_KEY")
    else:
        # 使用 cyclopts 或直接运行
        # 这里演示直接调用
        main(model_id="qwen3-max", sec_model_id = "qwen3.5-plus", suites=["workspace"], run_attack=True)

