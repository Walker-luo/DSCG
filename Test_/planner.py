import json
from typing import List, Tuple
from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.types import ChatMessage
from .action_schema import ActionPlan

class ActionPlanner(BasePipelineElement):
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools

    def _build_system_prompt(self) -> str:
        tool_descs = []
        for tool in self.tools:
            params = ", ".join(f"{k}: {v.__name__}" for k, v in tool.parameters.items())
            tool_descs.append(f"- {tool.name}({params}): {tool.description}")
        return f"""你是一个任务规划器。请将用户请求分解为一系列工具调用。
可用工具：
{chr(10).join(tool_descs)}

输出必须是严格符合以下 JSON Schema 的对象：
{ActionPlan.model_json_schema()}
只输出 JSON，不要任何其他文本。"""

    def query(self, query: str, runtime, env, messages=[], extra_args={}) -> Tuple:
        system_prompt = self._build_system_prompt()
        user_msg = {"role": "user", "content": query}
        
        # 调用 LLM 生成 JSON（需模型支持 JSON 模式）
        response = self.llm.client.chat.completions.create(
            model=self.llm.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                user_msg
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_plan = response.choices[0].message.content
        try:
            action_plan = ActionPlan.model_validate_json(raw_plan)
            extra_args["raw_action_plan"] = action_plan
        except Exception as e:
            print(f"⚠️ 动作计划解析失败: {e}")
            action_plan = ActionPlan(actions=[])
            extra_args["raw_action_plan"] = action_plan

        return query, runtime, env, messages, extra_args