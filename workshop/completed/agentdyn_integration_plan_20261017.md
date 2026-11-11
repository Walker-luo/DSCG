# AgentDyn 全流程接入（2026-10-17）

状态：工程接入与离线验收已完成；真实模型效果留待服务器实验。依据本对话已批准计划。只实现基准接入，不新增防御机制或有效性主张。

- 独立 `ipi-agentdyn`，固定上游 `5353cf7615b135cace8d07c8f12dac53a16b6db3`；原 `ipi` 和用户结果保留。
- 新入口仅 shopping/github/dailylife；共享目录、来源与字节锁定、全部工具风险元数据。
- 复用 full/partial、clean/baseline、预检/cohort/reuse；新协议和目录身份拒绝旧基准缓存。
- 网页实验/报告/历史/导出统一接入；旧历史可读，不补造基准身份或跨任务分母。
- 离线和固定模拟agent覆盖真实工具/OTP/终态与原生判定，无付费模型调用。
- 完整Python/Node回归、独立代码审查、文档、保护清单和研究侧回报；未验证TSR/ASR/攻击强度。

原始日志与实施账本：`workshop/artifacts/20261017_agentdyn_integration/`。交付与限制见 [接入报告](./agentdyn_integration_20261017.md)；TSR/ASR/攻击强度、图形浏览器人工验收及真实E0不在本轮完成范围。
