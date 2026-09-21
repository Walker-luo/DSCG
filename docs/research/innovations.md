# DSCG 当前框架的创新点梳理

> 本文只总结当前代码已经实现、可以被测试和复现实验支撑的机制。它不是论文定稿，也不主张“首次”“彻底解决”或形式化安全保证。最终创新性需要结合完整文献检索、基线和消融实验确认。

## 一句话定位

DSCG 将间接提示词注入防御从“让模型判断一段内容是否恶意”推进为“让模型提出候选动作，由确定性授权、统一仲裁和一次性执行票据控制真实副作用”。核心对象是任务授权契约、动作账本和 Reference Monitor，而不是某一个安全 Prompt。

## 已实现的机制

### 1. 授权与候选生成解耦（P0.2）

`ToolAuthorizationCompiler` 在主模型生成工具调用之前，根据当前可信用户消息、固定系统策略和宿主工具目录生成不可变的 `ToolAuthorizationContract`。assistant/tool 历史和主模型首轮候选不会进入授权输入，因此模型不能通过输出工具名给自己扩权。

可验证证据：授权编译发生在首次候选生成之前；污染的 assistant/tool 历史不能改变契约；每个新用户回合会撤销并重新编译旧授权。

### 2. 统一 Reference Monitor 与一次性执行票据（P0.3）

所有候选批次统一经过 `ReferenceMonitor`。它先对整个批次完成工具注册、授权状态和审计信号判定，再为批准动作签发绑定调用指纹、契约版本和 nonce 的 `ExecutionTicket`。`TicketedToolsExecutor` 是真实 `ToolsExecutor` 的唯一包装入口，缺失、篡改或重放票据不能触发真实工具。

这使“先产生 allow 决策，再执行”从约定变成可测试的不变量，并覆盖 Checker 反馈、重试、纠错和并发批次路径。

### 3. 面向安全属性的动作账本

`ActionLedger` 为每个候选动作分配 `action_id`，并维护显式状态机：

```text
proposed -> approved -> executed
         -> blocked
approved -> failed
```

非法转移（例如 `blocked -> executed`）会被拒绝。账本中的参数只保存摘要，评测轨迹保存状态、授权契约版本和机器可读 `reason_code`，减少把敏感正文写入日志的风险。

### 4. 审计模型降级为风险信号，而非执行权

`ActionSecurityChecker` 可以检查多步动作链和外部数据诱导，但不再直接调用主模型生成纠错动作。它只提交与当前候选批次指纹绑定的 allow/deny 信号；阻断结果由受控执行器转换为工具错误，后续主模型重规划仍需经过完整仲裁链。

这保留了异构安全模型对复杂逻辑滥用的检测价值，同时避免 Checker 成为绕过 Sandbox 的第二执行入口。

### 5. 安全失败和可复现实验记录

P0.1 的显式策略状态（`uninitialized`、`initialized_empty`、`allowlist`、`error`）与 P0.2 的授权摘要、P0.3 的动作账本一起写入 AgentDojo 轨迹。解析失败、未知工具、异常审计、缺失票据和票据重放默认拒绝；离线测试使用真实 `FunctionsRuntime` 验证无副作用路径。

## 与现有工作的关系和可主张程度

当前更适合主张“execution-centric、contract-aware 的系统组合与可验证实现”，而不是单独声称每个组件都是全新算法。潜在论文贡献可以组织为：

1. 一个将任务级授权、模型候选、风险审计和真实工具执行分层的 IPI 防御架构。
2. 一个把完整仲裁不变量具体化为不可变授权契约、批次级 Reference Monitor、一次性票据和动作状态账本的实现。
3. 一套能同时衡量安全性、效用、误拒绝率、延迟、token/成本和审计完整性的 AgentDojo 评测方法。

这些主张仍需要与 AgentDojo 原生防御、工具过滤器、提示增强、Task Shield/ACE/IPIGuard 等相关基线进行同套件、同任务和消融对比。

## 当前边界与下一步

- P0.5：移除工具名前缀推断，改用显式 effect/source/sink 元数据。
- P1：把工具名授权扩展为参数级 Task Contract，并在票据中绑定规范化参数。
- P2：为读取数据、外部内容和 sink 建立 provenance ledger，实现 source-to-sink 约束。
- P3：处理确认、委托、多 Agent/MCP 和无工具 IPI 攻击。
- P4：完成攻击矩阵、误拒绝率、置信区间、成本和跨模型泛化实验。

在这些证据完成前，本文中的“创新点”应作为研究假设和工程贡献候选，而不是最终论文结论。
