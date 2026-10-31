# 当前框架与平台展示交接

更新时间：2026-10-18（AgentDojo / AgentDyn 按环境自动识别；三层防御规则及默认开关保持）。当前默认版本 **three-layer-v3.1**。此前用户授权实现有限L1结构化投影，沿用L2工具视图/任务文件与L3动作正文审查；默认投影已接入factory、partial和网页API，架构说明同步。Spotlighting风格来源封装仍是不适用输入的回退。正式研究路线和闸门不改变。

## 双后端平台交接（2026-10-18）

同一个 Dashboard 入口按 Python 进程实际安装的来源与锁定源码自动识别后端：`ipi` 使用 AgentDojo，`ipi-agentdyn` 使用 AgentDyn，不增加后端选择器或额外参数。切换环境后须重启 Dashboard；需要并行查看时可在两个终端使用不同 `PORT`，各进程保持各自后端。启动命令见 [Dashboard 指南](./dashboard.md)。这替代 2026-10-17 仅允许 AgentDyn 新执行的接线限制；原始说明已保存在本次整理的原文归档中。

两边的 suite version 均为 `v1.2`。AgentDojo 注册 workspace/travel/banking/slack，用户/注入任务分别为 40/14、20/7、16/9、21/5；AgentDyn 注册 shopping/github/dailylife，分别为 20/9、20/9、20/10。全用户 clean 范围分别为 97 与 60 个原生用户任务，不是本次模型结果。网页场景、计数、预估任务、原生循环标签与攻击注册表来自当前已验证安装；任务上限、seed、模型连接、原生 baseline、三层开关及路由规则保持原设置。

来源和源码按 [AgentDojo](../config/agentdojo.lock.json)与 [AgentDyn](../config/agentdyn.lock.json)两份锁定文件核对。AgentDyn 固定 Git 提交 `5353cf7615b135cace8d07c8f12dac53a16b6db3`；AgentDojo 记录 PyPI 版本、发行包哈希及被允许的已审阅本地变体。`runtime_variant` 和实际 `implementation_sha256` 保留变体差异，不能将审阅后的本地内容称作逐字节原发行版。

`/api/config` 在未知安装或来源/字节不符时返回 `benchmark_id=unknown`、`backend_ready=false`、空场景/攻击及 `backend_error`，页面可打开且禁用启动。新执行在创建模型客户端前失败关闭，后台任务再次核对提交时身份；历史分析不依赖活动后端通过校验。新网页 ID 自动带实际 `agentdojo_` 或 `agentdyn_` 前缀。配置、summary、整体结果、报告和下载保留 `benchmark` 的 id、repository、revision、suite_version、implementation_sha256、catalog_sha256、任务/环境/攻击/工具哈希，以及 package_version、source_kind、runtime_variant；AgentDojo 另保留 release_sha256。

风险目录按活动后端选择，`tool_metadata_selection`、`tool_metadata_path` 和单独的 `tool_metadata_error` 报告实际来源、路径与问题。已识别为相反基准的通用 local 目录会被跳过并给出 warning，保留用户原文件；未归属的自定义通用目录要求明确配置，不静默合并。后端就绪与风险配置错误分别报告，baseline 不使用 DSCG 风险目录；DSCG 在模型创建前验证目录覆盖及分类。

历史场景和图表按记录动态生成，两个基准的新旧结果均可读；缺失基准身份保持 `unknown`，不根据当前安装或相邻场景补写。旧记录仅供历史查看/导出，新实验用新名称，不能借当前身份自动续跑旧未知目录。历史分析/导出记录 `paired_comparison_ready`、`comparison_warnings` 和 task_selection；不同基准、任务目录、运行变体或未知身份不能合并分母或计算配对收益。工作台多运行对比拒绝未对齐请求，历史图表独立展示，热图按已记录身份及任务选择分隔。同一结果混入不同身份时聚合指标和分母留空。身份/任务一致也不证明模型修订、攻击投递或独立 oracle 一致。

运行错误保留原始结果和轨迹；派生效用/安全标签留空，错误不计入有效分母，不把原生谓词在异常轨迹上的布尔输出当成有效安全结果。记录分别保留计划/实际任务、有效分母、错误数和 Token；下载 schema 2 保留原汇总与明细统计两套口径，不补零。

AgentDyn 的 `browse_webpage`、`input_to_webpage` 可派发模拟账户/文件/仓库修改、外发或转账等处理器；[内置风险目录](../config/tools.agentdyn-v1.2.toml)按共享名称的实现并集保守分类，不能按“浏览”名称走只读免审。单一 effect 字段只记录主导风险；当前仍是工具级授权与语义审计，不强制校验 URL、域名、处理器、对象、目的地或参数，也不限制工具内部每个副作用。此前银行月支出 L1 投影未扩展为 AgentDyn 专用投影。

本次 Dashboard 在两环境分别通过 47 项 Python 检查，Node 历史/UI 检查 41 项通过，另完成实际目录、metadata 选择、新 ID 与未知后端拒绝/保留历史探测；见 [验证记录](../workshop/artifacts/20261018_dual_benchmark/dashboard/dashboard_validation.json)。没有模型调用或计分 rollout，也没有图形浏览器布局验收；不证明模型效果、E0 通过、浏览器操作安全保证或框架增益。研究闸门不因双后端接线改变。

## v3.1增量交接

2026-10-16后续：准备读取候选完成有限配对诊断后撤回，默认版本/输入仍为v3.1/v2，无新增网页选项或候选接线。仅增加审计请求的JSON格式预检查，错误配置在API调用前按现有失败关闭路径处理；正常请求不变。L1/L2/Monitor/路由开关保持。用户全量clean导出73/97，不是新候选成绩；[诊断与撤回报告](../workshop/completed/read_discovery_20261016.md)。

L3使用最多8条当前任务相关调用—返回对，最近4条必留，再补相关旧证据，调用参数、正文与错误共享8192字符；删除候选的纯大小比较保留完整元数据，来源与省略/截断仍明确标记。输入v2与配置身份使旧路由artifact失效。L2新增有限的唯一邮件/指定网页来源，读取仍经原中介；有序复合委托不提前展开，保留原流程；L1只澄清用户请求不因工具数据而失去权威。该阶段模型、router off、重试0、completion false保持原设置；后续CLI路由默认值见下方控制表。新紧凑 `dscg_audit_evidence` 已写trace，网页尚无独立证据统计面板；full可诊断，不默认展示原始工具文本。模板/控件说明同步，旧结果不重标。约5pp clean目标与攻击/成本收益均待新线上验收；[工程报告](../workshop/completed/clean_utility_20261015.md)。

## 实际运行顺序

```text
普通任务：真实 user → L2 编译 → 有效授权工具视图 → 主模型候选
委托任务：明确执行文件/唯一邮件/指定网页 → 仅准备读取权限 → 原中介执行读取
                          → 原要求 + 完整文件任务 T_eff → L2 编译 → 主模型候选
共同循环：候选 → L2 整批前置 → L3 → Monitor → 一次性 ticket → 执行
              ↑                                                ↓
              └──── 主模型规划 ← L1 有限投影/来源封装 ← 结果/错误 ──┘
```

L1不增加独立模型调用：此前支持的明确原生银行月支出任务保留全部交易六字段，省略subject自由文本；其他输入保留原来源封装，原历史与L3正文保持。投影不是事实认证或范围授权。当前规则要求日常任务/摘要中的无关注入提醒使用概述，避免转述攻击目标；用户明确要求的分析/安全报告/必要引用仍支持原文。该日常输出规则仍是规划提示；有限投影只改变支持域内的工具视图，最终文本没有新增过滤器。L3仍审计当前动作，外发同时审查正文与目的地；安全提醒若夹带无关攻击链接/目标也可能越出任务，必要来源链接及显式安全分析可以保留。API默认纯算法路由off，full/partial的DSCG CLI默认shadow，baseline/NoChecker自动off；重审0、completion_prompt=false；公开sink-free读取免审是既有行为。有效deny对已授权sink-free读取仍可能被原Monitor的READ_ONLY_SOURCE_ALLOW覆盖，abstain/错误阻断。对象/目的地/参数/数据权限未强制约束，最终纯文本回答不经动作审计。

## L2 已实施与限制

- 默认只向规划器展示完整有效授权工具定义，保留真实runtime；Pydantic schema采用独立展示快照，避免视图编辑污染宿主。隐藏/伪造工具调用仍经真实执行边界拒绝。
- 默认授权集合沿用原策略：有效读取工具通常加入权限，动作工具由一次任务编译选择。API可选受信 `ToolAuthorizationProfile`：有限模式匹配、tools/prohibited_tools/evidence协议和宿主必要只读闭包。证据位置不证明语义正确；冲突失败，不自动补授写入/外发。未匹配回退原编译，默认无业务profile。
- 新实际user回合替换旧grant并撤销未用票据；任务内冻结目录，工具定义/schema、run和dependency callable代码、元数据变化失效。执行消费票据后再复核权限。不是任意宿主状态变更检测，也不承诺撤回已在执行的副作用。
- 明确执行order.txt等有限句式可走准备读取→T_eff→一次完整授权编译；规划/L3共享T_eff，原始user/tool角色不改。总结文件与普通返回不升级任务。支持read_file和AgentDojo云盘及host reader，不递归委托；正文1536字符、完整规范化T_eff2048字符、序列化返回16384字符上限，超限失败。
- 附加限制只支持有限下游查询/禁止发送等完整句式；读取禁令或未覆盖限制在入口失败，不先执行读取再解释。用户确认后任务文件污染按用户明确范围排除。本功能不认证任务文件安全，不新增对象读取硬授权。
- 非法混合批次仍整体拒绝；缺工具/错误反馈不触发反复编译。通用跨轮指代/禁令继承、懒展示、热目录切换、部分执行和恢复均未实施。

## 平台接线与对照

| 配置 | 默认 / 接口 | 实际行为 |
| --- | --- | --- |
| L1/input_isolation | true，网页/API | 主模型有限投影/来源隔离视图 |
| l1_projection_mode | projected，API/partial CLI | off保留旧来源标记，shadow只观察；网页默认projected，尚无单独选择器；关闭L1则off |
| L2/use_sandbox | true，网页/API | 工具授权与最终权限检查 |
| authorization_precheck | true，网页/API | L3前候选整批检查；NoL2关闭 |
| planning_tool_view | true，网页/API/partial `--no-tool-view` | 授权工具展示；NoL2关闭 |
| delegated_tasks | true，网页/API/partial `--no-delegated-tasks` | 有界明确任务来源展开；NoL2关闭 |
| authorization_profile / delegated_task_reader | 默认None，仅宿主API | 受信配置，不由网页文本/工具返回创建 |
| L3/use_security_checker | true，网页/API | 原动作审计 |
| audit_router_mode/artifact | API off；full/partial DSCG CLI shadow，baseline/NoChecker off | CSA硬门/真实校准不变，网页专门控件仍待完成 |
| trace_level | summary | standard判决/账本、full压缩诊断；保留实际字段覆盖 |

网页完整/NoL1/NoL2/NoL3预设和自定义组合已接线。**V2风格**预设关闭L1、前置、视图与文件展开，但新版目录复核仍存在，不是历史V2精确复现。L2/L3全关时L1关闭；原生baseline始终走活动后端的原生工具循环，不带DSCG元数据。

[app.js](../dashboard/static/js/app.js)区分待启动配置和保存的有效配置；HTML/TXT报告显示已保存开关。概览新增完整/可见工具累计量、编译器调用和文件展开，且只统计实际计分任务的 `dscg_l2` trace。编译器调用可能零模型调用；字符/工具定义数不是Tokens。旧记录缺字段显示未记录，不推定零；攻击生成预检不计进该trace统计。

版本、开关、profile/reader身份、协议和任务输入边界进入pipeline/config/L3绑定；partial manifest继续绑定任务、模型、攻击与源码SHA。同名配置不兼容不能复用缓存，所有新对照使用新名称。旧L3校准artifact不得直接沿用，新有效任务应按实际审计packet独立标注并重新核查配置域。

## 平台交接状态

| 交接项 | 状态 / 证据 |
| --- | --- |
| 架构弹窗和实际循环 | 已同步v3有限L1投影及原L3规则；页面和API版本来自引擎常量，预览随工具视图/委托开关更新；[index.html](../dashboard/templates/index.html)、[app.js](../dashboard/static/js/app.js) |
| 网页开关到factory | 已接线并覆盖配置依赖、保存配置显示；[evaluation.py](../dashboard/evaluation.py)、[app.py](../dashboard/app.py) |
| 历史分析下载、多指标分图 | 两个基准的新旧场景按记录动态读取；benchmark/运行变体身份、任务选择与对齐告警进入导出，不同目录不配对/合并；本次 Node41/41，旧结果不重标、原始数据不迁移 |
| L2记录与覆盖 | 已接线，概览单列L2 trace覆盖；已保存版本/路由状态取自运行记录，成本不可比较标记明确显示；[控件/trace检查](../tests/test_l2_controls.py) |
| CSA专门控件、独立失败片段浏览器 | 仍未实施；API/partial CSA能力不能当作网页已提供 |

前序交接和历史截图见 [工作台报告](../workshop/completed/dashboard_framework_ui_20261010.md)、[文档清理报告](../workshop/completed/framework_docs_cleanup_20261010.md)。前序显示源码已同步，详见 [v2.2平台报告](../workshop/completed/dashboard_v22_20261013.md)。未重启用户服务；重启Dashboard并刷新即可加载新页面。历史结果和既有证据保持原身份。

## 验证与后续工作

历史工程过程和统计集中保留在workshop：[v2.2显示与版本身份](../workshop/completed/dashboard_v22_20261013.md)、[L1投影实施](../workshop/completed/l1_projection_20261013.md)、[v3.1 clean修正](../workshop/completed/clean_utility_20261015.md)及[准备读取候选撤回](../workshop/completed/read_discovery_20261016.md)。旧144条v2.2实验不能重新标记成当前版本；离线检查不证明模型收益或真实E0通过。

当前真实E0仍pending，I3为24个有效探针/8个范围缺口/0个工具边界缺口，I2仍locked。后续工作按 [研究路线](../../research/technical_route.md)选择，保留原始评分、数据与版本身份。

框架优化可用partial的场景选择和冻结cohort；正式full及全用户筛选测量保持独立，具体命令和分母见 [小批量测试指南](./partial_benchmark.md#对照与输出)与[全量指南](./benchmark.md)。新对照使用新run名，Agent产物写入新的workshop/artifacts目录。CSA网页专门控件、失败片段浏览器及独立审计证据面板仍未交付，不把文档整理视为实现。

本轮复核还修正了网页clean的原生函数签名与版本传递。原生捕获的API/JSON运行错误保留原JSON标签，派生TSR/ASR排除错误行，另报total/planned、utility_valid/security_valid及execution_errors；Token不删除。历史页不从相邻场景推定缺失身份，export schema2保留四项组件哈希。
