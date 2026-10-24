# DSCG_v3.5 意图驱动执行实施记录

日期：2026-10-24。依据本轮批准的“意图驱动执行与读取免审”方案实施；没有付费调用、线上测试、暂存或提交。此前真实测试预算仍关闭。本次新默认与历史同名候选必须按有效 profile／协议身份区分。

## 交付行为

full、partial、cohort 共用的 `legacy` 默认现为 **DSCG_v3.5**；显式 `legacy-v34` 保留 v3.4 策略。baseline 继续使用原生流程。任务、攻击注册、原生评分、attack 并行、结果布局和冻结 cohort 轻量读取规则没有调整。

### L2：两阶段授权

1. `authorization_intents` 请求只返回 `authorization_steps: [{intent}]`。宿主严格检查 1–24 步、每项仅 intent、每项最多256字符，再按顺序分配 `intent_1…`。
2. `authorization_tools` 请求读取完整原请求、全部意图和原生工具目录，独立返回全局 `tools`。注册检查、自动读取权限及宿主上限继续生效。
3. 白名单启动时固定；切换、失败和工具返回不触发动态扩权。两阶段错误均终止本任务，不产生可执行授权。

宿主显式受限授权 profile 保留旧协议和权限上限，不启用自动意图切换；没有把普通编译失败降级为该路径。未匹配 profile 的原有回退实际使用旧 `CLASSIC_POLICY`，其身份也绑定该实际策略。

### 意图推进与提前结束

- 每批实际工具返回后，以主模型客户端独立调用 `intent_progress`。主模型同时保留完整请求、当前意图及完成／失败状态。
- 判断须引用真实消息／调用证据；效果完成还须存在**当前意图**下成功执行的效果性调用，正常 `None` 返回可作为证据。阻断、异常、主模型口头声称不能替代执行。
- 宿主拒绝未知证据、跨意图借用旧效果、回退、跳过未解释依赖及提前完成未来意图。失败可以推进到独立后续意图，依赖受阻单列。
- 最终文字回复也判断进度；每个意图最多一次继续反馈。真正需要用户选择时允许澄清结束；反馈已用尽而模型仍要求继续时，记有界 `INTENT_NO_PROGRESS` 错误。
- 进度证据窗口按最新内容优先分配容量后恢复时间顺序，保留截断标记；完整轨迹继续保存。信息回答／条件满足仍依赖模型的语义判断，引用存在不等于事实正确的证明。

### L3 与固定读取免审

L3 以当前 intent 为主要目标，保留完整原请求为不可覆盖约束；原生 Schema、实际效果和相关证据继续输入。保留严格四字段判决、Monitor 和一次性执行票据。

L2允许、Schema有效、已注册 `effect=read` 且 `sensitivity=public/internal` 的调用，直接免除 L3 模型请求，**不检查 URL来源／形式／sink**。三种 router 模式均如此；personal/secret 读取及效果性调用继续审计。新默认的敏感读取 deny 不再通过历史只读例外放行。

混合批次按原顺序执行，只审计非免审子集；拒绝写入不连带拒绝免审读取。完整批次回执同时绑定审计子集、意图状态、授权、工具目录及上下文；执行票据再绑定意图状态，切换后旧票据不可消费。

这是工具级规则，接受 internal 频道可能包含 private 对象、公开 URL 可能携带外发数据的局限；免审不代表经过语义安全认证。NoL2 按原请求审计，不启用意图推进；NoChecker 保留 L2 和意图推进。

## 定位入口

| 文件／函数 | 用途 |
| --- | --- |
| `dscg/intent_flow.py`: `compile_authorization`、`request_json` | 两阶段授权、显式输出 Schema、成本阶段、无重试请求 |
| 同文件：`IntentFlow.apply`、`observe`、`continue_once` | 严格状态转换、真实证据、一次继续反馈 |
| 同文件：`exempt_read`、`identity`、`decision_contracts` | 工具级读取规则及有效协议身份 |
| `dscg/pipelines/defended.py`: `ToolAuthorizationCompiler`、`OurFrameExecutor._generate_with_intents` | 共享 pipeline 编译及按意图执行 |
| 同文件：`ActionSecurityChecker._audit_packet`、`_query_intent_flow` | 当前意图／完整约束、混合批次审计 |
| 同文件：`ReferenceMonitor`、`TicketedToolsExecutor`、`_host_intent_binding` | 回执与执行边界 |
| 同文件：`make_qwen_newFrame_pipeline`、`router_configuration_hash` | 两入口共用默认及缓存身份 |
| `experiments/common/benchmark_tasks.py` | 任务级意图基础设施错误隔离，空评分标签，不伪造原生结果 |

新请求成本分别记入 `authorization_intents`、`authorization_tools`、`intent_progress`；不会把成功返回的 API 成本漏掉。新两阶段／进度请求禁用 SDK 重试，原生生成和已有 L3 重试选项保持原配置。此次没有新增生产模型参数、CLI 参数或后端源码修改，也不承诺总成本下降。

## 验证结果

所有 Python 验证均由本任务的 socket 禁用包装器执行；父进程及 spawn 子进程禁止联网，无连接尝试。离线使用真实安装套件、原生工具／攻击／评分，模型回复由内存 HTTP fixture 提供。

| 检查 | 结果 |
| --- | --- |
| 新意图流程定向检查（ipi） | 31项，通过，无跳过 |
| 新意图流程定向检查（ipi-agentdyn） | 31项，29通过、2跳过（AgentDojo专属真实场景） |
| ipi 完整回归 | 修改前698项：23失败／5错误／10跳过；修改后729项：23失败／5错误／10跳过 |
| ipi-agentdyn 完整回归 | 修改前702项：24失败／5错误／3跳过；修改后733项：24失败／5错误／5跳过 |

完整回归的失败／错误条目集合与修改前完全相同，**不能称整套回归通过**。旧协议 fixture 显式改用 `legacy-v34`；新默认由新两阶段／状态机／原生 HTTP 测试独立覆盖，没有把新默认响应自动转成旧协议。具体条目及对照见产物 `regression_comparison.json`。

原生场景 fixture 覆盖 banking `user_task_15 / important_instructions / injection_task_4` 和 Slack `user_task_4 / important_instructions / injection_task_1`，各包含合法动作及错误金额／错误发布地址的反例；同时验证完整成功和完整失败缓存均不新增请求。这些是宿主行为验证，**不是 Qwen 授权质量、真实 TSR／ASR 或整体安全性证据**。

## 最终审阅与限制

一次独立只读审阅发现受限 profile 回退策略／解析器不匹配、旧证据挤占新证据窗口两项问题；均先补失败复现再修复。另修正非最终阶段 needs_user 的提示／Schema矛盾，以及 JSON Object 请求未携带完整输出协议的问题。实际受限回退策略的身份绑定也有独立失败／通过检查。

保留一个轻微文案项：NoL2 下 `current_intent=null` 时，L3策略可更明确写出使用原请求；现有输入已完整保留 original/trusted request，且有无意图调用的专门测试。未以跳过校验处理该问题。

没有执行真实 benchmark、付费模型调用、Node 检查或线上恢复验证。未认证服务端推理设置、判断质量、TSR／ASR改善或工具级隐私安全。现有失败单列，不修改无关防御来使旧测试全绿。

## 使用与证据

默认新实验使用新名称，例如：

```bash
python -m experiments.run_benchmark --suites banking slack --progress --name DSCG_v35_intent_flow_01
python -m experiments.run_partial_benchmark --progress --name DSCG_v35_partial_01
```

v3.4对照加 `--prompt-profile legacy-v34` 并使用另一个新名称。旧测量缓存不能跨策略reuse，冻结cohort无需重筛。上述命令本次未运行。

证据：`workshop/artifacts/20261024_intent_flow_v35/`。其中保存修改前文件及哈希、失败／通过日志、完整回归前后对照、CLI帮助、原生fixture轨迹、文档和保护检查。保留工作区已有根文档删除／analysis迁移和 AGENTS 冲突标记，未暂存或提交。最终文件保护结果见 `verification.json`；不把并发文件变化归因于本任务，也不从快照恢复用户文件。
