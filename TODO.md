# DSCG 防御框架优化与论文路线

> 目标：将当前的“动态工具白名单 + 状态化 LLM 审计”原型，升级为一个以确定性执行约束为安全根、兼顾可用性与开销的间接提示词注入（IPI）防御框架。
>
> 论文主线候选：**Provenance-aware Dynamic Capability Graph**（面向数据来源的动态能力图）。

## 0. 当前定位

当前框架包含以下机制：

- `OurFrameExecutor`：根据原始用户请求生成写工具白名单。
- `PermissionSandbox`：在工具执行前检查工具名，并裁剪未授权动作。
- `ActionHistoryTracker`：保存历史工具名和参数。
- `ActionSecurityChecker`：在出现写操作时，结合原始请求和动作历史进行 LLM 审计。
- Mock Error / Retry：拦截违规动作后让主模型重新生成答案或动作。

当前版本适合作为实验原型，但还不能把 LLM 审计、动作历史或工具名白名单描述成严格的安全边界。下一阶段的原则是：

1. LLM 负责提出候选计划，确定性策略层负责批准执行。
2. 所有动作都必须被完整仲裁，包括重试、恢复和并发动作。
3. 外部数据可以帮助补全任务参数，但不能自行扩大 Agent 权限。
4. 权限判断从“工具名级”推进到“操作 + 参数 + 数据来源 + 当前状态”级。

---

## P0：修复安全正确性问题

这些问题会直接影响现有实验结论，应在扩展功能前完成。

### P0.1 白名单必须 fail-closed

- [ ] 修复 `PermissionSandbox` 中空列表代表全放行的问题。
- [ ] 明确区分：
  - `None`：策略尚未初始化，拒绝所有有副作用的动作；
  - `[]`：策略已初始化但未授权任何动作；
  - 非空列表：仅允许列表内动作。
- [ ] 意图解析超时、JSON 错误、模型拒答、工具不存在时，一律进入安全失败状态。
- [ ] 增加单元测试：空白名单、解析异常、未知工具均不能触发真实工具执行。

### P0.2 移除“先生成、后授权”

- [ ] 删除 `allowed = set(first_turn_tools)` 这种首轮候选动作自动进入白名单的逻辑。
- [ ] 白名单或 Task Contract 只能由可信用户消息和可信系统上下文生成。
- [ ] 主模型生成的工具调用只能作为候选动作，不能反向影响自己的权限。
- [ ] 意图解析应发生在第一次工具调用生成之前。

### P0.3 保证 Complete Mediation

- [ ] 禁止 Sandbox 或 Checker 内部生成的新工具调用直接进入 `ToolsExecutor`。
- [ ] 将恢复流程改为统一事件循环：`生成候选动作 -> 策略检查 -> 执行/拒绝 -> 再规划`。
- [ ] 重试动作、纠错动作、并发动作和 Mock Error 后动作必须重新经过全部检查。
- [ ] 为每个动作分配唯一 `action_id`，记录其 `proposed/approved/executed/failed/blocked` 状态。
- [ ] 增加测试：安全模块触发重试后生成未授权工具，必须再次被拦截。

### P0.4 审计模型结构化输出并默认拒绝

- [ ] 将自由文本 `SAFE/UNSAFE` 改为严格 schema，例如：

```json
{
  "decision": "allow | deny | abstain",
  "violations": ["unauthorized_recipient"],
  "confidence": 0.0,
  "reason_code": "ARGUMENT_OUT_OF_SCOPE"
}
```

- [ ] 解析失败、`abstain`、字段缺失和模型超时默认拒绝高风险动作。
- [ ] 不把未经处理的工具参数直接拼入安全 Prompt。
- [ ] 审计器只接收规范化字段、来源 ID 和策略特征；必要的原文放入明确的数据字段。
- [ ] LLM 审计只作为补充判据，不作为唯一安全根。

### P0.5 修正工具风险分类

- [ ] 移除通过 `get_`、`read_`、`download_` 等前缀推断读写属性的方式。
- [ ] 为每个工具注册显式安全元数据：

```yaml
effect: read | write | delete | financial | external_send
source: calendar | email | cloud | web | local
sink: none | external_recipient | public_output
sensitivity: public | internal | personal | secret
idempotent: true | false
reversible: true | false
```

- [ ] 未注册元数据的工具默认按高风险处理。
- [ ] 区分公共读取、敏感读取、外部发送、不可逆删除和金融操作。

---

## P1：实现参数级 Task Contract

工具级白名单只能回答“能否调用 `send_email`”，无法回答“能发给谁、发什么、发几次”。需要在读取不可信数据前，从原始用户请求生成不可变的任务契约。

### P1.1 Task Contract 数据结构

- [ ] 定义 Pydantic 模型，至少包含：
  - 允许的操作类型；
  - 允许访问的资源范围；
  - 参数约束；
  - 允许的数据来源；
  - 允许的数据去向；
  - 最大调用次数或金额；
  - 有效期；
  - 需要用户确认的条件；
  - 是否允许从外部数据补全特定参数。
- [ ] 保存原始用户请求、规范化意图和 Contract 的哈希，运行过程中不可被工具输出修改。
- [ ] Contract 编译失败时允许继续纯文本回答，但禁止产生外部副作用。

示例：用户要求给 Alice 发送一封会议提醒时，权限应类似：

```yaml
operation: email.send
recipient:
  allowed_values: [alice@example.com]
subject:
  source: trusted_user_or_fixed_template
body:
  allowed_sources: [trusted_user, calendar_event]
max_calls: 1
allow_untrusted_instruction_expansion: false
```

### P1.2 确定性 Reference Monitor

- [ ] 在真实 `ToolsExecutor` 前建立唯一、不可绕过的策略入口。
- [ ] 检查工具 effect、参数值、资源范围、调用次数、任务状态和数据来源。
- [ ] 对每个拒绝给出机器可读 reason code，不依赖自然语言错误文本。
- [ ] 将安全检查和恢复提示解耦：策略层负责判决，恢复层负责提高 utility。
- [ ] 对高风险动作支持 dry-run，在真正提交前展示规范化效果。

### P1.3 单调能力状态机

- [ ] 将任务计划表示为 Capability Graph，而不是一次性全局白名单。
- [ ] 每个节点描述允许的 effect、前置条件、参数约束和完成条件。
- [ ] 只有前置节点成功后才能激活下一节点。
- [ ] 外部观察只能缩小或消费权限，不能增加权限：`C_(t+1) <= C_t`。
- [ ] 新增权限必须来自新的可信用户消息或显式确认。
- [ ] 只读节点的动态扩展也必须受资源范围和敏感级别约束。

---

## P2：实现 Provenance 与信息流约束

### P2.1 将 ActionHistoryTracker 升级为安全账本

- [ ] 记录候选动作、批准结果、真实执行结果和失败原因，而不只是工具名与参数。
- [ ] 为每个工具输出分片分配 `source_id`。
- [ ] 记录来源工具、资源 ID、信任级别、敏感级别和产生时间。
- [ ] 记录每个写参数依赖了哪些用户字段、工具输出分片或模型推断。
- [ ] 账本由执行层写入，主模型只能读取，不能修改。

建议事件结构：

```json
{
  "action_id": "a-17",
  "tool": "send_email",
  "status": "blocked",
  "arguments": {},
  "argument_provenance": {
    "recipients": ["tool-output:mail-42#chunk-3"],
    "body": ["trusted-user:turn-1"]
  },
  "policy_decision": "UNTRUSTED_DATA_CONTROLS_EXTERNAL_SINK"
}
```

### P2.2 Source-to-Sink 策略

- [ ] 定义敏感 source：邮件、云文件、账户信息、联系人、私有日历等。
- [ ] 定义危险 sink：发邮件、发消息、HTTP 请求、上传、公开回答、转账等。
- [ ] 默认禁止敏感 source 流向未授权 sink。
- [ ] 默认禁止不可信内容决定收件人、支付对象、删除目标和权限变更对象。
- [ ] 允许用户在 Task Contract 中显式授权特定流，例如“把报告内容发给 Alice”。
- [ ] 研究显式流与控制流依赖；先实现可解释的显式传播，再考虑近似隐式流。

### P2.3 不使用 embedding 充当污点证明

- [ ] embedding 相似度仅作为语义告警信号，不作为 provenance 主机制。
- [ ] 通过结构化引用和运行时依赖记录建立因果来源。
- [ ] 评估改写、翻译、摘要、编码和分块后 provenance 是否仍能传播。
- [ ] 对无法可靠确定来源的参数标记为 `unknown`，高风险 sink 默认拒绝或要求确认。

---

## P3：处理复杂授权与无工具 IPI

### P3.1 Delegation Envelope

解决“读取指定文件并执行其中指令”这类合法委托任务：

- [ ] 用户可指定某个资源为合法指令源，但必须同时限定其权限上界。
- [ ] 委托范围至少包含允许动作、对象范围、金额/次数、外发权限和有效期。
- [ ] 外部文件不能把自己的权限继续委托给第三方内容。
- [ ] 删除、支付、凭据操作和跨域外发默认要求用户确认。
- [ ] 对 `banking/user_task_12` 建立专项用例，衡量安全性与任务可用性的平衡。

### P3.2 无工具调用与只读攻击

- [ ] 覆盖虚假信息、恶意链接、系统提示提取、隐私披露和内容完整性攻击。
- [ ] 最终回答记录关键事实的来源，必要时只允许从结构化字段生成。
- [ ] 对外部内容中的链接、命令和身份声明保留 untrusted 标签。
- [ ] 防止敏感读取结果未经授权进入最终回答。
- [ ] 测试“没有写工具但仍造成泄露或误导”的攻击场景。

### P3.3 风险分级和用户确认

- [ ] 建立分级：公共读取、私有读取、可逆写入、外部发送、不可逆删除、金融操作。
- [ ] 用户确认界面展示实际 effect，而不是展示模型的自然语言解释。
- [ ] 确认内容包括目标、接收者、金额、数据来源和不可逆影响。
- [ ] 确认授权只对当前规范化动作有效，不能被后续动作复用。

---

## P4：测试与评测设计

### P4.1 安全不变量测试

- [ ] 空策略永不执行写动作。
- [ ] 未注册工具永不默认放行。
- [ ] 工具输出不能扩大 Capability Graph。
- [ ] 每个已执行动作都存在对应的 allow decision。
- [ ] 每个重试动作都有新的策略检查记录。
- [ ] 不可信数据不能未经授权控制高风险参数。
- [ ] 敏感 source 不能未经授权流向外部 sink。
- [ ] 审计模型失效时，高风险动作仍然安全失败。

测试层次：

- [ ] 单元测试：策略、参数约束、状态转换、provenance 传播。
- [ ] 集成测试：完整 Pipeline、并发工具调用、重试和部分裁剪。
- [ ] Property-based 测试：随机工具名、未知参数、动作排序和异常输出。
- [ ] 回归测试：每个曾经成功的攻击都保存为固定测试样本。

### P4.2 AgentDojo 主实验

- [ ] 使用完整四领域：Workspace、Slack、Travel、Banking。
- [ ] 不只选择前几个 user/injection task，运行全部有效组合。
- [ ] 覆盖所有适用攻击模板，而不只是 `important_instructions`。
- [ ] 至少选择 3 个主模型和 2 个不同规模的审计模型。
- [ ] 每个随机配置重复多个种子，并报告置信区间。
- [ ] 分开报告良性任务效用与攻击环境下任务效用。
- [ ] 对攻击能力不足的模型报告 conditional ASR。

主要指标：

- ASR：攻击成功率；
- Benign Utility / Utility Under Attack；
- False Positive / False Refusal；
- 高、中、低严重度攻击的加权风险；
- 用户确认次数；
- P50/P95 延迟；
- 主模型、安全模型和策略层的 token、时间与金额成本。

### P4.3 自适应攻击

- [ ] 白盒攻击 Task Contract 编译器。
- [ ] 在工具参数中注入审计器指令。
- [ ] 多个工具输出分阶段拼接 payload。
- [ ] 使用已授权工具，但替换收件人、对象、金额或正文来源。
- [ ] 工具描述、schema、错误消息和记忆中的注入。
- [ ] 诱导重试、循环、并发调用和权限耗尽。
- [ ] 跨会话记忆污染与持久化攻击。
- [ ] 对工具重命名，验证框架没有依赖名称前缀。

### P4.4 消融实验

- [ ] 无 Task Contract。
- [ ] 无 Capability Graph，仅静态参数策略。
- [ ] 无 provenance/source-to-sink 策略。
- [ ] 无 LLM Security Checker。
- [ ] 无恢复与细粒度裁剪。
- [ ] 不同风险阈值和确认策略。
- [ ] 比较确定性策略与 LLM 审计各自贡献及组合效果。

---

## P5：论文设计

### P5.1 建议研究问题

- RQ1：参数级动态能力约束能否比工具级白名单显著降低 IPI 的 ASR？
- RQ2：provenance-aware source-to-sink 策略能否防御同工具参数劫持和多阶段攻击？
- RQ3：单调能力图能否在安全性、任务效用和运行开销之间取得更好的平衡？
- RQ4：LLM 审计从安全根降级为辅助信号后，是否仍能提升对语义越权的覆盖率？
- RQ5：Delegation Envelope 能否处理合法的“按外部文档指令执行”任务？

### P5.2 可能的贡献点

1. **动态参数级能力图**：把用户意图编译成随任务状态推进、但不能被不可信观察扩大的能力边界。
2. **面向 Agent 动作参数的 provenance 约束**：追踪外部数据如何影响工具参数，并在危险 sink 前强制执行策略。
3. **完整仲裁的弹性执行循环**：所有正常、并发和恢复动作都经过相同检查，同时通过安全裁剪保持 utility。
4. **有界外部委托模型**：允许用户授予外部资源有限指令权，解决全拒绝与全信任之间的冲突。

创新性最终需要通过系统文献检索确认。在实现完成前避免使用“首次”“彻底解决”“唯一信任源”等绝对表述。

### P5.3 基线与对比对象

- AgentDojo 原生无防御与内置防御；
- Tool Filter / Prompt Injection Detector；
- Spotlighting / Delimiting / Repeat User Prompt；
- IPIGuard：重点比较固定 TDG 与动态单调能力图；
- IntentGuard：重点比较推理痕迹检测与执行层强制约束；
- ACE：重点比较重型 IFC/隔离与轻量运行时 provenance enforcement。

### P5.4 论文成立的最低条件

- [ ] P0 的完整仲裁和 fail-closed 测试全部通过。
- [ ] 至少实现 Task Contract、参数级 Reference Monitor 和显式 provenance。
- [ ] 在完整或有代表性的多领域基准上显著降低 ASR。
- [ ] 相比强基线没有不可接受的 benign utility 下降。
- [ ] 对多阶段、同工具参数劫持和审计器注入给出专项结果。
- [ ] 所有主要结论附带样本数、方差或置信区间。
- [ ] 代码、配置、攻击样本和原始结果能够复现。

---

## 推荐实施顺序

### 里程碑 M1：可信执行底座

- 完成 P0；
- 重构统一安全事件循环；
- 建立工具元数据与策略单元测试。

### 里程碑 M2：核心论文机制

- 完成 Task Contract；
- 完成参数级 Capability Graph；
- 完成确定性 Reference Monitor。

### 里程碑 M3：复杂攻击防御

- 完成 provenance ledger；
- 完成 source-to-sink 策略；
- 完成 Delegation Envelope 和用户确认。

### 里程碑 M4：系统实验与论文

- 固化攻击矩阵和回归样本；
- 运行主实验、消融实验和开销实验；
- 根据实验结果收缩论文 claim，整理威胁模型、算法和局限性。

## 暂不优先

- 不优先继续增加注入关键词和正则规则。
- 不优先扩大 Security Checker Prompt 长度。
- 不把模型异构本身视为可靠安全保证。
- 不在缺少 provenance 的情况下用 embedding 相似度声称实现了污点追踪。
- 不在只测试单领域、单攻击模板时声称达到通用防御。
