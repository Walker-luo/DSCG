# 8.2 宿主进度状态机实施计划

> 执行方式：本会话按 executing-plans 直接实施，TDD 后进行一次只读审查；不暂存、不提交。

**Goal:** 将默认 v3.5 的确定性进度控制收回宿主，模型只提供有限语义判断。
**Architecture:** 在已有意图分解请求固化目标类型；宿主从真实执行账本／最终回答形成标志与合法证据，再把有限语义结果转为状态转换。L2全局工具、L3、Monitor、票据及现有请求触发频率不变。
**Tech Stack:** 现有 Python、AgentDojo／AgentDyn、JSON Schema、unittest。
**Spec:** [analysis/DSCG_v35.md §8.2](../../analysis/DSCG_v35.md)。

## 约束与设计决定

- 不实现8.3完成条件谓词、8.4增量触发或8.5依赖图；无新参数／动态授权／恢复，不引用标准答案或评分谓词控制运行。
- 首次意图分解增加goal_kind：facts/effect/answer/condition/conditional_effect；只表示目标交付形态，不证明分解或参数正确。
- 进度模型仅返回satisfaction及evidence_ids；satisfaction是satisfied/not_yet/ambiguous/condition_false。condition_false只适用于条件效果，仍需真实读取证据；模型对条件／歧义的语义判断仍可能错误。
- host维护facts_observed/effect_observed/answer_emitted/semantic_satisfied；成功None是执行事件，阻断、报错、缺归属／摘要不匹配不能成为本意图效果证据。
- satisfied不单独导致完成，须满足宿主目标形态／引用约束。ambiguous须有真实最终回复引用才可awaiting_user，不自行发确认；not_yet保持当前目标，沿用一次最终续行上限。
- 普通完成只前进一个ID。没有可信依赖信息时不跳过意图；耗尽是有界尝试停止，不推断业务上不可能完成。
- 新协议、Schema、行为和目标类型绑定现有身份；新运行名，历史结果／缓存／cohort不改写。默认legacy直接生效，旧显式profile含义不变。
- 使用当前工作区，保护现有移动；证据进入workshop/artifacts/20261025_intent_host_fsm/。

## Review Focus

- 错归属或旧效果不得满足当前目标；未来／未知／重复证据引用拒绝。
- 回答目标不能因查询成功或主模型宣称成功就完成；已发送的副作用不重放。
- 模型不能输出next ID、status、skip或自由解释作为控制字段；非法决策不修补。
- 条件未知／一次deny不能成为false条件或任务不可完成；歧义不是任意终止入口。
- NoChecker仍运行状态机，NoL2／受限宿主profile／旧profile保持边界，身份变化阻止旧测量复用。

## Task 1：目标类型与宿主FSM

Files: dscg/intent_flow.py、tests/test_intent_host_fsm.py。

- [x] 先添加可失败回归：查询≠交付、None成功／错误、旧效果、有限输出／严格引用、歧义／条件未知、串行前进／耗尽。
- [x] 在ipi运行新测试，保存RED；实现最小FSM及新协议，再保存GREEN。
- [x] parse_intents/compile_authorization传递文本及类型，不改变全局工具选择规则。

## Task 2：共享执行与诊断集成

Files: dscg/pipelines/defended.py、tests/test_intent_flow.py、tests/test_intent_flow_native.py、tests/test_task_diagnostics.py。

- [x] grant保留冻结goal_kind，两个IntentFlow创建位置一致；progress目录显示已冻结授权事实。
- [x] 适配已有协议fixture，验证full/partial/cohort共享factory、身份变化、票据／回执、原文先保存及失败计分。
- [x] 两环境针对回归；完整Python与Node检查保留已知失败集，不为旧失败改防御。

## Task 3：在线小样本、文档与交付

- [x] 用现有配置和共享partial入口完成至少9个计分任务；限定小范围跨场景／攻击，不跑全量，不重用关闭预算。记录GOAL、真实请求、usage、错误与原生标签；API不可用如实报告。
- [x] 同步README／指南／AGENTS／analysis状态，计划完成后移至completed，保留工程报告／一次审查及文件保护证据。
- [x] 语法、链接、diff、原结果哈希／Git index核对，说明没有建立完整基准效用／安全结论。
