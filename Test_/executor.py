from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.functions_runtime import FunctionsRuntime
from .action_schema import ActionPlan

class ActionExecutor(BasePipelineElement):
    def __init__(self, tools_runtime: FunctionsRuntime):
        self.tools_runtime = tools_runtime

    def query(self, query, runtime, env, messages, extra_args):
        plan: ActionPlan = extra_args.get("approved_action_plan")
        if not plan:
            return query, runtime, env, messages, extra_args

        outputs = []
        for action in plan.actions:
            try:
                result = self.tools_runtime.call_function(action.tool, **action.args)
                outputs.append(str(result))
            except Exception as e:
                outputs.append(f"Error in {action.tool}: {e}")

        final_output = "\n".join(outputs)
        extra_args["final_output"] = final_output
        return query, runtime, env, messages, extra_args