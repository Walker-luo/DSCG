# 已完成阶段的优化材料

新增[冻结cohort轻量读取](./cohort_lightweight_20261021.md)：只校验主模型ID/provider、后端版本、所选任务及一次名单摘要；不再访问原预检证据。实际测量缓存配置保持严格绑定，screen证据流程不变；取代下面旧adapter no-op名单读取策略。


新增[旧cohort请求适配标记兼容](./cohort_adapter_noop_20261021.md)：仅对证据及当前序列化验证为无实际变化的AgentDojo/DashScope新增标记允许原名单继续读取；原cohort不改写，实际请求变化仍拒绝。双环境离线回归通过，无模型调用。

新增[L3直接阈值路由](./l3_threshold_20261021.md)：默认经验阈值0.70，internal/personal读取资格，无运行时artifact依赖；shadow阈值比较与旧记录语义分离，真实收益待新实验。

新增[Benchmark兼容与报告简化](./ponytail_benchmark_20261020.md)：单个runner净减44行；双后端6个离线场景共50份输出一致，全量Python及Node检查通过，无模型调用或研究闸门变化。

新增[AgentDyn零TSR/ASR诊断与小样本对照](./agentdyn_zero_rates_20261020.md)：只读诊断与36条真实计分小样本；两模型shopping clean baseline均2/3，当前DSCG及两个候选均0/3。未修改默认策略；baseline攻击也为零且Qwen预检不稳定，不能据此认定防御有效。原266个用户结果文件哈希不变。

新增[AgentDyn tool_knowledge 不兼容组处理](./agentdyn_tool_knowledge_20261020.md)：对实际选中目标做原生参考调用只读检查，dailylife组标记unsupported；CLI/Dashboard保留计划数、跳过理由和有效分母。双环境及Node离线回归通过，原DeepSeek结果保持原字节；真实模型续跑由用户显式启动。

新增[AgentDyn/DeepSeek Chat角色兼容](./deepseek_chat_roles_20261020.md)：本次422诊断定位到AgentDyn的developer请求角色，宿主对DeepSeek增加独立适配身份；离线协议和双环境回归通过，真实服务须新名复测。

新增[DeepSeek/AgentDyn TypeError 定位与修复](./deepseek_agentdyn_typeerror_20261020.md)：在线最小诊断定位到失败成本汇总，修正结构化API诊断的计数方式；AgentDyn原生缓存类型在内存中初始化。原用户结果保留，真实修复后测量仍需新运行名复测。

新增[AgentDyn/Qwen消息角色兼容](./agentdyn_qwen_roles_20261019.md)：DashScope公共Chat适配与受限API失败诊断；请求身份绑定，新run名复测。原始失败与conda包保留；仅离线验证，服务器模型测试待运行。

新增[L3校准候选参数初始化](./l3_preset_20261019.md)：候选网格/参考值与5%风险、5%置信错误目标已保存，校准入口支持显式预设；仍需独立标签/分组校准，无部署阈值或新免审。

新增[结果精简与L3运行级汇总](./result_reports_20261019.md)：共享离线报告、紧凑摘要与完整失败索引已接线；指定旧目录仅新增两份报告，1279原文件SHA256不变。两环境/网页回归通过，无模型调用或防御策略变化；[使用指南](../../docs/result_files.md)。

最新结果布局：[按后端分目录](./backend_result_layout_20261018.md)。CLI测量/预检使用分类根/后端/运行目录；旧目录原地续跑，历史页兼容；网页发起实验布局不变。

当前测试流程：[顺序执行与轻量校验](./serial_lightweight_20261018.md)。已移除workers及源码扫描哈希；旧结果按配置续跑，cohort证据校验保留。此前并发实施报告保留为历史。

当前：[双基准自动切换](./dual_benchmark_20261018.md)支持ipi/AgentDojo与ipi-agentdyn/AgentDyn，只切换环境；旧阶段的AgentDyn-only描述保留当时上下文，不再限制当前新实验。

新增 [AgentDyn全流程接入](./agentdyn_integration_20261017.md)：固定后端、新三个场景、风险目录、CLI/网页/历史身份、错误分母与离线模拟已完成；原四场景结果保持历史，真实攻击强度和模型TSR/ASR待验收。

新增 [Clean通用误伤修正](./clean_utility_20261015.md)：工程与离线回归完成；约5pp目标、真实clean/攻击/成本验收待完成。

后续 [准备读取诊断](./read_discovery_20261016.md) 已完成一轮有限验证，提示/输入候选因新增误拒撤回。保留的请求格式预检查不改善TSR，不能把归档候选算作已部署能力。

当前运行代码为 **three-layer-v3.1**。这里收纳工程、评估或整理阶段已完成的文件；每个阶段的实验目标、备选机制与研究闸门分别列示。历史原文中的“尚未实施”描述属于当时设计，当前状态以本表和后续实施报告为准。

| 材料 | 已完成 / 当前保留 | 未完成、撤回或仅为设计 |
| --- | --- | --- |
| [Qwen接入与进程并发](./qwen_parallel_20261018.md) | 双模型默认Qwen3.7-Flash关闭思考；该阶段并发实现已由后续顺序流程替代，原报告/证据保留 | 仅离线接线与调度验收；无官方Batch折扣、真实服务或防御收益验证 |
| [服务器cohort续跑排错](./cohort_resume_diagnostics_20261017.md) | 明确源码不匹配提示、相同服务器Python版本的兼容修复；413项离线回归 | 服务器需同步修复、恢复解析器默认None并保持原防御参数；未运行真实benchmark |
| [默认攻击与显式续跑](./benchmark_reuse_20261017.md) · [用法](../../docs/benchmark.md#显式续跑示例) | 新typical三攻击；reuse保留旧计划/缓存及证据，407项离线通过 | 旧baseline缺原生防御证据时拒绝；不新增错误重试或真实模型结果 |
| [Experiments目录归类](./experiments_layout_20261017.md) · [入口索引](../../experiments/README.md) | 三个日常入口保留原命令，其余归入common/diagnostics/calibration/tools；391项离线回归 | 没有新增模型结果，I3/E0状态及既有实验身份保留 |
| [测试指南结构整理](./docs_benchmark_structure_20261017.md) · [测试索引](../../docs/evaluation.md) | 分开完整任务与partial运行说明；同步CLI shadow默认与baseline/NoChecker兼容 | 无真实模型或收益验证；原始文档及历史证据保持可追溯 |
| [预检进度与统一benchmark入口](./injection_progress_20261016.md) | screen实时进度/15秒等待、旧状态与名单兼容、统一--cohort、screened元数据、薄兼容转发；369/369离线通过 | 真实服务器预检/筛选攻击待执行，未产生新模型结果或安全收益 |
| [Injection 目标预检与筛选测量](./injection_precheck_20261016.md) · [用户指南](../../docs/injection_precheck.md) | 独立screen/benchmark、兼容复用/失败复测、冻结分母与错误/成本记录；358项离线回归 | 真实服务器预检和筛选后的匹配攻击实验待执行，直接失败不证明间接攻击不可能 |
| [全量benchmark入口同步](./full_benchmark_20261015.md) · [用户指南](../../docs/benchmark.md) | 复用执行/报告流程、全部注册任务、baseline/clean/攻击选择、当前控制与绑定；318项离线检查通过 | 未运行真实全量模型实验，不证明防御率/成本收益或E0通过 |
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

仍待真实数据与收益验收的 [L3 Checker](../L3_checker_opt.md) 与 [授权对照校准（历史归档）](../archive/framework_docs_cleanup_20261010/originals/workshop/original_framework_direction_20261008.md) 留在 [顶层索引](../README.md)。正式E0/I3/I2状态以 [研究路线](../../../research/technical_route.md) 和 [I3交接记录](../../../research/Experiments/implementation_status.md) 为准。

旧稿件与CFP：[投稿草案](../archive/legacy_submission/ALMML_sub.md)、[原附件](<../archive/legacy_submission/AIMLL WS.pdf>)；旧docs/图表见 [归档索引](../archive/project_structure_20261008/README.md)。旧证据位于 [workshop/results/](../results/framework_optimization/)，所有新输出放 `workshop/artifacts/`。

本次移动前的原始字节与哈希单独保留；历史报告的路径更新只改变当前阅读入口，不重写原样本或测量。完整存放规则见 [AGENTS.md](../../AGENTS.md)。
