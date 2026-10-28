# DSCG Project State

> 2026-10-28（Asia/Shanghai）。当前 **DSCG_v3.5.4 / static-task-v354**。只保留现行机制、验证范围与遗留问题；历史报告不作为新的调用授权。

## 1. 工作区与当前任务

| 项目 | 状态 |
| --- | --- |
| 目录／分支／开始HEAD | `DSCG/`／`workshop`／`9020780d0f043d1373bd4a976b30d7208df9935c`（2026-10-27 22:01:17+08:00）；未切分支、暂存或提交 |
| 本次任务 | 按v3.5.3第5节实施协议／错误投影／规划审计优化，真实Qwen在线对照，保护ASR与travel、重点核对银行和Slack |
| 初始脏文件 | AGENTS.md、DV_STATE.md、analysis/v3-5-3.md；AGENTS和旧分析原样保留，状态在既有内容基础上更新 |
| 当前默认 | `static-task-v354`；显式`static-task-v352`保留v3.5.3策略／协议，legacy为单阶段对照；baseline默认legacy走原生循环 |
| 在线授权 | 仅真实qwen3.7-flash；主／授权／审计／GOAL均核对。当前任务允许必要新批次，不重开历史campaign或直接开全量 |

## 2. 当前机制

- **L1：**原始历史重建规划视图；有限银行月支出profile保留所有行和六个结构字段，其余来源封装。CLI off、factory/API projected，原始返回保留供审计／记录。
- **L2：**先提取片段ID静态视图，再编译全局动作工具布尔表、合并自动读取；宿主将已知ID映射逐字span，关系使用互斥对象分支。未知ID／非法结构失败封闭；无修补／回退／额外调用。原请求及原生定义仍为依据，视图不认证语义或条件。
- **规划／L3：**强调当前操作required／optional、独立步骤、当前频道与先前频道的区别；新付款日期须有依据。提示仍会被模型忽略。四字段审计保留实际参数、目的地／正文和有限成功证据，deny／abstain阻断。
- **任务源／Monitor：**保留中介准备读取、有限明确txt/md委托、冻结授权／目录、整批回执及一次性票据；普通返回不能新增任务权威，污染委托源仍在既有边界外。
- **读取／入口：**sink-free-read-v4范围不变；CLI router shadow、factory/API off，off仍审计非免审批次。static NoL2／NoChecker仅router off；full／partial／cohort／Dashboard共享工厂和原生评分。
- **错误投影：**共享读取器合并当前attempt后，对已记账API失败派生null标签；旧attempt不污染新attempt。原生评分／实际效果不改，旧持久汇总不回写；新投影策略绑定reuse身份。SDK retries0，原生generation仍可重试，未记账失败无法推断。
- **未新增：**host意图进度FSM、完成闸门、恢复、动态扩权、参数修补、对象／数据／参数硬授权或最终文本审计。

## 3. 最新实施与验证

- **v3.5.4专项：**5个冻结臂各62个同键任务，合计310次计分运行、62个不同任务键，305有效／5API错误；不是310个独立任务。旧默认与最终候选共同60有效成功40→43；banking4/12持平、Slack10/11→11/11、travel7/11→8/11，travel clean含合法控制9/10持平。有效攻击ASR0/37，2个最终候选错误保留未知。所有未采用／退步结果保留，详见[分析](analysis/v3-5-4.md)、[阶段报告](workshop/completed/v354_optimization_20261028.md)。
- **默认入口验证完成：**11例中10有效／1 API错误，成功8/10、有效攻击ASR0/7；两个原错误路径在新批次正常结束且未攻击成功，原错误／分母不替换。合计321计分运行／315有效／6错误／0未完成，62个不同键；另141 GOAL轨迹140有效／1错误，独立计账。4个组件probe共8次成功Qwen调用、13,969 tokens，不执行工具、不计入TSR／ASR覆盖。
- **Offline Regression：**最终AgentDojo776项，原有5失败／5错误／13跳过；AgentDyn780项，原有6失败／5错误／8跳过，额外失败为既有网页副作用夹具。与冻结旧源码核对无新增失败；Node49/49。独立Sol审查无可行动发现，不能据此证明语义质量。
- **正式历史结果：**v3.5.3共同1119键／1116有效，utility727→741，banking−20、Slack−5、travel+39，ASR2→0；L1配置差异与API错误保留，见[v3.5.3](analysis/v3-5-3.md)。本次不重标正式文件。
- **已关闭阶段：**[v3.5.3专项](workshop/completed/v353_optimization_20261027.md)248计分／消融、247有效／1错误，2,968 API尝试／2,966响应，8,252,464已知tokens；仅属其冻结源码与范围，不追加调用。更早逐例证据见[details](analysis/details.md)及[历史索引](workshop/completed/README.md)。

## 4. 未解决问题

| 问题 | 当前结论／边界 |
| --- | --- |
| banking整体TSR未改善 | u15攻击样例仍只更新地址、漏已有订单更新；新付款缺日期不应阻断可独立执行的更新。不能称已解决 |
| 日期与参数语义 | u6/K:6及clean仍有无依据日期且原生True；日历年份、费用／人数语义疑点继续单列，ASR0不认证参数正确 |
| Slack／travel波动 | u11第二频道在本批恢复，u13 clean、travel u3 clean与部分推荐仍退步；小样本不可外推正式全量 |
| 协议与语义 | 协议错误5→0不等于摘要正确；占位条件／额外付款解释已改提示并检查，但无语义认证 |
| 错误与成本 | API故障不作为安全成功；已记账失败统一投影，损坏／缺失记录和未知usage仍保留未知，历史持久汇总不回写 |
| 长请求／后端范围 | 原有2048提取上限及NoL2／纯读／受限host原协议边界保留；AgentDyn本轮只做离线共享代码回归，无新在线效能结论 |
| 研究门槛 | E0 pending、I3 partial（24有效／8范围缺口）、I2 locked；旧I3诊断失败不改，无新机制或关闭路线解锁 |

## 5. 证据与下一步

本轮产物均在`workshop/artifacts/20261028_v354_optimization/`：冻结源／hash、选择清单、原生轨迹、审计原文、API成本与错误、离线日志和核验。实际3,930 API尝试／3,923响应，11,104,437已知tokens；7次失败调用usage未知，不当0。正式results／download保持原样；最终验收、调用账及保护检查见阶段报告。

下一步优先定位银行已有订单更新为何未提出，评估只读展示已授权工具required／optional字段；先验证合法部分执行，不追逐猜日期的原生分数。日期依据与任务语义先明确；不引入进度FSM／恢复／动态授权。实施边界见[当前框架](docs/framework_updates.md)与兄弟仓库[technical_route.md](../research/technical_route.md)的当前状态链接；不修改研究决策、不重开关闭campaign。
