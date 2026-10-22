# Workshop 优化状态索引

- 2026-10-22：[DSCG_v3.3读取路由与当前动作审计](./completed/l3_read_policy_20261022.md)，读取批次规则候选、shadow观察与严格协议；仅离线验收。

- 2026-10-22：[当前DSCG_v3.2的Slack下降分析](./completed/slack_v32_analysis_20261022.md)，L2漏授改善、L3读取及记录校验仍主导；164条Slack退步逐条证据。

- 2026-10-22：[L2原生定义与步骤授权](./completed/l2_step_authorization_20261022.md)，v3.3；Qwen固定小样本及剩余L3阻断，未证明整体收益。

新增[Slack/banking v4.1逐案例分析](./completed/slack_banking_tsr_cases_20261022.md)：对齐baseline成功而v4.1失败的337条（Slack176、banking161），逐条记录授权、读取阻断、审计记录校验、工具调用及末答；只读分析，不改策略、不调用模型。

新增[默认L2/L3意图与来源策略](./completed/intent_source_relaxation_20261021.md)：默认v3.2保留合理工具候选、精简当前动作审计；分开记录模型协议、审计记录和回执失败。执行边界不变、旧诊断回放保留，仅离线验收，真实TSR/ASR待固定小样本验证。

新增[Qwen 单案例在线核对](./completed/tool_arguments_live_20261021.md)：仅原失败案例及其生成边界，9 次请求、11,472 Tokens，未复现 JSON 异常；单案例被审计阻断，效用未成功。补充安全错误元数据，不宣称输出根因修复。

新增[工具参数 JSON 单任务隔离](./completed/tool_arguments_json_20261021.md)：CLI 解析错误只结束当前任务，后续任务继续；错误排除评分分母，GOAL 错误独立报告，无参数修补或请求重试。原结果保留，线上续跑待用户启动。

新增[按Attack默认并行](./completed/attack_parallel_20261021.md)：每个attack独立spawn进程，内部场景与任务顺序不变；主进程统一校验、进度和根汇总。无新增参数；双环境原生离线并行/缓存对照通过，真实服务加速和限流待测。


新增[精简任务对齐候选](./completed/task_alignment_20261021.md)：`--prompt-profile task-alignment-v1`可直接进行benchmark；L2步骤与工具作用匹配、L3当前动作审计，保留原简洁目录和全部执行边界。诊断authorized-v2补齐合成授权/来源工具，旧包可复核。默认legacy不变，真实效果待测，无新增模型调用。

新增[Qwen有限真实诊断结果](./completed/utility_diagnosis_20261021.md)：已用完明确授权的144次请求，API错误0、Token131,588；L3协议改善未证明效用恢复，银行诊断缺授权上下文；L2语义候选新增错授权，不晋升默认。保留原始输入和响应，先以新版本修诊断；source/37clean未启动。

新增[有限真实诊断采集器](./completed/utility_collection_20261021.md)：明确执行/次数上限、SDK零重试、首次接口错误停止、调用前持久化及provider适配；此前为实际0次、等待授权的工程快照；后续用户明确批准的144次执行结果见上方新报告。

新增[banking/Slack分阶段诊断准备](./completed/utility_stages_20261021.md)：固定24审计例/12授权例、相邻响应比较和重叠失败信号；当时仅离线工程交付；后续144次模型诊断已完成但不晋升，37项clean仍待安排，默认防御未改。

新增[L3审计提示压缩](./completed/l3_audit_prompt_20261021.md)：基础提示3262→1919字符，保留来源/准备读取/外发审查并明确四字段协议；配置身份自动变化，仅离线验收，真实语义效果待测。

新增[L3直接阈值路由](./completed/l3_threshold_20261021.md)：默认经验阈值0.70，internal/personal读取资格，无运行时artifact依赖；shadow阈值比较与旧记录语义分离，真实收益待新实验。

新增[AgentDyn/Qwen消息角色兼容](./completed/agentdyn_qwen_roles_20261019.md)：DashScope公共Chat适配与受限API失败诊断；请求身份绑定，新run名复测。原始失败与conda包保留；仅离线验证，服务器模型测试待运行。

新增[L3校准候选参数初始化](./completed/l3_preset_20261019.md)：候选网格/参考值与5%风险、5%置信错误目标已保存，校准入口支持显式预设；仍需独立标签/分组校准，无部署阈值或新免审。

新增[结果精简与L3运行级汇总](./completed/result_reports_20261019.md)：共享离线报告、紧凑摘要与完整失败索引已接线；指定旧目录仅新增两份报告，1279原文件SHA256不变。两环境/网页回归通过，无模型调用或防御策略变化；[使用指南](../docs/result_files.md)。

2026-10-19：[Qwen候选验收计划](./qwen_utility_20261019.md)、[已完成工程报告](./completed/qwen_utility_20261019.md)与[使用指南](../docs/qwen_utility.md)。协议诊断和分阶段候选工程已接线，默认legacy保留；首轮144次模型诊断已完成但输入限制/候选错误阻止晋升，37/97clean与冻结cohort攻击未执行，尚未证明TSR恢复。L1未改。

最新结果布局：[按后端分目录](./completed/backend_result_layout_20261018.md)。CLI测量/预检使用分类根/后端/运行目录；旧目录原地续跑，历史页兼容；网页发起实验布局不变。

当前测试流程：[顺序执行与轻量校验](./completed/serial_lightweight_20261018.md)。已移除workers及源码扫描哈希；旧结果按配置续跑，cohort证据校验保留。此前并发实施报告保留为历史。

当前：[双基准自动切换](./completed/dual_benchmark_20261018.md)支持ipi/AgentDojo与ipi-agentdyn/AgentDyn，只切换环境；旧阶段的AgentDyn-only描述保留当时上下文，不再限制当前新实验。

新增 [AgentDyn全流程接入](./completed/agentdyn_integration_20261017.md)：固定后端、新三个场景、风险目录、CLI/网页/历史身份、错误分母与离线模拟已完成；原四场景结果保持历史，真实攻击强度和模型TSR/ASR待验收。

当前运行框架为 **three-layer-v3.1**。目录按工程落实状态管理：基础方案已实施的文件归入 completed；仍需实现的新机制留在顶层。完成工程不等于实验目标或研究闸门全部通过。

## 已完成与归档

| 方案 / 阶段 | 已完成 | 尚未完成或未采用 |
| --- | --- | --- |
| [Qwen接入与进程并发](./completed/qwen_parallel_20261018.md) | 双模型默认Qwen3.7-Flash关闭思考；该阶段并发实现已由后续顺序流程替代，原报告/证据保留 | 仅离线接线与调度验收；无官方Batch折扣、真实服务或防御收益验证 |
| [服务器cohort续跑排错](./completed/cohort_resume_diagnostics_20261017.md) · [用法](../docs/benchmark.md#cohort-或续跑校验失败) | 定位服务器解析器改动；细化校验错误、修复兼容映射生成环境限制；413项离线回归 | 服务器需恢复已审核源码并保留旧路由off；无真实模型或完整服务器轨迹校验 |
| [默认攻击与显式续跑](./completed/benchmark_reuse_20261017.md) · [用法](../docs/benchmark.md#显式续跑示例) | 新typical三攻击；full/partial/clean/cohort支持reuse、旧名单与严格兼容、快照；407项离线回归 | 原生错误缓存不自动重试；未知来源或旧baseline证据不足拒绝；无真实模型测量 |
| [Experiments目录归类](./completed/experiments_layout_20261017.md) · [入口索引](../experiments/README.md) | 顶层三个日常入口；共享实现、诊断、校准与工具分目录，已知旧预检严格兼容；391项离线回归 | 无真实模型或费用/安全收益验证；专项fixture与历史证据保留 |
| [测试指南拆分与CLI默认值](./completed/docs_benchmark_structure_20261017.md) · [测试索引](../docs/evaluation.md) | benchmark/partial分开，公共说明集中；CLI默认shadow、baseline/NoChecker off；389项离线回归 | 未调用真实模型；保留原档与用户删除，既有plan/report缺失引用另列 |
| [全量入口场景选择](./completed/full_suites_20261017.md) · [用法](../docs/benchmark.md#1-使用哪个入口) | full/partial共用--suites；full保留所选场景全部任务，兼容clean/cohort/导出；385项离线回归 | 场景子集不是四场景全量；无真实模型/费用收益测量 |
| [experiments/docs整理](./completed/experiments_docs_cleanup_20261017.md) · [当前实验入口](../experiments/README.md) | 退役8个旧文件、清理生成缓存、索引与文档去重；原始字节归档 | 不改变运行/评分；早期迁移快照校验已有README哈希冲突，单独保留记录 |
| [Partial 冻结目标筛选](./completed/partial_cohort_20261017.md) · [用法](../docs/partial_benchmark.md#对照与输出) | `--cohort`只过滤原前三个注入目标，保留前三个用户；partial_screened明确分母；381项离线回归 | 未调用真实模型或证明费用/安全收益；与全量screened范围不同 |
| [Partial 场景选择](./completed/partial_suites_20261017.md) · [用法](../docs/partial_benchmark.md#对照与输出) | 可跳过workspace，按所选场景导出/计分/绑定范围；375项离线回归 | 优化子集不代表四场景完整评测；未运行真实模型或测量实际节省费用 |
| [预检进度与统一入口](./completed/injection_progress_20261016.md) · [指南](../docs/injection_precheck.md) | 即时进度/15秒等待提示、已知旧状态兼容、run_benchmark --cohort、明确screened范围；369项离线回归 | 未执行新的真实模型预检/攻击；需同步服务器并用新测量name执行匹配对照 |
| [Injection 目标预检](./completed/injection_precheck_20261016.md) · [用户指南](../docs/injection_precheck.md) | 独立目标预检、兼容历史复用、失败复测、冻结名单与全用户/筛选目标测量；离线358/358 | 未运行新的模型预检/攻击；筛选子集不是全量结果，不证明安全收益或E0通过 |
| [准备读取诊断及候选撤回](./completed/read_discovery_20261016.md) · [配对清单](./completed/read_discovery_20261016_manifest.json) | 有限模型审计28+28、L1延续4次；候选18/28→22/28但新增误拒，已撤回；保留JSON请求预检查 | 未恢复TSR，未运行新全量clean/攻击；默认v3.1，准备读取/相关来源的稳定判定仍待解决 |
| [Clean通用误伤修正](./completed/clean_utility_20261015.md) · [已实施计划](./completed/clean_utility_opt_20261015.md) | L3有界相关调用—返回证据、大小比较完整元数据；L2明确邮件/网页来源；L1来源澄清；v2输入兼容绑定 | 全量clean/攻击及重复真实模型验收待完成，约5pp是目标，不宣称TSR恢复 |
| [全量benchmark同步](./completed/full_benchmark_20261015.md) · [测试指南](../docs/benchmark.md) | 全任务范围、原生baseline/clean、多攻击、当前控制、隔离输出、配置绑定和统一报告；partial前缀保留 | 该工程阶段仅离线验证；当前另有用户全量clean导出，重复/攻击/研究闸门验收仍待完成 |
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
