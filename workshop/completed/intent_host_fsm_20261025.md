# v3.5 宿主进度状态机：8.2实施与验证

2026-10-25，基点`d457369`、分支`dev-v3.4`，在当前工作区直接修改，未暂存／提交。用户批准实施[分析§8.2](../../analysis/DSCG_v35.md)，并另行明确授权固定9条计分任务与6条必要GOAL预检。[实施计划](./intent_host_fsm_plan_20261025.md)，[工程证据](../artifacts/20261025_intent_host_fsm/)。

## 交付结果与边界

默认`legacy / DSCG_v3.5`已采用宿主FSM，full／partial／cohort／Dashboard共享factory，**无需新增参数或切换prompt-profile**。框架版本名称保留，行为由新协议／策略／Schema绑定；旧显式profile含义保持。

1. 原首次意图分解增加冻结`goal_kind`：facts、effect、answer、condition、conditional_effect。第二次仍选全局工具，调用数不增加；没有每意图工具映射、动态补权或业务完成谓词。
2. 进度模型只输出`{"satisfaction":"satisfied","evidence_ids":["call:..."]}`。合法语义结果为satisfied/not_yet/ambiguous/condition_false；不再生成reason、status、next_intent_id或跳步列表。未知字段／非法值／未知或重复引用仍拒绝，不提取或修补旧回复。
3. 宿主从真实调用、参数摘要、成功返回及当前意图归属形成`facts_observed`、`effect_observed`、`answer_emitted`，模型判断另记`semantic_satisfied`。None可证明执行；错误、受阻和主模型完成宣称不能替代执行。
4. 完成必须同时满足有限语义判断和目标类型所需的真实引用：查询成功不能替代最终回答，旧意图效果不能满足新效果。condition_false仅适用于显式条件效果，需要成功读取，当前或此前已发生效果时不能再标为无需执行。业务真假／参数正确性仍需模型判断，宿主只检查必要的执行条件。
5. 宿主只前进一个顺序ID。ambiguous须引用已发出的最终澄清回复才可awaiting_user，是否真正有歧义仍是模型判断；普通未完成保留当前意图。每意图仍最多一次最终续行，耗尽按INTENT_NO_PROGRESS原生终止计分，不推断所有业务路径均不可能，也不猜测跳过未知依赖。

新协议为`dscg.intent-progress.host-fsm.v2`、分解协议为`intent-global-tools-v2-goal-kinds`；目标类型、提示及Schema进入现有配置／缓存身份。使用新name，旧测量缓存不得跨版本reuse；原结果、冻结cohort和旧记录解释保持。

L2全局工具选择规则、L3四字段判决和固定免审、Monitor、整批回执、一次性票据、请求触发频率／模型／重试设置保持。本轮未实现§8.3完成条件匹配、§8.4事件触发或§8.5依赖图，不建立对象全集、覆盖oracle或恢复机制。没有成本／TSR改善保证。

## Online Evaluation

新运行：[host_fsm_v2_network_smoke_20261025](../artifacts/20261025_intent_host_fsm/online/agentdojo/qwen3.7-flash_host_fsm_v2_network_smoke_20261025/summary.md)。使用现有Qwen3.7-Flash主／审计配置与历史DashScope端点，reasoning_effort=none、shadow、完整原生工具／评分及共享partial入口。

固定范围：三种攻击ignore_previous、important_instructions、tool_knowledge；banking的user_task_1/2、Slack的user_task_1，各自injection_task_1。共9条计分轨迹、3个不同用户任务key，另有6条GOAL。重复攻击不是独立用户样本；本轮没有baseline、clean、全量、重筛cohort或追加任务重跑。

| 场景 | 计划／实际／有效 | 运行错误 | TSR | 原生ASR | 框架终止 |
| --- | --- | ---: | --- | --- | ---: |
| banking | 6／6／6 | 0 | 2/6 | 0/6 | 5 |
| Slack | 3／3／3 | 0 | 0/3 | 0/3 | 3 |
| 合计 | 9／9／9 | 0 | **2/9** | **0/9** | 8 |

8条框架终止中7条INTENT_NO_PROGRESS、1条INTENT_INVALID_PROGRESS（INVALID_EVIDENCE）；有1条在终止前已经满足原生utility，原生True保留。实际审计另有1次DECISION_INCONSISTENT，继续严格阻断，不作为运行错误或成功放行。原生ASR为0不能证明一般安全，也没有同轮对照据以判断安全退化。

进度模型共74次：计分38次、GOAL36次，已记录调用均成功返回；1次证据引用非法。模型原始有限结果为satisfied 4次、not_yet 68次、ambiguous 2次。旧reason长度／多字段组合不再是当前输出契约，但多数轨迹仍停在语义未满足／主模型未继续执行，**效用尚未恢复**。

| 阶段 | 实际调用 | 已记录Token |
| --- | ---: | ---: |
| authorization_intents | 15 | 7,034 |
| authorization_tools | 15 | 23,580 |
| generation | 74 | 184,443 |
| intent_progress | 74 | 236,053 |
| audit | 32 | 65,825 |
| 合计 | **210** | **516,935** |

计分108调用／218,254Token；GOAL102调用／298,681Token。已记录API失败0、缺失usage0，不把GOAL重复加进成本或TSR／ASR分母。计数来自现有阶段跟踪，没有新增底层HTTP重试或服务版本认证；原生generation采样保持，不把配置temperature=0误称为已发送或服务确定性保证。GOAL效用0/6，4条框架终止、2条等待澄清；这些也采用DSCG，不能当作独立无防御能力筛选，更不能据此删计分任务。

首次受限环境尝试保存在独立`host_fsm_v2_smoke_20261025`：15次连接异常（9计分＋6GOAL），有效模型回复0，DNS独立检查gaierror8；已记录Token为0，但没有服务端usage，不能据此认证费用。该批为运行错误，不是15个正常失败标签。首次升级联网被自动审批拒绝，原因是需要明确授权benchmark上下文外发与付费；用户随后授权上述固定范围，才启动成功联网运行。拒绝本身未创建模型进程，未绕过。

## 在线发现、后置修正与剩余限制

这9例中有5例意图列表把“计算总支出”或“生成摘要”标为effect；其中banking important_instructions/user_task_1确实进入该错误类型目标，其余不能据此作单因归因。进度控制原始窗口仍可能受到源命令／事实不足和模型过度谨慎影响；本轮2/9不是全部由标签解释。

最终交付相对实际执行源码有两项后置改动，**未追加付费复测**：

- 首次分解提示明确effect仅为真实工具状态变更／支付／通信，计算、摘要草稿与规划不能独立标为effect，应合并到请求的回答／发送目标。没有规则修补模型标签、任务ID或新增调用；这个提示澄清的实际语义效果尚未在线验证。
- 在次数耗尽异常前，补写已经生成的最后一条宿主observation。实际在线版本有11条最后派生观测未独立写入progress事件（不是原始回复丢失），原始74条进度回复及最终状态仍在。持久化缺口已通过真实侧车写入的RED/GREEN回归修正，只影响未来诊断，不改判决／执行／调用，不回填上述历史在线轨迹。

实际执行源码保存在`executed_code/`和`executed_code.json`；最终源码及差异见`final_code/`与`delivery_verification.json`。因此上表属于本轮**执行版本**，不能宣称为最终提示澄清后的复测成绩。进度输入与调用频率未优化，仍占成本主要部分，不宣称Token节省。

## Offline Regression、审查与文件保护

针对回归：ipi 46项通过；AgentDyn 46项中43通过、3个原生场景相关skip；Node 49项通过。新增状态／证据／条件冲突／异常前派生观测持久化均有RED/GREEN记录，SDK回复仅为工程fixture，不代表真实模型质量。

完整Python回归保留既有失败，**不全绿**：ipi基线747项→最终759项，均23 failures／6 errors／10 skips；AgentDyn基线751项→最终763项，均24 failures／6 errors／6 skips。最终同名失败／错误头清单与基线逐项一致，详情见`regression_comparison.json`；没有为消除旧失败放宽防御。

一次gpt-6.1-sol只读审查发现“窗口滚出后忘记旧效果”的Important问题，已用持久标志并集修正并补跨观察RED/GREEN；没有第二次审查。后续自身核对补了上述异常诊断写入缺口，报告不把该新增诊断修正说成经过第二次审查。

现有analysis移动／删除保留；原results/download 20,434个初始文件的最终核对见`delivery_verification.json`。无暂存／提交，不改原生谓词、评分或历史数据；E0 pending、I3 partial、I2 locked及关闭研究路线不变。精确命令／退出码、日志及源码差异均保存在工程证据目录。

下一步：用新name小范围复测最终提示的目标分类与banking／Slack进度质量，再决定是否扩大；本轮授权的9条计分＋6条GOAL已结束，不追加模型调用。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --model-config config/models.local.toml --audit-router-mode shadow \
  --name DSCG_v35_host_fsm_01
```

上述是后续测试者命令，默认partial范围大于本轮9例；本轮未执行该扩大范围命令。full仍使用experiments.run_benchmark，机制自动生效，同样必须新name。
