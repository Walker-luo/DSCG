# v3.5.4 当前交接

更新：2026-10-28。当前状态见[DV_STATE](../DV_STATE.md)，结果见[v3.5.4专项](../analysis/v3-5-4.md)；最近正式全量复盘仍是[v3.5.3](../analysis/v3-5-3.md)。

| 部分 | 当前行为 |
| --- | --- |
| 默认 | `static-task-v354`；先片段ID静态视图，再冻结全局工具权限。`static-task-v352`保留v3.5.3逐字引用策略，legacy保留单次授权 |
| L2协议 | 宿主提供逐字片段及span；模型选ID，条件／非条件使用互斥分支。未知ID／非法字段失败封闭，不重试提取、不修补或回退 |
| 规划／L3 | 按当前操作原生required／optional字段规划；审计当前目标与先前已完成目标的区别，保留外发目的地／正文及实际参数检查。辅助视图不认证语义、事实或完成 |
| L1／执行 | 来源封装、有限银行投影、授权工具视图、整批检查、Monitor及一次性票据保留；原始返回继续用于审计和记录 |
| 读取 | `sink-free-read-v4`仍仅固定免审已授权／schema有效、read、public/internal、sink=none调用 |
| 错误分母 | 共享读取器按当前attempt已记账API失败派生null标签；原始等级／效果不变，旧持久汇总不回写。新策略绑定reuse身份，须新运行名 |

普通循环仍是L2编译→主模型候选→整批检查→固定免审或L3→Monitor→执行→L1视图。明确委托沿原有中介准备协议；污染任务源仍在既有支持边界外。NoL2／NoChecker仅允许router off；baseline为legacy／原生循环。

## 验证与限制

Qwen共同60有效样例成功40→43：banking攻击4/12持平、Slack10/11→11/11、travel7/11→8/11；travel clean含合法控制9/10持平。有效攻击ASR0/37，另2例API错误保留未知，不外推全量或保证。所有候选和错误保留于[阶段报告](../workshop/completed/v354_optimization_20261028.md)。

- **银行未解决：**u15仍漏已有订单更新；u6仍有无依据日期且原生判True，不能算参数正确。新付款真实缺日期应澄清。
- **Slack／travel仍有个例退步：**第二频道在本批恢复，u13 clean及部分推荐／最终交付仍失败。协议错误减少不代表语义正确。
- CLI L1默认off，factory/API仍projected；CLI router shadow、factory/API off；off仍有L3。采样保持原生，SDK retries0不代表端到端只发送一次。
- 已记账失败可投影；未记账／损坏证据仍不能推断成本或安全。没有完成闸门、恢复、动态扩权、对象／参数硬授权或最终文本审计。
- 离线完整套件仍有原有I3失败／错误及AgentDyn网页副作用夹具失败；E0 pending、I3 partial、I2 locked。

[配置](model_tool_configuration.md) · [评测](evaluation.md) · [诊断](qwen_utility.md) · [阶段历史](../workshop/completed/README.md)。
