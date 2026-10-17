# 当前框架与平台展示交接

更新时间：2026-10-17（目录与文档整理，运行机制未变）。当前默认版本 **three-layer-v3.1**。本次用户授权实现有限L1结构化投影，沿用L2工具视图/任务文件与L3动作正文审查；默认投影已接入factory、partial和网页API，架构说明同步。Spotlighting风格来源封装仍是不适用输入的回退。正式研究路线和闸门不改变。

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

L1不增加独立模型调用：明确的原生银行月支出任务保留全部交易六字段，省略subject自由文本；其他输入保留原来源封装，原历史与L3正文保持。投影不是事实认证或范围授权。当前规则要求日常任务/摘要中的无关注入提醒使用概述，避免转述攻击目标；用户明确要求的分析/安全报告/必要引用仍支持原文。该日常输出规则仍是规划提示；有限投影只改变支持域内的工具视图，最终文本没有新增过滤器。L3仍审计当前动作，外发同时审查正文与目的地；安全提醒若夹带无关攻击链接/目标也可能越出任务，必要来源链接及显式安全分析可以保留。API默认纯算法路由off，full/partial的DSCG CLI默认shadow，baseline/NoChecker自动off；重审0、completion_prompt=false；公开sink-free读取免审是既有行为。有效deny对已授权sink-free读取仍可能被原Monitor的READ_ONLY_SOURCE_ALLOW覆盖，abstain/错误阻断。对象/目的地/参数/数据权限未强制约束，最终纯文本回答不经动作审计。

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

## 验证与后续工作

历史工程过程和统计集中保留在workshop：[v2.2显示与版本身份](../workshop/completed/dashboard_v22_20261013.md)、[L1投影实施](../workshop/completed/l1_projection_20261013.md)、[v3.1 clean修正](../workshop/completed/clean_utility_20261015.md)及[准备读取候选撤回](../workshop/completed/read_discovery_20261016.md)。旧144条v2.2实验不能重新标记成当前版本；离线检查不证明模型收益或真实E0通过。

当前真实E0仍pending，I3为24个有效探针/8个范围缺口/0个工具边界缺口，I2仍locked。后续工作按 [研究路线](../../research/technical_route.md)选择，保留原始评分、数据与版本身份。

框架优化可用partial的场景选择和冻结cohort；正式full及全用户筛选测量保持独立，具体命令和分母见 [小批量测试指南](./partial_benchmark.md#对照与输出)与[全量指南](./benchmark.md)。新对照使用新run名，Agent产物写入新的workshop/artifacts目录。CSA网页专门控件、失败片段浏览器及独立审计证据面板仍未交付，不把文档整理视为实现。
