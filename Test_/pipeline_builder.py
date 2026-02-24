# pipeline_builder.py
from agentdojo.agent_pipeline import AgentPipeline
from agentdojo import get_environment, load_tasks
from .planner import ActionPlanner
from .sanitizer import ArgumentSanitizer
from .enforcer import PolicyEnforcer
from .executor import ActionExecutor

def build_staged_pipeline(
    main_llm,
    quarantined_llm,
    security_policy_engine,
    task_suite: list[str] = ["workspace"]
):
    env = get_environment(task_suite)
    tools = env.get_tools()
    tools_runtime = FunctionsRuntime(tools)  # 假设 FunctionsRuntime 可从 tools 构建

    return AgentPipeline([
        ActionPlanner(main_llm, tools),
        ArgumentSanitizer(quarantined_llm),
        PolicyEnforcer(security_policy_engine),
        ActionExecutor(tools_runtime),
    ])