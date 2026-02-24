# enforcer.py
from agentdojo.agent_pipeline import BasePipelineElement
#! from agentdojo.base_security_policy_engine import BaseSecurityPolicyEngine
from .action_schema import ActionPlan

class PolicyEnforcer(BasePipelineElement):
    def __init__(self, security_policy_engine = None):
        self.security_policy_engine = security_policy_engine

    def query(self, query, runtime, env, messages, extra_args):
        plan: ActionPlan = extra_args.get("sanitized_action_plan")
        if not plan:
            return query, runtime, env, messages, extra_args

        # 实例化策略引擎（传入当前环境）
        if(self.security_policy_engine == None):
            print("security_policy_engine is None ==============================")
            return query, runtime, env, messages, extra_args

        policy_engine = self.security_policy_engine(env)

        approved_actions = []
        for action in plan.actions:
            # 检查工具是否被允许
            if policy_engine.is_tool_allowed(action.tool, action.args):
                approved_actions.append(action)
            else:
                print(f"🚫 动作被拒绝: {action.tool}({action.args})")
                # 可选择：中断流程 / 跳过该动作 / 抛出异常

        extra_args["approved_action_plan"] = ActionPlan(actions=approved_actions)
        return query, runtime, env, messages, extra_args