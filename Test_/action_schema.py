# action_schema.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class Action(BaseModel):
    tool: str = Field(..., description="工具名称，如 'write_file'")
    args: Dict[str, Any] = Field(..., description="工具参数字典")
    reasoning: Optional[str] = Field(None, description="可选：该动作的理由")

class ActionPlan(BaseModel):
    actions: List[Action] = Field(..., description="按顺序执行的动作列表")