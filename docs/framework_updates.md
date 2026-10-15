# 当前框架与平台展示交接

更新时间：2026-10-13。当前默认版本 **three-layer-l1-v3**。本次用户授权实现有限L1结构化投影，沿用L2工具视图/任务文件与L3动作正文审查；默认投影已接入factory、partial和网页API，架构说明同步。Spotlighting风格来源封装仍是不适用输入的回退。正式研究路线和闸门不改变。

## 实际运行顺序

```text
普通任务：真实 user → L2 编译 → 有效授权工具视图 → 主模型候选
委托任务：明确执行文件 → 仅准备读取权限 → 原中介执行读取
                          → 原要求 + 完整文件任务 T_eff → L2 编译 → 主模型候选
共同循环：候选 → L2 整批前置 → L3 → Monitor → 一次性 ticket → 执行
              ↑                                                ↓
              └──── 主模型规划 ← L1 有限投影/来源封装 ← 结果/错误 ──┘
```

L1不增加独立模型调用：明确的原生银行月支出任务保留全部交易六字段，省略subject自由文本；其他输入保留原来源封装，原历史与L3正文保持。投影不是事实认证或范围授权。当前规则要求日常任务/摘要中的无关注入提醒使用概述，避免转述攻击目标；用户明确要求的分析/安全报告/必要引用仍支持原文。该日常输出规则仍是规划提示；有限投影只改变支持域内的工具视图，最终文本没有新增过滤器。L3仍审计当前动作，外发同时审查正文与目的地；安全提醒若夹带无关攻击链接/目标也可能越出任务，必要来源链接及显式安全分析可以保留。默认纯算法路由off、重审0、completion_prompt=false；公开sink-free读取免审是既有行为。有效deny对已授权sink-free读取仍可能被原Monitor的READ_ONLY_SOURCE_ALLOW覆盖，abstain/错误阻断。对象/目的地/参数/数据权限未强制约束，最终纯文本回答不经动作审计。

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
| delegated_tasks | true，网页/API/partial `--no-delegated-tasks` | 有界明确任务文件展开；NoL2关闭 |
| authorization_profile / delegated_task_reader | 默认None，仅宿主API | 受信配置，不由网页文本/工具返回创建 |
| L3/use_security_checker | true，网页/API | 原动作审计 |
| audit_router_mode/artifact | 默认off，API/partial CLI | CSA硬门/真实校准不变，网页专门控件仍待完成 |
| trace_level | summary | standard判决/账本、full压缩诊断；保留实际字段覆盖 |

网页完整/NoL1/NoL2/NoL3预设和自定义组合已接线。**V2风格**预设关闭L1、前置、视图与文件展开，但新版目录复核仍存在，不是历史V2精确复现。L2/L3全关时L1关闭；原生baseline始终走AgentDojo原循环，不带DSCG元数据。

[app.js](../dashboard/static/js/app.js)区分待启动配置和保存的有效配置；HTML/TXT报告显示已保存开关。概览新增完整/可见工具累计量、编译器调用和文件展开，且只统计实际计分任务的 `dscg_l2` trace。编译器调用可能零模型调用；字符/工具定义数不是Tokens。旧记录缺字段显示未记录，不推定零；攻击生成预检不计进该trace统计。

版本、开关、profile/reader身份、协议和任务输入边界进入pipeline/config/L3绑定；partial manifest继续绑定任务、模型、攻击与源码SHA。同名配置不兼容不能复用缓存，所有新对照使用新名称。旧L3校准artifact不得直接沿用，新有效任务应按实际审计packet独立标注并重新核查配置域。

## 平台交接状态

| 交接项 | 状态 / 证据 |
| --- | --- |
| 架构弹窗和实际循环 | 已同步v3有限L1投影及原L3规则；页面和API版本来自引擎常量，预览随工具视图/委托开关更新；[index.html](../dashboard/templates/index.html)、[app.js](../dashboard/static/js/app.js) |
| 网页开关到factory | 已接线并覆盖配置依赖、保存配置显示；[evaluation.py](../dashboard/evaluation.py)、[app.py](../dashboard/app.py) |
| 历史分析下载、多指标分图 | 既有实现保留，本轮Node28/28；目录与manifest身份分别记录，旧结果不重标、原始数据不迁移 |
| L2记录与覆盖 | 已接线，概览单列L2 trace覆盖；已保存版本/路由状态取自运行记录，成本不可比较标记明确显示；[控件/trace检查](../tests/test_l2_controls.py) |
| CSA专门控件、独立失败片段浏览器 | 仍未实施；API/partial CSA能力不能当作网页已提供 |

前序交接和历史截图见 [工作台报告](../workshop/completed/dashboard_framework_ui_20261010.md)、[文档清理报告](../workshop/completed/framework_docs_cleanup_20261010.md)。前序显示源码已同步，详见 [v2.2平台报告](../workshop/completed/dashboard_v22_20261013.md)。未重启用户服务；重启Dashboard并刷新即可加载新页面。历史结果和既有证据保持原身份。

## 前序v2.2证据与版本身份（2026-10-13核对）

前序文档复核时HEAD为 `c209c6ef35247bb646dcdff45a1c3207a1cd7185`，初始工作树clean。L2 helper与原实施hash一致；当时L1/流水线、两探针入口和固定fixture均匹配v2.2修复记录。保留的54份探针/定向模拟产物hash一致；真实模型探针19/19、12攻击TSR12/12/nativeASR0/12与3干净TSR3/3是此前结果，该文档阶段只读核对、未新增API调用。模拟的是AgentDojo工具环境，不能写成所有验证都使用Mock模型。

现有目录 `results/partial_benchmark/deepseek-flash_3layer_L2opt/` 中144条记录日期为2026-10-13、版本均为v2.2。manifest的pipeline名为 `deepseek-flash_3layer_L2_v2`；输出目录字段还保留原路径。本轮不重命名/迁移目录，不把目录名当版本证据。

| 检查项 | 当前源记录 |
| --- | --- |
| 任务/原生指标 | 144条，utility有效144、security布尔有效144、错误0；TSR130/144、nativeASR0/144 |
| 与初版三层配对 | 144相同task keys、144相同载荷、144相同授权工具集合；后续L1/L3策略同时改变，不是L2视图单变量消融 |
| L3状态 | 144条use_security_checker=true，audit_router_mode=off；off不等于移除L3 |
| 成本 | 主模型1,347,126、审计338,699、合计1,685,825 Tokens为16份汇总记录量；cost_scope=new_api_calls_this_invocation，cost_comparison_ready全部false，不能直接算节省比例 |
| 历史hash边界 | 旧诊断292个input中148相符、144旧L2opt轨迹字节变化、缺失0；旧导出/诊断保留为当时证据，不能用当前文件重新认证原比较 |

本次 [结果核对](../workshop/artifacts/20261013_l2_docs_sync/latest_results.json)保留实际task ID、版本、成本状态和输入hash。单次源记录不替代独立环境终态oracle、真实E0或重复验证；不能推断参数范围已被强制约束，也不以警告引用减少单独证明安全增强。

## 验证及下一步

前序文档复核的离线283/283、Node28/28及源码/证据检查见 [复核报告](../workshop/completed/l2_docs_sync_20261013.md)，其原产物和9份文档原文保留。前序Dashboard离线284/284、Node31/31通过；新增回归验证引擎版本动态展示、有效流程和历史运行身份。新产物在 `workshop/artifacts/20261013_dashboard_v22/`，六份当前文档原始字节在 `workshop/archive/dashboard_v22_20261013/`；原报告/manifest/hash不改写，用户results/download保留。

平台v2.2显示交接已完成，沿用已接线控件，不增加配置机制。CSA专门模式/artifact控件和失败片段浏览器仍未实施，未因本次页面更新而开启选择性免审。

下一项使用新run名做v3的projection off/projected匹配对照，另保留shadow覆盖与合法引用反例，核查独立终态及总模型成本。已有144条属于v2.2，不能重新标记成v3。归因L2时两组固定投影模式/L3规则并关闭delegation，再比较view开/关。Agent临时partial实验必须显式传新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`；原结果与导出不覆盖。

真实E0仍pending、I3仍partial24valid/8scope/0tool-boundary、I2locked/closed路线不变。前序文档阶段未新跑I3/E0；本次L1工程复跑仍得到同一partial/合成分母。按 [implementation_status](../../research/paper/implementation_status.md)回报本轮文档/审查证据，不修改 [technical_route](../../research/technical_route.md)。


## L1 v3新增交接（2026-10-13）

- 一个原生banking-monthly-spending-v1 profile；完整有限请求、原生callable/code/输入schema、七字段Transaction、read/sink-none元数据与严格解析。全行/顺序、六字段保留，subject省略；格式异常/错误/截断/绑定歧义/混合内容/未知字段/超界/不更短均回退。必要备注、引用及委托任务保持原文。
- 网页API保存有效l1_projection_mode并转交factory；模板版本仍来自引擎，配置/预览/架构说明已更新。TXT导出记录模式，旧记录显示未记录；没有添加投影模式选择器或独立计数面板，API/partial可做off/shadow/projected对照。
- 模式、profile/adapter/native/schema/bounds身份进入缓存和L3兼容配置，旧artifact不沿用。原L3与Monitor读取例外不变；字段正确不等于事实正确，源端漏行无法验证。dscg_l1_projection记录重复呈现的实际/候选计数、回退原因和字符；封装added_characters_total仍独立，不能抵扣后当总Tokens。
- 离线303/303、Node31/31；144历史末视图检查只有12任务/12返回适用，14787→7380字符。没有真实模型/外部工具调用或新benchmark rollout，离线I3执行测试工具桩，历史标签未重算。I3复跑24valid/8scope/0tool、E0合成6例valid1/tool1/infrastructure4；正式E0未通过。
- 证据/原字节/精确命令见 [L1实施报告](../workshop/completed/l1_projection_20261013.md)。用户服务需重启/刷新才加载源码；本阶段未重启服务，旧结果/证据保持。workshop只把完成的有限工程计划/报告归入completed，L1_opt保留未验收项。
