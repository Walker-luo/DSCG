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


### Ablation Study

- myFrame
🏆 总体评测得分汇总:
👉 [workspace] 整体可用性 (Utility): 67.14%
👉 [workspace] 攻击成功率 (ASR): 0.00%
👉 [workspace] 整体安全性 (Defense Rate): 100.00%

💰 系统开销评估 (Overhead):
👉 任务 Input Tokens: 4992944.0
👉 任务 Output Tokens: 117728.0
👉 任务总计 Tokens: 5110672.0

💰 安全模型开销评估 (Overhead):
👉 Sec Input Tokens: 2169648.0
👉 Sec Output Tokens: 189894.0
👉 Sec Tokens: 2359542.0



- No SandBox

🏆 总体评测得分汇总:
👉 [workspace] 整体可用性 (Utility): 68.10%
👉 [workspace] 攻击成功率 (ASR): 0.48%
👉 [workspace] 整体安全性 (Defense Rate): 99.52%

💰 系统开销评估 (Overhead):
👉 任务 Input Tokens: 5083574.0
👉 任务 Output Tokens: 108086.0
👉 任务总计 Tokens: 5191660.0

💰 安全模型开销评估 (Overhead):
👉 Sec Input Tokens: 3118935.0
👉 Sec Output Tokens: 147879.0
👉 Sec Tokens: 3266814.0


- NO SecurityChecker (and HistoryTracker)

🏆 总体评测得分汇总:
👉 [workspace] 整体可用性 (Utility): 67.14%
👉 [workspace] 攻击成功率 (ASR): 5.24%
👉 [workspace] 整体安全性 (Defense Rate): 94.76%

💰 系统开销评估 (Overhead):
👉 任务 Input Tokens: 5179706.0
👉 任务 Output Tokens: 106469.0
👉 任务总计 Tokens: 5286175.0

💰 安全模型开销评估 (Overhead):
👉 Sec Input Tokens: 0.0
👉 Sec Output Tokens: 0.0
👉 Sec Tokens: 0.0

