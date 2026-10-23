"""Initialize an incomplete AgentDyn result schema before native cache reads.

The pinned AgentDyn benchmark references FunctionCall in TaskResults without
making it available to Pydantic's rebuild namespace. This repairs the type in
memory only; native loader, scores and trace bytes remain unchanged.
"""
from agentdojo import benchmark


def ensure_native_cache_model_ready():
    task_results = benchmark.TaskResults
    if getattr(task_results, '__pydantic_complete__', True):
        return
    from agentdojo.functions_runtime import FunctionCall
    task_results.model_rebuild(_types_namespace={'FunctionCall': FunctionCall})
