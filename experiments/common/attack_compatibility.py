"""Read-only checks for native attack requirements on the selected task scope."""


def check_attack_compatibility(suite, attack_name: str,
                               user_task_ids: list[str], injection_task_ids: list[str]) -> dict | None:
    """Describe an unsupported whole group, or return None when it can run.

    Match native ToolKnowledgeAttack.get_tools_sequence: inspect each selected
    injection task's ground truth in a fresh default environment. Exceptions
    from ground_truth are genuine preparation errors and deliberately propagate.
    """
    if attack_name != 'tool_knowledge' or not injection_task_ids:
        return None
    affected = []
    for task_id in injection_task_ids:
        try:
            environment = suite.load_and_inject_default_environment({})
            calls = suite.injection_tasks[task_id].ground_truth(environment)
            if any(call.placeholder_args is None for call in calls):
                affected.append(task_id)
        except Exception as exc:
            exc._baseintent_execution_stage = 'attack_compatibility'
            exc._baseintent_task_id = task_id
            raise
    if not affected:
        return None
    return {
        'reason_code': 'missing_placeholder_args',
        'injection_task_ids': affected,
        'planned_pairs': len(user_task_ids) * len(injection_task_ids),
    }
