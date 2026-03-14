import os
from pathlib import Path
import openai
import random
# import cyclopts

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



# 封装千问 API 适配器
def make_qwen_original_pipeline(model_id: str):
    """
    构建一个原始的 AgentDojo Pipeline，使用千问模型
    """
    client = openai.OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


    #! 添加千问模型
    QWEN_MODELS = {
        model_id: model_id
    }

    MODEL_NAMES.update(QWEN_MODELS)
    
    #! 非openai模型  reasoning_effort=None 查看README
    llm = agent_pipeline.OpenAILLM(client, model_id, temperature=0.0, reasoning_effort= None)
    llm.name = model_id


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
    pipeline.name = llm.name
    return pipeline


def main(
    model_id: str = "qwen-flash-2025-07-28",
    # suites: list[str] = ["workspace", "banking"],
    suites: list[str] = ["workspace"],
    run_attack: bool = True
):
    """
    针对千问 Agent 的安全性实验脚本
    """
    attack_name = "important_instructions"  # 使用 AgentDojo 预定义的注入攻击
    logdir = Path("./logs")
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}, 攻击: {attack_name if run_attack else '无'}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        # A. 构建 Pipeline
        pipeline = make_qwen_original_pipeline(model_id)       
        
        # B. 加载套件和攻击载荷
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks 数量: {len(user_task_ids)}")
        print(f"总计 Injection Tasks 数量: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, pipeline)

        selected_users = user_task_ids[:3] 
        selected_injections = injection_task_ids[:3]
        
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
                    injection_tasks = selected_injections
                )

        # D. 输出结果分析
        utility_results = results["utility_results"]
        security_results = results.get("security_results", {})

        # 定义报告保存路径
        report_file_path =  f"{logdir}/{pipeline.name}/origin.txt" 
        
        # 提前打开文件，在遍历过程中直接写入
        with open(report_file_path, "w", encoding="utf-8") as f:
            
            f.write("\n" + "="*50 + "\n")
            f.write(f"moddel_id:{model_id} \n")
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
        main(model_id="qwen3-max", suites=["workspace"], run_attack=True)