# 已完成阶段的优化材料

新增 [Clean通用误伤修正](./clean_utility_20261015.md)：工程与离线回归完成；约5pp目标、真实clean/攻击/成本验收待完成。

当前运行代码为 **three-layer-v3.1**。这里收纳工程、评估或整理阶段已完成的文件；每个阶段的实验目标、备选机制与研究闸门分别列示。历史原文中的“尚未实施”描述属于当时设计，当前状态以本表和后续实施报告为准。

| 材料 | 已完成 / 当前保留 | 未完成、撤回或仅为设计 |
| --- | --- | --- |
| [全量benchmark入口同步](./full_benchmark_20261015.md) · [用户指南](../../docs/full_benchmark.md) | 复用执行/报告流程、全部注册任务、baseline/clean/攻击选择、当前控制与绑定；318项离线检查通过 | 未运行真实全量模型实验，不证明防御率/成本收益或E0通过 |
| [L1有限投影实施](./l1_projection_20261013.md) · [计划](./L1_projection_implementation_plan_20261013.md) | 原生银行月支出六字段/全行投影、严格回退、模式/缓存/路由绑定、原文审计与平台默认同步 | 仅一个有限profile；真实四臂安全/效用/Token验收与更广输出适配仍待完成，未宣称新颖性 |
| [Dashboard v2.2显示同步](./dashboard_v22_20261013.md) | 动态引擎版本、L1/L3规则、有效流程预览、历史版本/路由/成本状态、桌面与窄屏验收 | 无新模型评测或运行机制；网页CSA控制和失败片段浏览器仍未实施 |
| [防御下降诊断与修复](./defense_regression_analysis_20261012.md) · [后续复核](./l2_docs_sync_20261013.md) | 定向验证保留；当前已记录144条v2.2：TSR130/144、nativeASR0/144 | 原报告是2026-10-12快照；当前重复控制、独立终态与因果/成本验收仍待完成，旧哈希不改写 |
| [L2文档/平台交接复核](./l2_docs_sync_20261013.md) | 当前源码/保留产物审查、完整144条现有记录核对、README/workshop/指南同步；当时的显示待办由后续Dashboard阶段完成 | 不新增运行机制或模型评测；原报告保留当时状态 |
| [模型/工具配置文档](../../docs/model_tool_configuration.md) · [报告](./configuration_docs_20261013.md) | evaluation配置节扩写、README入口、TOML/离线代码示例与字段/控制核对 | 无runtime/默认值/配置改动，不运行真实模型或任务 |
| [L2优化实施](./l2_implementation_20261012.md) · [计划](./L2_implementation_plan_20261012.md) | 授权视图、host profile API/只读闭包、有界文件展开、新任务替换/目录复核、平台控件 | 真实profile/标签、匹配成本与效用/安全验证待完成；通用跨轮语义、按需展示、热目录与部分执行未实施 |
| [三层基础方案](./3_layer_opt.md) · [实施报告](./three_layer_implementation_20261010.md) · [实施计划](./three_layer_implementation_plan_20261010.md) | L1来源视图、L2整批前置、原L3、平台架构；离线实施验收完成 | §5总成本目标与§7匹配模型消融尚未正式验收；CSA、DRV、LLM净化、自动恢复未启用 |
| [L3纯算法实现](./l3_algorithm_implementation_20261010.md) · [计划](./l3_algorithm_implementation_plan_20261010.md) | 工具/模式/校准/凭据工程接入，默认off | 真实独立数据、部署阈值和模型匹配收益尚未验收 |
| [框架与平台介绍](../../report/report.md) | 按用户要求放在 report/；10页主线与备份资料，供后续 LaTeX Beamer 制作 | 平台截图留白；实际幻灯片和真实收益实验待后续制作/验证 |
| [本次文档与交接核查](./framework_docs_cleanup_20261010.md) | README流程/例子、归档状态和平台交付核对 | 文档核查不证明ASR/TSR改善 |
| [实验配置与工作台](./dashboard_framework_ui_20261010.md) | 三层配置/预设、实际配置与路由统计、有效分母/成本口径、响应式验收 | 无新模型实验、CSA 或失败片段浏览器；旧 trace 缺失不重建 |
| [Partial结果报告](./partial_reporting_20261010.md) | 运行级摘要、位置索引、有界失败片段 | 无新评分oracle；平台独立失败片段浏览器未实施 |
| [V2后续报告](./framework_v2_followup_report.md) | Stage1宿主描述与准备读取判断保留；重放方法已纠正 | Stage2执行提示已评估并撤回，completion_prompt默认false；重复控制和真实E0仍待完成 |
| [V2实施记录](./framework_v2_report.md) | 任务隔离、授权简化、有限工具上下文等保留 | 当时试验参数不等于当前默认；不认定动态扩权/完整scope已实现 |
| [V2提案](./framework_optimization_v2_proposal_20261007.md) · [约束](./framework_optimization_direction_20261007.md) | 授权/审计主线已由后续报告落实；新三层由用户另行选用 | 原§5局部LLM工具返回处理未采用；当前L1是来源封装，不能称等价净化已完成 |
| [初轮方案](./framework_optimization_20261007.md) · [报告](./framework_optimization_report.md) · [复核](./framework_optimization_review_20261007.md) | 任务隔离、风险元数据与误拒问题已进入后续V2修正 | 有界重审/完成提示不作为默认；原重复模型验证矩阵不是全已执行清单 |
| [早期工程计划](./2026-10-05-workshop-engineering-optimization.md) · [报告](./workshop_optimization_report.md) | harness bookkeeping、紧凑trace与I3 fixtures | E0合成自检不等于真实闸门；旧八例I3 no_go被24valid/8scope的partial证据取代 |
| [项目结构整理](./project_structure_20261008.md) | 文档分工、路径与产物规则 | 既有历史输入缺失不重建，完整迁移存在已记录限制 |

L2原始工程报告和计划保留为当时v2的实施记录，当前v2.2状态读 [后续复核](./l2_docs_sync_20261013.md)；未验收的 [L2方案](../L2_opt.md)仍在顶层。

仍待真实数据与收益验收的 [L3 Checker](../L3_checker_opt.md) 与 [授权对照校准（历史归档）](../archive/framework_docs_cleanup_20261010/originals/workshop/original_framework_direction_20261008.md) 留在 [顶层索引](../README.md)。正式E0/I3/I2状态以 [研究路线](../../../research/technical_route.md) 和 [I3报告](../../docs/i3_p0_stress_report.md) 为准。

旧稿件与CFP：[投稿草案](../archive/legacy_submission/ALMML_sub.md)、[原附件](<../archive/legacy_submission/AIMLL WS.pdf>)；旧docs/图表见 [归档索引](../archive/project_structure_20261008/README.md)。旧证据位于 [workshop/results/](../results/framework_optimization/)，所有新输出放 `workshop/artifacts/`。

本次移动前的原始字节与哈希单独保留；历史报告的路径更新只改变当前阅读入口，不重写原样本或测量。完整存放规则见 [AGENTS.md](../../AGENTS.md)。
