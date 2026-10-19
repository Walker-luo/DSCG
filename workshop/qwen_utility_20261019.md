# Qwen banking / Slack 通用效用修正

状态：候选工程已完成；默认策略保持 legacy，真实模型验收待授权。[工程报告](./completed/qwen_utility_20261019.md)和[使用指南](../docs/qwen_utility.md)。本文件保留在pending目录，用于尚未完成的模型/效果验收，不是待重复实现的代码任务。

按用户批准计划执行：协议诊断与严格输出契约 → 宿主工具语义目录 → 独立来源语义候选。L1仅在模型对照支持时修改；本轮无付费调用，不运行正式clean/攻击。不是TSR恢复或研究闸门结论。

接口：`prompt_profile=legacy|protocol-v1|tool-semantics-v1|source-context-v1`，候选累积前一阶段改动。默认legacy保留原提示、目录、模型、路由和重试。候选绑定提示内容和目录协议版本；不同候选不能混用缓存或校准文件。

验证：离线协议类型/阻断/日志边界、目录来源及身份、CLI/API/cohort接线，两个环境完整Python回归及Node。未来同轮37项局部clean、97项全量clean和冻结cohort三攻击比较，由用户授权后另跑，不用模拟结果冒充模型效果。

## 执行账本

- 基点：e9b494e6c13fcc0d0fee9885f5eadbdc58147e85，workshop分支，开始时工作树干净。
- Ruling：在用户指定的现有checkout内工作，保留结果和环境；不创建新worktree。
- Ruling：语义提示改进作为显式候选，不替换默认。离线mock无法确认模型判断改善，遵守先验收再替换的停止条件。
- Ruling：所有本轮产物存放workshop/artifacts/20261019_qwen_utility/，覆盖技能默认workspace位置。
- 完成：协议诊断、三个候选、CLI/API/cohort/身份绑定、15项新离线测试、两个环境完整回归（511/515项，各1跳过）、Node45/45、文档。
- 待验收：候选输出协议稳定性、独立模型正反例、37项及97项clean和冻结cohort攻击；这些需要后续模型调用授权。没有证据支持修改L1，因此未改。
- 边界修正：RED暴露错误decision=list被归为MODEL_ERROR、无效工具metadata在新目录中解引用None；分别修正为INVALID_DECISION和unknown/critical，全部仍失败关闭。
