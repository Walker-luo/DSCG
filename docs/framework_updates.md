# v3.5.3 当前交接

更新时间：2026-10-27。本文记录当前实现与限制，历史过程从[阶段报告索引](../workshop/completed/README.md)查阅；详细实验状态以[DV_STATE](../DV_STATE.md)为准。

## 本版实际采用的内容

| 部分 | 当前状态 |
| --- | --- |
| 默认策略 | `static-task-v352`／DSCG_v3.5.3；先静态任务视图，再全局工具授权；显式legacy保留单次对照 |
| 主规划／L3 | 区分来款与出款、计划与真实执行，最终答复保留完整字段；static共享编号／后续读取对照，审计并列任务及相关成功事实；风险元数据和严格判决保留 |
| 两阶段L2 | 现有静态提取补充交付字段、独立推荐条件和费用口径；原请求保留，视图不授予权限、不证明完成 |
| L1与执行 | 保留有限银行投影、来源封装、整批检查、Monitor与一次性票据；未采用隔离延后或标记拆分候选 |
| 读取分流 | `sink-free-read-v4`：授权、参数有效的public/internal、sink=none读取固定免审，其他调用审计 |
| 诊断 | 保留输入哈希／实际采样设置；静态任务视图输出失败新增固定field/rule定位，不存L2原始回复 |

普通任务循环：L2编译→主模型候选→L2整批检查→固定免审或L3→Monitor／票据→工具执行→L1规划视图。显式委托先经原中介准备读取，再编译完整有效任务；普通工具结果不能新增任务权限。最终文本无独立动作审计。

## 验证与遗留问题

本轮已默认启用static；Qwen四臂共244例＋4例消融，247有效／1 API错误。共同60例成功29→39，最终攻击ASR0/38；banking仅1/10，低于旧默认2/10，不能称银行问题已解决。详见[阶段报告](../workshop/completed/v353_optimization_20261027.md)。专项结果与历史正式结果分开；未增加完成性闸门、自动恢复、重试、参数修补或新模型阶段。

最新正式v3.5.3结果与v3.5.2共同1119键／1116有效，成功727→741：banking净少20、Slack净少5、travel净增39，原生ASR2→0。L1模式同时变化，不能作单因素因果结论；专项静态视图收益不能替代正式成绩。见[最新分析](../analysis/v3-5-3.md)。

- 正式结果中banking u4／u6有权限无候选，u15退款授权改善但实际完成仍差；Slack u13私信已恢复，u11第二频道仍误拒，travel候选／年份和最终交付仍有缺口。静态视图不保证任务完成或参数正确。
- 正式28例静态协议失败为19引用／9条件关系，与专项中的1例剩余引用失败属于不同范围，不混用分母。
- static的CLI／Dashboard NoL2、NoChecker已打通，非off路由仍要求L2／L3；baseline默认legacy走原生循环，历史候选继续保留各自限制。
- 本轮202项集成与AgentDyn相关49项、Node49项通过；相关旧版本／默认／夹具断言已适配。旧I3仍有5失败／5错误，不能称全套通过。
- SDK重试关闭不代表原生generation无重试；已记录失败后又成功的调用尚未统一投影为基础设施错误，成本与效用分母需单列复核。
- CLI投影默认off是本轮前已存在设置，factory/API仍projected；本轮在线四臂显式统一off。读取规则仍为sink-free-read-v4。
- 工具级控制不提供对象／参数硬授权，不能认证事实或保证最终回答无污染。E0 pending、I3 partial、I2 locked。

操作入口：[配置](model_tool_configuration.md) · [测试](benchmark.md) · [诊断](qwen_utility.md) · [Dashboard](dashboard.md)。

## 历史入口

[v3.5.1正式复盘](../workshop/archive/v351_analysis_20261026.md) · [117例分型](../workshop/completed/v351_tsr_diagnosis_20261026.md) · [v3.5.1优化报告](../workshop/completed/v35_optimization_20261026.md) · [v3.4.1优化](../workshop/completed/v34_utility_optimization_20261025.md) · [双后端接线](../workshop/completed/dual_benchmark_20261018.md) · [L1投影](../workshop/completed/l1_projection_20261013.md) · [早期平台](../workshop/completed/dashboard_v22_20261013.md)。历史默认值、预算和成绩只适用于各自阶段。
