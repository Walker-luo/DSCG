# L1 结构化投影：当前边界与未验收项

当前实现见 [input_isolation.py](../dscg/input_isolation.py)、[l1_projection.py](../dscg/l1_projection.py)和[配置指南](../docs/model_tool_configuration.md)。版本与默认值跟随当前代码，不沿用早期提案的框架身份。

## 已实现边界

- `banking-monthly-spending-v1`仅覆盖明确的原生银行月支出任务与严格兼容返回，保留全部记录、原顺序及六个结构字段，省略subject。错误、歧义、不完整或不适用输入回退来源封装。
- 原始消息继续用于审计和记录；投影与来源标记都不认证事实或完整性，不提供对象／参数授权，也不新增模型调用。
- `off`、`shadow`、`projected`已实现；CLI默认off，factory/API保留projected。模式、适配器及边界参与有效配置绑定，改变策略使用新名称。
- AgentDyn没有新增投影profile；不能把网页handler按纯文本读取投影或凭名称免审。

## 尚未验收

更广原生返回格式、字段与引用保真、真实安全／效用／总成本对照仍需独立选择范围和验证。字符减少不是Token或费用节省证据，不因投影后缺少攻击词扩大L3免审。保持用户确认的任务源污染范围及研究侧未解锁机制边界。

原提案与有限实现记录见 [2026-10-13阶段报告](completed/l1_projection_20261013.md)及其原始归档。历史设计中的未实现状态和默认值不适用于当前代码；后续工作从 [DV_STATE.md](../DV_STATE.md)选择，不重新执行旧计划。
