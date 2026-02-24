import os
import openai
import time

from agentdojo import agent_pipeline, functions_runtime, logging, benchmark, attacks
from agentdojo.task_suite import get_suite
from agentdojo.agent_pipeline.agent_pipeline import load_system_message
from agentdojo.models import MODEL_NAMES

#! 添加千问模型

QWEN_MODELS = {
    "qwen-flash-2025-07-28": "qwen-flash"
}

MODEL_NAMES.update(QWEN_MODELS)

#! 执行过程中引入延迟，绕过某些API的频率限制
class Sleep(agent_pipeline.BasePipelineElement):
    def __init__(self, amount: int) -> None:
        super().__init__()
        self._amount = amount

    def query(
        self,
        query: str,
        runtime,
        env=functions_runtime.EmptyEnv(),
        messages=[],
        extra_args={},
    ) -> tuple:     
        if self._amount > 0:
            time.sleep(self._amount)
        return query, runtime, env, messages, extra_args



def make_qwen_pipeline_newFrame(model_id: str):
    """
    构建一个原始的 AgentDojo Pipeline，使用千问模型
    """
    client = openai.OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
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




def make_qwen_original_pipeline(model_id: str):
    """
    构建一个原始的 AgentDojo Pipeline，使用千问模型
    """
    client = openai.OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    
    #! 非openai模型  reasoning_effort=None 查看README
    llm = agent_pipeline.OpenAILLM(client, model_id, temperature=0.0, reasoning_effort= None)
    llm.name = model_id

    # 构建标准的 AgentDojo 循环
    # InitQuery -> LLM -> ToolsExecutionLoop (ToolsExecutor + LLM)
    tools_loop = agent_pipeline.ToolsExecutionLoop([
        agent_pipeline.ToolsExecutor(), 
        # Sleep(5),
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

