import json
import time
from typing import Sequence, Iterable, Callable, Any
import logging

from agentdojo import agent_pipeline, functions_runtime
from agentdojo import types as ad_types
# from agentdojo.models import KnownModelName

# 假设这些是你项目中已有的辅助函数
# from agentdojo.agent_pipeline import ... 

class JsonStreamPrivilegedLLM(agent_pipeline.BasePipelineElement):
    """ A pipeline element that generates action sequences(JSON) expressing the user query.

    Args:
        llm: the LLM to use to generate the sequences.
        security_policy: the policy used to check whether the action sequecnes is safe or not
    """

    def __init__(
        self,
        llm: agent_pipeline.BasePipelineElement,
        #TODO security_policy_engine: type[AgentDojoSecurityPolicyEngine],
        security_policy,
        # JSON 模式下不需要专门的 Prompt Generator 生成 Python 函数签名，
        # 但我们需要一个生成 JSON Schema 描述的 Generator
        system_prompt:str,
        max_attempts: int = 5,
    ) -> None:
        self.llm = llm
        self.security_policy_engine = security_policy
        self.max_attempts = max_attempts
        self.dummy_runtime = functions_runtime.FunctionsRuntime()

    def _parse_json_response(self, text: str) -> list[dict] | None:
        """尝试从 LLM 回复中提取并解析 JSON 列表"""
        try:
            # 处理可能的 Markdown 包裹 ```json ... ```
            clean_text = text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            actions = json.loads(clean_text)
            if isinstance(actions, list):
                return actions
            return None
        except json.JSONDecodeError:
            return None

    def execute_json_actions(
        self,
        actions: list[dict],
        env: functions_runtime.TaskEnvironment,
        runtime: functions_runtime.FunctionsRuntime
    ) -> tuple[str, list[tuple[functions_runtime.FunctionCall, Any]], str | None]:
        """
        逐个执行 JSON 动作流，并进行安全检查。
        """
        results_log = []
        tool_calls_record = []
        policy = self.security_policy_engine(env) # 初始化安全策略
        
        output_buffer = ""
        execution_error = None

        for i, action in enumerate(actions):
            tool_name = action.get("tool")
            args = action.get("args", {})

            if not tool_name:
                continue

            # 1. 安全检查 (Pre-execution Security Check)
            # 这里的 check 接口需要根据你具体的 Policy Engine 实现来调整
            # 假设接口是 policy.check(tool_name, args) -> bool or raise Exception
            try:
                # 模拟 CaMeL 的安全检查
                is_safe = True 
                if hasattr(policy, "check_tool_call"):
                     # 注意：这里需要构造一个临时的 FunctionCall 对象传给 Policy
                    temp_call = functions_runtime.FunctionCall(name=tool_name, arguments=args)
                    # 如果策略引擎返回 False 或抛出异常，视为拦截
                    if not policy.check_tool_call(temp_call):
                         raise RuntimeError(f"Security Policy Violation: Action '{tool_name}' blocked.")
            except Exception as e:
                execution_error = f"Security Error at step {i+1}: {str(e)}"
                break

            # 2. 获取并执行工具
            if tool_name not in runtime.functions:
                execution_error = f"Tool '{tool_name}' not found."
                break
            
            try:
                func = runtime.functions[tool_name]
                # 执行工具
                result = func.run(**args)
                
                # 记录结果
                tool_calls_record.append((functions_runtime.FunctionCall(name=tool_name, arguments=args), result))
                output_buffer += f"Step {i+1} [{tool_name}]: {str(result)}\n"
                
            except Exception as e:
                execution_error = f"Execution Error at step {i+1} ({tool_name}): {str(e)}"
                break

        return output_buffer, tool_calls_record, execution_error

    def query(
        self,
        query: str,
        runtime: functions_runtime.FunctionsRuntime,
        env=functions_runtime.EmptyEnv(),
        messages: Sequence[ad_types.ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple:
        
        # 1. 构造 System Prompt，指导模型输出 JSON
        # 这里简化了 Prompt，实际应用中需要动态生成工具 Schema
        tools_desc = "\n".join([f"- {name}: {f.description}" for name, f in runtime.functions.items()])
        
        system_instruction = (
            f"You are a helpful assistant. You must verify the user's request and execute necessary actions.\n"
            f"Available tools:\n{tools_desc}\n\n"
            f"IMPORTANT: You strictly reply with a JSON LIST of actions to execute sequentially.\n"
            f"Format: [{{\"tool\": \"tool_name\", \"args\": {{\"arg1\": \"value\"}}}}, ...]\n"
            f"Do not include any explanation, just the JSON."
        )

        privileged_messages = [
            ad_types.ChatSystemMessage(role="system", content=[ad_types.text_content_block_from_string(system_instruction)]),
            ad_types.ChatUserMessage(role="user", content=[ad_types.text_content_block_from_string(query)])
        ]

        attempts = self.max_attempts
        final_output = ""
        tool_calls_results = []
        
        # 2. 循环：生成 -> 解析 -> 执行 -> (出错则修正)
        while attempts > 0:
            # 调用 LLM (传入 dummy_runtime 避免原生 Function Calling)
            _, _, _, [*_, response_msg], _ = self.llm.query(
                query=query,
                runtime=self.dummy_runtime, 
                messages=privileged_messages
            )
            
            response_text = ad_types.get_text_content_as_str(response_msg["content"])
            actions_list = self._parse_json_response(response_text)

            # 如果解析失败，让模型重试
            if actions_list is None:
                error_msg = "Invalid JSON format. Please output a valid JSON list."
                privileged_messages.append(response_msg)
                privileged_messages.append(ad_types.ChatUserMessage(role="user", content=[ad_types.text_content_block_from_string(error_msg)]))
                attempts -= 1
                continue

            # 执行 JSON 动作流
            output_buffer, current_tool_results, error = self.execute_json_actions(actions_list, env, runtime)
            
            tool_calls_results.extend(current_tool_results)
            final_output += output_buffer

            if error:
                # 如果执行出错（安全拦截或工具报错），将错误喂回模型
                error_feedback = f"Execution stopped due to error: {error}. Please fix your plan and provide the JSON list again."
                privileged_messages.append(response_msg) # 把之前生成的 JSON 加入历史
                
                # 添加工具结果消息 (Tool Outputs)
                for call, res in current_tool_results:
                     privileged_messages.append(
                        ad_types.ChatToolResultMessage(
                            role="tool", 
                            tool_call=call, 
                            content=[ad_types.text_content_block_from_string(str(res))],
                            tool_call_id=None, error=None
                        )
                    )
                
                privileged_messages.append(ad_types.ChatUserMessage(role="user", content=[ad_types.text_content_block_from_string(error_feedback)]))
                attempts -= 1
            else:
                # 执行成功，跳出循环
                break

        # 3. 构造最终返回给用户的消息
        # 这里只返回最后的执行结果摘要
        final_assistant_msg = ad_types.ChatAssistantMessage(
            role="assistant",
            content=[ad_types.text_content_block_from_string(final_output or "Task completed.")],
            tool_calls=[tc for tc, _ in tool_calls_results]
        )
        
        updated_messages = [*messages, final_assistant_msg]

        return query, runtime, env, updated_messages, extra_args