from pathlib import Path

from agentdojo import attacks, benchmark, logging
from agentdojo.task_suite import get_suite
# from openai.types.chat import ChatCompletionReasoningEffort
from models import make_qwen_original_pipeline
import cyclopts



def main(
    model: str,
    use_original: bool = False, #! 采用原始模型对照
    ad_defense: str | None = None, 
    run_attack: bool = False,
    replay_with_policies: bool = False,
    suites: list[str] | None = None,
    q_llm: str | None = None,
    user_tasks: list[str] | None = None, #! 选择的task对应id
):
    """Example usage of the defense.


    Other newer models might work as well.

    Args:
        model: the model to use. like qwen-flash-2025-07-28
        use_original: whether to use the original model with tool calling API instead of CaMeL
        ad_defense: whether to use a defense from AgentDojo and which one. It must be used in conjunction with `--use-original`.
            Tested defenses are "tool_filter", "repeat_user_prompt", "spotlight_with_delimiting"
        run_attack: whether to run the attack (it uses AgentDojo's `important_instructions` attack)
        replay_with_policies: replay the run with the given model enforcing security policies. Note that the equivalent run (with same model and attack config)
            should have already been run.
        suites: which suites to run AgentDojo on (can be a list from `["workspace", "banking", "travel", "slack"]`)
        q_llm: what model to use as a quarantined llm. If None, the same as `model` is used.
    """

    attack_name = "important_instructions"

    suites = suites or ["workspace", "banking", "travel", "slack"]
    total_utility_results = []
    total_security_results = []
    logdir = Path("./logs")
    logdir.mkdir(parents=True, exist_ok=True)

    for suite_name in suites:
        tools_pipeline = make_qwen_original_pipeline(model_id= model)
        suite = get_suite("v1.2", suite_name)

        # 统计任务数量
        user_task_ids = list(suite.user_tasks.keys())
        injection_task_ids = list(suite.injection_tasks.keys())
        print(f"\n--- 套件统计 [{suite_name}] ---")
        print(f"总计 User Tasks 数量: {len(user_task_ids)}")
        print(f"总计 Injection Tasks 数量: {len(injection_task_ids)}")

        attack = attacks.load_attack(attack_name, suite, tools_pipeline)

        #! 选取部分任务，用于测试
        # selected_users = user_task_ids[:10] 
        # selected_injections = injection_task_ids[:10]

        with logging.OutputLogger(str(logdir)):
            if run_attack:
                results = benchmark.benchmark_suite_with_injections(
                    tools_pipeline,
                    suite,
                    attack,
                    logdir,
                    force_rerun=False,
                    # user_tasks = selected_users,
                    user_tasks=user_tasks,
                )
            else:
                results = benchmark.benchmark_suite_without_injections(
                    tools_pipeline,
                    suite,
                    logdir,
                    force_rerun=False,
                    # user_tasks = selected_users,
                    user_tasks=user_tasks,
                )


        utility_results = results["utility_results"]
        total_utility_results += utility_results.values()
        print(f"{suite_name} - utility: {sum(utility_results.values()) / len(utility_results.values())}")

        if run_attack:
            security_results = results["security_results"]
            total_security_results += security_results.values()
            print(f"{suite_name} - security: {sum(security_results.values()) / len(security_results.values())}")

    print(f"overall - utility: {sum(total_utility_results) / len(total_utility_results)}")
    if run_attack:
        print(f"overall - security: {sum(total_security_results) / len(total_security_results)}")


if __name__ == "__main__":
    main()
