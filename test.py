import os
from pathlib import Path
import openai

import json
from pydantic import BaseModel
from typing import List, Dict, Any
from agentdojo import types as ad_types
from agentdojo import agent_pipeline, functions_runtime,logging, benchmark, attacks
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


QWEN_MODELS = {
    "qwen-flash-2025-07-28": "qwen-flash"
}

MODEL_NAMES.update(QWEN_MODELS)



# 定义 JSON 结构
class ActionModel(BaseModel):
    thought: str
    tool_name: str
    parameters: Dict[str, Any]

class ActionSequenceModel(BaseModel):
    actions: List[ActionModel]


class JsonActionExecutor(agent_pipeline.BasePipelineElement):
    def __init__(self, llm: agent_pipeline.OpenAILLM):
        self.llm = llm

    def generate_actionSequences(self, prompt):
        pass

    def query(self, query, runtime, env, messages, extra_args):

        json_instruction = (
            "\n\nYou MUST respond with a JSON object in the following format:\n"
            "{\"actions\": [{\"thought\": \"reasoning\", \"tool_name\": \"function_name\", \"parameters\": { ... }}]}\n"
            "Do not output anything other than the JSON."
        )
        
        new_messages = list(messages)
        
        # --- 修改部分：安全地更新 System Message ---
        # print("="*100)
        # print(type(new_messages)) #! class: lsit
        # print(new_messages)
        # print("="*100)

        if new_messages and new_messages[0]["role"] == "system":
            # 1. 使用工具函数安全获取原始文本内容
            original_text = ad_types.get_text_content_as_str(new_messages[0]['content'])
            
            #TODO
            #! 拼接新的指令:原来的system_prompt+json_instruction
            updated_text = original_text + json_instruction
            
            # 3. 重新创建一个 System Message 对象替换旧的
            new_messages[0] = ad_types.ChatSystemMessage(
                role="system",
                content=[ad_types.text_content_block_from_string(updated_text)]
            )

            # print("="*100)
            # print(new_messages[0])
            # print("="*100)
            # print(new_messages)
            # print("="*100)
            # x = input()

        # 2. 调用 LLM
        dummy_runtime = functions_runtime.FunctionsRuntime()
        # 注意：这里接收返回的消息时也要注意结构
        _, _, _, [*_, response_msg], _ = self.llm.query(query, dummy_runtime, env, new_messages, extra_args)
        
        # print("="*100)
        # print(response_msg)
        # print("="*100)
        # x = input()
        content = ad_types.get_text_content_as_str(response_msg['content'])
        print(f"\n[LLM Generated JSON]:\n{content}")

        try:
            clean_content = content.replace("```json", "").replace("```", "").strip()
            data = ActionSequenceModel.model_validate_json(clean_content)
            
            import uuid # 建议在文件开头导入
            ad_tool_calls = []
            for action in data.actions:
                # 添加一个随机的 call id，防止框架在校验格式时报错
                call_id = f"call_{uuid.uuid4().hex[:8]}" 
                
                ad_tool_calls.append(functions_runtime.FunctionCall(
                    function=action.tool_name,  
                    args=action.parameters,
                    id=call_id 
                ))

            assistant_msg = ad_types.ChatAssistantMessage(
                role="assistant",
                content=[ad_types.text_content_block_from_string(f"Thinking: {data.actions[0].thought}")],
                tool_calls=ad_tool_calls
            )
            # print("="*100)
            # print(f"assistant_msg:\n{assistant_msg}")
            
            # 将新生成的助手消息加入列表
            updated_messages = [*messages, assistant_msg]

            print("="*100)
            print("成功提取 ActionSequenceModel，将 Assistant 消息返回给框架")
            print(updated_messages)
            print("="*100)

            # --- 修改核心点：直接返回，不再调用 ToolsExecutor ---
            # 这样消息列表的最后一条就是带有 tool_calls 的 assistant_msg
            return query, runtime, env, updated_messages, extra_args

        except Exception as e:
            # 异常处理部分保持您的原样即可
            print(f"JSON 解析或执行失败: {e}")
            error_msg = {
                "role": "assistant",
                "content": [{"type": "text", "text": f"Error parsing JSON: {str(e)}"}],
                "tool_calls": [] 
            }
            updated_messages = [*messages, error_msg]
            print("="*100)
            print("处理发生错误")
            print(updated_messages)
            print("="*100)
            # x = input()
            return query, runtime, env, updated_messages, extra_args



def make_qwen_json_pipeline(model_id: str):
    client = openai.OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    llm = agent_pipeline.OpenAILLM(client, model_id, temperature=0.0, reasoning_effort=None)
    llm.name = model_id

    # 创建我们的自定义执行器
    json_executor = JsonActionExecutor(llm)

    pipeline = agent_pipeline.AgentPipeline([
        agent_pipeline.SystemMessage(load_system_message(None)), 
        agent_pipeline.InitQuery(),
        json_executor  # 这里直接处理了 生成JSON + 解析 + 执行工具
    ])
    
    pipeline.name = f"{llm.name}-json-mode"
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
    logdir = Path("./test_logs")
    logdir.mkdir(parents=True, exist_ok=True)

    print(f"开始实验 - 模型: {model_id}, 攻击: {attack_name if run_attack else '无'}")

    for suite_name in suites:
        print(f"\n正在测试套件: {suite_name}...")
        
        # A. 构建 Pipeline
        pipeline = make_qwen_json_pipeline(model_id)       
        
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
        utility_score = sum(utility_results.values()) / len(utility_results)
        print(f"[{suite_name}] 可用性 (Utility): {utility_score:.2%}")

        if run_attack:
            security_results = results["security_results"]
            security_score = sum(security_results.values()) / len(security_results)
            print(f"[{suite_name}] 安全性 (Security): {security_score:.2%}")
            
            # 安全性得分 0% 意味着模型每次都中了注入攻击
            # 安全性得分 100% 意味着模型成功忽略了所有注入指令


if __name__ == "__main__":
    # 确保设置了环境变量
    if "DASHSCOPE_API_KEY" not in os.environ:
        print("错误: 请先设置 DASHSCOPE_API_KEY")
    else:
        # 使用 cyclopts 或直接运行
        # 这里演示直接调用
        main(model_id="qwen-flash-2025-07-28", suites=["workspace"], run_attack=True)