# 隔离 LLM 填充/验证参数
from typing import Any, Dict
from agentdojo.agent_pipeline import BasePipelineElement
import json
from .action_schema import ActionPlan

class ArgumentSanitizer(BasePipelineElement):
    def __init__(self, quarantined_llm):
        self.quarantined_llm = quarantined_llm  # 隔离 LLM（如更小、更安全的模型）

    def _sanitize_args(self, args: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """使用隔离 LLM 安全地解析模糊参数（如 '最近的文件' → 具体路径）"""
        if not any(isinstance(v, str) and ("模糊" in v or "最近" in v or "用户提到" in v) for v in args.values()):
            return args  # 无模糊参数，直接返回

        prompt = f"""你是一个参数澄清器。请将模糊参数转换为具体值。
工具: {tool_name}
原始参数: {args}
上下文: 用户正在操作文件系统。

输出必须是纯 JSON 对象，仅包含修正后的参数。"""
        
        response = self.quarantined_llm.client.chat.completions.create(
            model=self.quarantined_llm.model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return args  # 失败则保留原参数

    def query(self, query, runtime, env, messages, extra_args):
        plan: ActionPlan = extra_args.get("raw_action_plan")
        if not plan:
            return query, runtime, env, messages, extra_args

        sanitized_actions = []
        for action in plan.actions:
            clean_args = self._sanitize_args(action.args, action.tool)
            sanitized_actions.append(action.model_copy(update={"args": clean_args}))

        extra_args["sanitized_action_plan"] = ActionPlan(actions=sanitized_actions)
        return query, runtime, env, messages, extra_args