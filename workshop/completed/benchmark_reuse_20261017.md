# 三攻击typical与显式续跑

日期：2026-10-17。基准revision：`cee87b851e44d8c1a9d699eb6fd177ea965d817b`；开始时工作树干净，本次改动未提交。

## 行为

新typical为ignore_previous、important_instructions、tool_knowledge；injecagent仍可显式/all选择。默认partial108条，travel/banking/slack81条，full2847条；用户前缀、场景默认、原生评分与结果根不变。历史四攻击成绩与分母不改写。

full/partial CLI增加reuse，API增加reuse=False。要求原name与可核验目录；显式reuse覆盖DSCG_FORCE_RERUN，与显式force-rerun和清单导出互斥。未指定attack/suites时恢复原完整计划，旧四攻击继续四攻击；缺少根计划须显式原范围。新普通运行提前记录benchmark_plan，screened保留原requested/active分工。

共享实现先预检全部绑定，再备份汇总、保存兼容记录、补写已验证的新绑定并执行原生cache。所有已有manifest和完整raw保持原字节；不完整raw及侧车被native重跑前留快照。已完成的utility失败和原生接受的API错误不自动重试；损坏JSON仍走原错误路径。汇总覆盖原范围，成本仍区分历史与本次调用。

## 兼容边界

测量使用独立明确映射：对候选来源核对相同防御字节和native benchmark dispatch AST，并在续跑时继续匹配模型、任务、攻击、场景、工具元数据及有效控制。7个候选完整来源集合中接纳6个；一个未通过此核验，不借用预检资格放行。未知来源、运行时或配置差异拒绝。直接GOAL预检映射另行更新，仅补充本次等价入口变化。

新运行绑定agentdojo_defense。旧baseline缺字段时，须由与旧绑定相符的summary明确defense，或已验证的screened根记录提供证据；没有证据拒绝，不推定None。这可能阻止某些很早中断、尚无汇总的普通baseline目录升级续跑，应使用原代码或新name。

## 验证

产物：`workshop/artifacts/20261017_benchmark_reuse/`；精确命令、退出码、工作树、哈希与限制见validation.json。修改前原文和当前映射见 [归档](../archive/benchmark_reuse_20261017/README.md)。用户用法见 [完整指南](../../docs/benchmark.md#显式续跑示例)和[partial指南](../../docs/partial_benchmark.md#中断缓存与任务清单)。

- 初始391项；最终 `conda run -n ipi python -B -m unittest discover -s tests -v`：407/407，exit0。新续跑14项、cohort9项分别通过；全部为离线mock/native日志验证。
- 先RED后GREEN验证新接口和不完整轨迹保存。独立审阅发现两项并修复：原生防御未绑定（2项RED→GREEN），筛空cohort误比requested/active（1项RED→GREEN）。修复后全套再次407/407；无延期项。
- 帮助、文档命令解析、实际任务/攻击规模、源码兼容/拒绝、本地链接及归档哈希验证均记录到本次产物。只读/离线检查不调用真实服务。
- 旧结果文件、此前归档和dscg防御实现保留。此前已有的plan/report缺失链接单列，不重建历史材料；历史迁移快照不用于认证当前新增功能。

新增真实模型请求0、真实benchmark样本0。E0 pending、I3 partial、I2 locked及closed路线不变。下一步：用户更新服务器后按两份指南，以原name和相同配置选择reuse；无法核验证据的旧运行使用原代码续跑或新name重新测量。
