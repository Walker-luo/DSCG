# 当前框架与平台展示交接

更新时间：2026-10-12。当前默认版本 **three-layer-l2-v2**。用户明确要求按 [L2_opt.md](../workshop/L2_opt.md)优化第二层，本轮已接入授权工具视图、有限宿主 profile、有界任务文件展开和平台控件。正式研究路线、创新判断和实验闸门不改变；本轮不是模型效果评测。

## 实际运行顺序

```text
普通任务：真实 user → L2 编译 → 有效授权工具视图 → 主模型候选
委托任务：明确执行文件 → 仅准备读取权限 → 原中介执行读取
                          → 原要求 + 完整文件任务 T_eff → L2 编译 → 主模型候选
共同循环：候选 → L2 整批前置 → L3 → Monitor → 一次性 ticket → 执行
              ↑                                                ↓
              └──── 主模型规划 ← L1 工具返回来源隔离 ← 结果/错误 ──┘
```

L1仍是零独立模型调用的软来源封装，原历史与L3正文保持。L3仍审计当前动作，默认纯算法路由off、重审0、completion_prompt=false；公开sink-free读取免审是既有行为。有效deny对已授权sink-free读取仍可能被原Monitor的READ_ONLY_SOURCE_ALLOW覆盖，abstain/错误阻断。对象/目的地/参数/数据权限未强制约束，最终纯文本回答不经动作审计。

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
| L1/input_isolation | true，网页/API | 主模型来源隔离视图 |
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
| 架构弹窗和实际循环 | 已更新three-layer-l2-v2，含视图、任务文件、profile范围和执行基础设施；[index.html](../dashboard/templates/index.html) |
| 网页开关到factory | 已接线并覆盖配置依赖、保存配置显示；[evaluation.py](../dashboard/evaluation.py)、[app.py](../dashboard/app.py) |
| 历史分析下载、多指标分图 | 既有实现保留，本轮Node回归；不会将旧结果改标为新版，也不迁移原始数据 |
| L2记录与覆盖 | 已接线，缺失历史字段保持缺失；[控件/trace检查](../tests/test_l2_controls.py) |
| CSA专门控件、独立失败片段浏览器 | 仍未实施；API/partial CSA能力不能当作网页已提供 |

前序交接和历史截图见 [工作台报告](../workshop/completed/dashboard_framework_ui_20261010.md)、[文档清理报告](../workshop/completed/framework_docs_cleanup_20261010.md)。本轮不向其他对话发任务、不重启用户服务；运行中旧服务须重载、浏览器刷新才能显示新源码。

## 验证及下一步

本轮完整命令、退出码、源码revision、未提交状态、artifacts/hashes和样本分母见 [L2实施报告](../workshop/completed/l2_implementation_20261012.md)。新证据在 `workshop/artifacts/20261012_l2_implementation/`，原始文档字节在 `workshop/archive/l2_implementation_20261012/`；旧报告/manifest不改写。

没有外部模型调用或真实benchmark。本地检查验证中介与配置，不能证明总Token、TSR/ASR改善。真实E0仍pending，I3仍partial，I2locked/closed路线不变。按 [implementation_status](../../research/paper/implementation_status.md)回报工程证据，不修改 [technical_route](../../research/technical_route.md)。

下一步先固定L1/L3、关闭任务展开，用新名称跑工具视图A0/A1匹配对照，检查独立终态、TSR/nativeASR、总/分阶段Tokens和延迟；再选择真实宿主profile评测B0/B1。委托任务另列准备读取/审计、有效任务长度和业务编译成本，不能把少做任务当作节省。Agent临时partial实验必须显式传新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`，用户results/download完整保留。
