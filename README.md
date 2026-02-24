## Notice
- openai的模型会把`system message`修改为`developer message`, 在对应的位置修改，参考下列路径的`#TODO`
> [agentdojo/agent_pipeline/llms/openai_llm.py](
/home/luoyuxin/miniconda3/envs/myFrame/lib/python3.10/site-packages/agentdojo/agent_pipeline/llms/openai_llm.py)





## Result

`./logs`

- `injection_task_n`是**能力测试**：验证模型本身是否具备执行这个攻击动作的能力（不涉及任何欺骗）
- `user_task_n`是**防御测试**：不同的*n*代表不同的主线任务


### Qwen-flash
>![](./photo/qwen_flash_result_1.png)
- 可用性：58%
- 安全性：12%



