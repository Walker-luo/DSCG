# 当前框架与平台展示交接

更新时间：2026-10-10。当前默认为 **three-layer-v1 三层基础框架**。本次由用户明确要求按 [已归档三层基础方案](../workshop/completed/3_layer_opt.md)实施并同步网页；覆盖旧交接中“保持两层/网页不在范围”的限制。正式研究路线、创新判断和实验闸门仍未改变。

## 运行顺序与组件

```text
可信用户任务 → L2 授权编译（首次候选之前）
                     ↓
                 主模型规划 ← L1 工具返回隔离 ← 工具结果 / 错误
                     ↓                            ↑
                L2 候选前置检查                    │
                     ↓                            │
                L3 动作审计 → Monitor 复核 → ticket → 执行
```

编号是防御职责，不表示每轮调用三个模型。实现基线是 `8f608618171d4ffac8c8ec99d1278302282204fe`，本轮变更及源码哈希见 [实施报告](../workshop/completed/three_layer_implementation_20261010.md)。

### L1：主模型输入隔离

[dscg/input_isolation.py](../dscg/input_isolation.py)构造独立主模型视图：工具消息保持真实 role、tool_call_id 和 tool_call，正文加短宿主来源头尾，保留符以可逆映射转义。非空 error 在 AgentDojo 适配器中优先于 content，因此视图中的 error 也封装；原 history 的 error 不变。注册工具名来自实际 assistant 调用匹配，不相信正文或返回中的 name。系统数据边界说明每个实际请求只有一份；从原 history 重新构造，不层层嵌套。

原 tool history、原生任务 JSON 与 L3 最近返回窗口仍保留原正文。L1 不删除、摘要或截断工具内容，也不恢复被覆盖事实；这是软提示防护，不是事实认证、字段 provenance 或参数授权。普通姓名、ID、链接、金额保持文本原样；碰到保留符时模型可能误解转义，需要实跑引用/复制任务检查效用。

L1 无独立 API 调用，但其规则/封装随历史反复进入主模型输入。`dscg_input_isolation`记录累计主模型请求、结果呈现次数、转义次数和新增字符；字符数不是 Token 数。真实 Token 使用现有 tracker。

### L2：可信任务授权与确定性前置

沿用 `ToolAuthorizationCompiler`、`TrustedTaskRequest` 和 `PermissionSandbox`：真实用户请求、固定宿主策略与注册目录决定工具权限；工具反馈不能扩权。目录排序、temperature=0、条件任务语义和任务内编译缓存保留。新任务清空授权与票据。有效纯读取目录无需授权模型调用；包含动作工具时通常编译一次。

新增 `ToolAuthorizationPrecheck` 在 L3 之前检查每个真实候选：工具是否注册、当前权限状态/白名单、宿主风险元数据是否有效。任何成员失败则**整个批次拒绝**，包括其中原本可用的成员；所有候选仍进入 ActionLedger，逐个生成阻断结果，无工具副作用、无审计模型调用。不得误称保留了原混合批次的部分执行行为。

前置结果是宿主不可变对象，绑定原候选、沙箱状态/契约与当前工具目录（工具名、描述、参数 schema、函数和依赖的身份/定义）。Monitor 消费它并重新检查；候选、权限或目录变化，结果缺失/过期，均不签发票据。公开 JSON 的审计 allow 不能替代这个交接。L2 仍只约束工具，不新增对象、目的地或数据权限。

### L3：原当前动作审计

`ActionSecurityChecker`保留原职责：L2 通过后，有效公开 read 且 sink=none 沿用 `READ_AUDIT_BYPASS`；内部/个人/秘密读取、写入、外发与金融动作继续语义审计。公开读取免审是既有能力，不计新增收益。未知/无元数据在完整框架中已由 L2 拒绝。

原审计包仍包含可信任务、当前参数、有界动作记录、候选宿主描述（最多512字符）、当前任务最后4条原始不可信工具返回（每条最多2048字符）。不因 L1 封装改变审计窗口或事实；查询未知事实与后续写入分开判断。默认每批次至多一次审计；`abstain`、缺失/无效记录和模型/解析错误仍阻断。

原 Monitor 的 **READ_ONLY_SOURCE_ALLOW** 例外保留：已授权且无 sink 读取的有效审计 deny 仍可执行，不检查 deny 的具体理由。本次 L2 整批拒绝先于该例外，不能被它覆盖。必须区分原审计意见、最终执行决定和独立安全真值；“秘密读取仍审计”不等于 deny 一定阻止读取。

### 执行基础设施

Monitor 与一次性 ticket 不是第四层。ActionLedger 保留 PROPOSED → APPROVED/BLOCKED → EXECUTED/FAILED；Monitor 是唯一出票者，ticket 绑定调用指纹/契约/nonce/签名。所有执行通过 TicketedToolsExecutor；重放单独阻断，外层任务结束撤销未使用票据。工具错误或阻断后的新候选重新走完整边界。

## 默认配置、消融与版本

| 配置 | 默认 | 行为 |
| --- | --- | --- |
| `input_isolation` | true | 新增 L1；factory API 可显式 false 作匹配对照 |
| `authorization_precheck` | true | 新增 L2 候选前置；依赖 use_sandbox |
| `use_sandbox` | true | 原任务编译、沙箱、前置检查与最终权限仲裁 |
| `use_security_checker` | true | 原 L3；关闭后仍保留 L1/L2 |
| `audit_retries` | 0 | 不新增在线重审 |
| `completion_prompt` | false | 历史 Stage2 提示仍撤回 |
| `trace_level` | summary | full 仅诊断，增加序列化/写盘 |

页面现支持 L1/L2/L3 与 L2 前置检查配置及三层消融 / V2 对照预设；L2/L3 两者全关时 L1 也关闭。NoSandbox 不启用 L2，NoChecker 保留 L2；原生 baseline 始终用 AgentDojo 原工具循环，不带 DSCG 运行元数据。

运行 trace 记录 `dscg_framework` 的实际开关/version；`dscg_layer_routing`记录候选批次、L2允许/拒绝、既有公开读取免审和语义模型调用数。partial run manifest 写明新版本/L1/L2，并继续绑定任务、模型、攻击和源码 SHA；新旧配置不能复用同名缓存。全量跑批默认 pipeline 名包含版本与实际 L1/L2 开关，避免复用 V2 或其他消融缓存；显式 --name 会覆盖默认名，仍须用新名称。factory 的两个 API 参数可建立 V2 对照，现也已暴露为网页控件；它们尚未暴露为 partial CLI，不使用不存在的 flags。

## 平台交接核查（2026-10-10）

结论：**此前平台交付范围已落实**。已只读查询“dashboard optimize”对话最近完成记录，并对照当前源码与离线检查；三层架构展示由随后框架实施阶段补齐。没有向其他对话发送新任务。

| 交接项 | 当前状态 | 核查位置 / 证据 |
| --- | --- | --- |
| 三层架构弹窗、实际循环、Monitor单列与能力限制 | 已交付 | [index.html](../dashboard/templates/index.html)含L1/L2/L3；框架实施阶段有桌面/390px窄屏截图，本次Flask路由再检查正文 |
| 现有L2/L3开关接线与默认三层 | 已交付 | [app.py](../dashboard/app.py)把sandbox/checker传给factory；[defended.py](../dscg/pipelines/defended.py)启用L1/L2前置，两个旧开关全关时L1关闭 |
| 历史分析选择与下载ASR/TSR | 已交付 | `/history`、`/api/history/export`、[history_export.py](../dashboard/history_export.py)；ZIP含analysis.json、summary.csv、task_records.csv与README，缺失/错误/截断单列 |
| 多指标独立成图、实验身份与颜色映射 | 已交付 | [history_charts.js](../dashboard/static/js/history_charts.js)、[history.js](../dashboard/static/js/history.js)，既有Node检查本次重跑21/21 |
| 使用说明与运行状态同步 | 已交付 | README、AGENTS、[dashboard.md](./dashboard.md)、本文件和workshop两级索引 |

上述表格是文档交接阶段的核查；随后的用户授权 UI 更新已补齐**独立 L1 网页开关、前置检查开关、配置预设和三层统计面板**，详见[工作台实施报告](../workshop/completed/dashboard_framework_ui_20261010.md)。统计显示已计分 trace 覆盖与重复呈现字符，不是安全增益或 Token 节省的证据。**网页CSA模式、专门路由统计图和独立失败片段浏览器仍未实施**。partial 命令的注册顺序前缀选择与网页有限子集的 seed 排序是不同入口，跨入口对照需核对实际 task IDs。

当前源码已更新，运行中的旧服务若未重载，需重启面板并刷新才显示当前版本；本次不重启用户服务或启动模型评测。历史结果不迁移、不重算，也不重新标为三层。交接详情、原文归档与本次检查命令见 [文档归档/交接报告](../workshop/completed/framework_docs_cleanup_20261010.md)。

## 验证与后续工作

本轮以离线行为回归、真实本地工具副作用检查、已有 I3/E0 fixtures、Flask 页面/Node检查和独立代码审查验收；生成日志均在 `workshop/artifacts/20261010_three_layer_impl/`。精确命令、退出码、源码 SHA 和分母见实施报告。未调用模型 API 或运行真实 benchmark，不能宣称 ASR/TSR 或总成本改善。

用户已激活 ipi 时可直接运行：

```bash
python -m unittest discover -s tests -v
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline_3layer_01
python -m experiments.run_partial_benchmark --force-rerun --name three_layer_01
```

以上模型命令由用户选择预算后运行，本轮没有运行。临时 agent 实验必须另传新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`；默认首3 user/首3 injection、四 typical 攻击和144规划rollout保持。root results/download 留给用户正式运行与导出。

真实 E0 仍 pending；I3 已有24 valid/8 scope violations，仍 partial；I2 locked，旧 provenance/I1/I4/exactly-once 路线关闭。本次显式 workshop 工程实施不修改 [technical_route](../../research/technical_route.md)。按 [implementation_status](../../research/paper/implementation_status.md)追加证据，不自行宣布论文贡献或研究闸门通过。

后续先用新名字做匹配的原 V2、L1、L2前置、完整三层消融，报告真实终态、native ASR、TSR、总/分阶段Tokens与延迟；L1文本增量和混合批次整拒是主要待测代价。[L3纯算法路由](../workshop/L3_checker_opt.md)已接入API/partial CLI和原生trace/summary，默认off；网页专门模式/artifact控件、真实校准与端到端收益未验收。DRV、恢复回路、动态扩权未实施。

## L3纯算法交接（2026-10-10）

引擎新增 `audit_router_mode` 与 `audit_router_artifact`，partial CLI对应 `--audit-router-mode` / `--audit-router-artifact`；公共读取与L2拒绝不计作新增免审。summary.json的audit_router包含实际/潜在免审、有效覆盖、已知/未知审计成本和本地延迟。当前网页尚未暴露CSA专门控制，网页现有基础三层预设仍沿用off；不要将旧数据或普通路由面板当作已启用CSA。需要后续网页接线时沿用同一factory绑定，不能绕过校准条件。独立真实标签/部署artifact和匹配selective模型试验待完成。见 [实现报告](../workshop/completed/l3_algorithm_implementation_20261010.md)。
