# Workshop 优化状态索引

当前运行框架为 **three-layer-v3.1**。目录按工程落实状态管理：基础方案已实施的文件归入 completed；仍需实现的新机制留在顶层。完成工程不等于实验目标或研究闸门全部通过。

## 已完成与归档

| 方案 / 阶段 | 已完成 | 尚未完成或未采用 |
| --- | --- | --- |
| [全量入口场景选择](./completed/full_suites_20261017.md) · [用法](../docs/full_benchmark.md#1-使用哪个入口) | full/partial共用--suites；full保留所选场景全部任务，兼容clean/cohort/导出；385项离线回归 | 场景子集不是四场景全量；无真实模型/费用收益测量 |
| [experiments/docs整理](./completed/experiments_docs_cleanup_20261017.md) · [当前实验入口](../experiments/README.md) | 退役8个旧文件、清理生成缓存、索引与文档去重；原始字节归档 | 不改变运行/评分；早期迁移快照校验已有README哈希冲突，单独保留记录 |
| [Partial 冻结目标筛选](./completed/partial_cohort_20261017.md) · [用法](../docs/evaluation.md#对照与输出) | `--cohort`只过滤原前三个注入目标，保留前三个用户；partial_screened明确分母；381项离线回归 | 未调用真实模型或证明费用/安全收益；与全量screened范围不同 |
| [Partial 场景选择](./completed/partial_suites_20261017.md) · [用法](../docs/evaluation.md#对照与输出) | 可跳过workspace，按所选场景导出/计分/绑定范围；375项离线回归 | 优化子集不代表四场景完整评测；未运行真实模型或测量实际节省费用 |
| [预检进度与统一入口](./completed/injection_progress_20261016.md) · [指南](../docs/injection_precheck.md) | 即时进度/15秒等待提示、已知旧状态兼容、run_benchmark --cohort、明确screened范围；369项离线回归 | 未执行新的真实模型预检/攻击；需同步服务器并用新测量name执行匹配对照 |
| [Injection 目标预检](./completed/injection_precheck_20261016.md) · [用户指南](../docs/injection_precheck.md) | 独立目标预检、兼容历史复用、失败复测、冻结名单与全用户/筛选目标测量；离线358/358 | 未运行新的模型预检/攻击；筛选子集不是全量结果，不证明安全收益或E0通过 |
| [准备读取诊断及候选撤回](./completed/read_discovery_20261016.md) · [配对清单](./completed/read_discovery_20261016_manifest.json) | 有限模型审计28+28、L1延续4次；候选18/28→22/28但新增误拒，已撤回；保留JSON请求预检查 | 未恢复TSR，未运行新全量clean/攻击；默认v3.1，准备读取/相关来源的稳定判定仍待解决 |
| [Clean通用误伤修正](./completed/clean_utility_20261015.md) · [已实施计划](./completed/clean_utility_opt_20261015.md) | L3有界相关调用—返回证据、大小比较完整元数据；L2明确邮件/网页来源；L1来源澄清；v2输入兼容绑定 | 全量clean/攻击及重复真实模型验收待完成，约5pp是目标，不宣称TSR恢复 |
| [全量benchmark同步](./completed/full_benchmark_20261015.md) · [测试指南](../docs/full_benchmark.md) | 全任务范围、原生baseline/clean、多攻击、当前控制、隔离输出、配置绑定和统一报告；partial前缀保留 | 该工程阶段仅离线验证；当前另有用户全量clean导出，重复/攻击/研究闸门验收仍待完成 |
| [L1有限投影实施](./completed/l1_projection_20261013.md) · [计划](./completed/L1_projection_implementation_plan_20261013.md) | 原生银行月支出六字段/全行投影、严格回退、模式/缓存/路由绑定、原文审计与平台默认同步 | 仅一个有限profile；真实四臂安全/效用/Token验收与更广输出适配仍待完成，未宣称新颖性 |
| [Dashboard v2.2显示同步](./completed/dashboard_v22_20261013.md) | 引擎版本动态读取、L1/L3规则、普通/委托流程预览、路由与成本状态、窄屏验收 | 无新防御机制、模型评测、网页CSA控件或失败片段浏览器 |
| [防御下降诊断与修复](./completed/defense_regression_analysis_20261012.md) · [最新复核](./completed/l2_docs_sync_20261013.md) | L1概述/外发规则与L3正文审查；19/19探针、12攻击+3干净任务；当前已记录144条v2.2：TSR130/144、nativeASR0/144 | 单次观察；重复匹配、独立终态与因果/成本验收未完成；原144条历史诊断不改写 |
| [三层基础方案](./completed/3_layer_opt.md) · [实施报告](./completed/three_layer_implementation_20261010.md) | L1来源视图、L2整批前置、原L3与平台架构同步 | 匹配四臂消融、总成本目标、引用保真和独立终态验证；CSA/DRV不在已实施范围 |
| [Partial报告优化](./completed/partial_reporting_20261010.md) | Markdown运行摘要、逐场景指标与有界失败片段 | 不改变原生评分，不提供新的安全oracle；尚未在平台增加独立失败片段浏览器 |
| [V2与其他历史阶段](./completed/README.md) | 各阶段已完成项及证据已归档 | Stage2执行提示撤回；旧方案里的重审/恢复、LLM净化等不能当作当前默认能力 |
| [本次文档与交接核查](./completed/framework_docs_cleanup_20261010.md) | README解释、方案归属和平台交付清单 | 真实实验结论仍由原始结果/独立核查决定 |
| [L3纯算法实现](./completed/l3_algorithm_implementation_20261010.md) | 固定评分、硬条件、分组校准工具、一次性路由交接和CLI成本账 | 独立真实数据、部署阈值、selective收益验收及网页专门控件 |
| [实验配置与工作台更新](./completed/dashboard_framework_ui_20261010.md) | 三层控件与预设、响应式布局、有效分母与两类模型成本、trace 统计覆盖 | 无新模型评测；CSA 与独立失败片段浏览器未实施 |
| [模型/工具配置文档](../docs/model_tool_configuration.md) · [阶段报告](./completed/configuration_docs_20261013.md) | 模型角色/字段/获取方式、工具schema与风险元数据、加载顺序/自检/可选参数已说明 | 文档与离线解析检查，不证明服务鉴权、模型工具能力或新的实验收益 |
| [L2优化实施](./completed/l2_implementation_20261012.md) · [当前状态](./completed/l2_docs_sync_20261013.md) | 默认视图/有界任务文件、host profile API、目录复核、控件/trace均保留；当前源码重新审查 | 真实profile/独立标签与L2视图单变量控制待完成，当前成本标记不可直接比较；L2_opt.md保留余项 |
| [框架与平台汇报材料](../report/report.md) | 用户指定 report/ 目录；10页主线介绍架构、各层实现/例子、优缺点和平台；README 列出 L3 待决定项 | 截图待用户补入；尚未生成实际幻灯片，不新增实验结论 |

## 待完成验收的方案

2026-10-13文档复核已完成，见 [报告](./completed/l2_docs_sync_20261013.md)。该文档阶段保护运行源码、旧报告/原字节与用户results/download；随后L1有限投影工程另有报告，最新观察不等于所有方案都已通过验收。

| 方案 | 已落实的关联基础 | 未实施内容 / 当前决定 |
| --- | --- | --- |
| [L1结构化投影候选](./L1_opt.md) | 当前 Spotlighting 风格来源封装、原文审计与日志保留 | 已实施一个原生月支出profile及模式/严格适配；更广profile与四臂保真/安全/成本评估待完成，不适用则保留来源封装 |
| [L2授权优化余项](./L2_opt.md) | 授权工具视图、有限host profile/正负证据与只读闭包、有界 order.txt 展开与共享 T_eff、新user替换授权、目录冻结和平台控件已实施 | 真实host profile/独立标签、匹配模型成本/安全/效用验收待完成；通用跨轮解析、按需展示、目录热切换和部分执行未实施；任务源污染按用户范围排除，不新增对象/参数/数据授权 |
| [L3 Checker优化](./L3_checker_opt.md) | 三层基础、公开读取免审、确定性权限前置 | 纯算法路由、分组校准工具、off/shadow/selective、受信交接已实现；真实独立数据/部署阈值与端到端验收仍待完成，不训练分类器 |
| [授权对照校准（历史归档）](./archive/framework_docs_cleanup_20261010/originals/workshop/original_framework_direction_20261008.md) | 原可信任务授权和当前动作审计 | 原候选入口已不在当前树；按保留归档阅读。机制未实施且暂停，不叠加到三层默认 |

[21篇来源目录](./3_layer_sources_20261008.json)保留在顶层供待优化项引用。旧 [DRV方案](./archive/3_layer_low_cost_20261009/originals/workshop/3_layer_opt.md)及[更早三层方案](./archive/3_layer_redesign_20261008/originals/workshop/3_layer_opt.md)仅作历史参考。方案中的样本数、成本算例和验收目标属于设计，不能当成已经运行的结果。

## 平台交接

[docs/framework_updates.md](../docs/framework_updates.md)列出逐项核查：三层架构展示、历史分析下载与多指标分图已交付。后续工作台更新补齐独立 L1 与 L2 前置控件、三层消融 / V2 风格对照和统计面板；2026-10-12补齐L2工具视图/任务文件控件及实际trace统计；2026-10-13先完成v2.2动态版本说明，再同步v3有限投影与默认API配置；网页无单独投影模式选择器；CSA API/partial CLI模式已接入，网页CSA专门控件与独立失败片段浏览器仍未实施。

## 存放规则

| 路径 | 内容 |
| --- | --- |
| `workshop/*.md` | 待实施机制方案；README为索引 |
| [completed/](./completed/README.md) | 已完成工程/评估阶段的方案与报告，明确剩余项/撤回项 |
| `artifacts/<YYYYMMDD>_<task>/` | 所有新agent测试产物，日志与诊断固定放在此处 |
| `archive/` | 历史方案、原始字节及日期化迁移/修订清单 |
| [results/](./results/framework_optimization/) | 已有历史证据与脚本，不新增运行输出 |

正式论文路线/计划在兄弟 [research](../../research/technical_route.md)。测试源码在tests，用户正式结果/导出留在 [results/](../results/) 和 [download/](../download/)。Agent partial实验必须显式传新 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。其余规则见 [AGENTS.md](../AGENTS.md)。

`python workshop/verify_migration.py` 默认只读，不改旧证据。完整历史检查仍受研究侧既有兼容路径删除影响；本次当前文件、原字节和链接检查记录于本次阶段报告，不能把局部通过称为完整迁移通过。
