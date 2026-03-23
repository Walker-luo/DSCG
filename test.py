import os
from pathlib import Path
from agentdojo.default_suites.v2.suites import get_suite
from agentdojo.scripts import benchmark
from agentdojo import attacks
from agentdojo.logging import Logger
from agentdojo.utils import logging

# ==========================================
# 1. 引入 AgentDojo 的防御加载器
# ==========================================
from agentdojo.defenses import load_defense

# [保留你的 make_qwen_original_pipeline 函数完全不变]
# def make_qwen_original_pipeline(model_id: str, sec_model = None): ...

def main(
    model_id: str = "qwen-max",
    suites: list[str] = ["workspace"],
    run_attack: bool = True,
    defense_name: str = "tool_filter"  # 💡 新增：允许传入内置防御名称（如 None 则为裸奔）
):
    """
    针对千问 Agent 的安全性实验脚本 (已无缝接入 AgentDojo 内置防御)
    """
    attack_name = "important_instructions"
    
    # 💡 优化：根据是否加载了防御，动态修改日志目录，防止跑分结果被相互覆盖
    base_log_path = "./logs"
    if defense_name:
        logdir = Path(f"{base_log_path}/{model_id}_{defense_name}")
    else:
        logdir = Path(f"{base_log_path}/{model_id}_no_defense")
        
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}")
    print(f"攻击: {attack_name if run_attack else '无'}")
    print(f"防御策略: {defense_name if defense_name else '无 (裸奔)'}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        # A. 构建原始 Pipeline
        pipeline = make_qwen_original_pipeline(model_id)       
        
        # ==========================================
        # 2. 核心修改点：动态挂载内置防御
        # ==========================================
        if defense_name:
            # 从 AgentDojo 注册表中加载对应的防御机制
            defense = load_defense(defense_name)
            # 将防御机制强行包裹在你的 Qwen 管道外层
            pipeline = defense.apply(pipeline)
            print(f"[*] 已成功挂载防御策略: {defense_name}")
        
        # B. 加载套件和攻击载荷
        suite = get_suite("v1.2", suite_name)
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks: {len(user_task_ids)}")
        print(f"总计 Injection Tasks: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, pipeline)

        # selected_users = user_task_ids[:3] 
        selected_injections = injection_task_ids[:6]
        
        # C. 运行基准测试并记录日志
        with logging.OutputLogger(str(logdir)):
            if run_attack:
                results = benchmark.benchmark_suite_with_injections(
                    pipeline,
                    suite,
                    attack,
                    logdir,
                    force_rerun=True,
                    # user_tasks = selected_users,
                    injection_tasks = selected_injections
                )
            else:
                results = benchmark.benchmark_suite_without_injections(
                    pipeline,
                    suite,
                    logdir,
                    force_rerun=True,
                    # user_tasks = selected_users,
                    injection_tasks = selected_injections
                )