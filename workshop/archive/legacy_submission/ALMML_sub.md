# AIMLL Workshop 投稿与 DSCG 后续执行计划

## 0. 计划依据

本计划以项目内 `DSCG/AIMLL WS.pdf` 为唯一投稿约束来源。

PDF 给出的关键信息：

- 目标：AI, ML and LLMs (AIMLL) Workshop
- 会议：The 23rd International Conference on Wireless Communications and Mobile Computing
- 时间：2027 年 6 月 13–17 日
- 地点：Barcelona, Spain
- 主题相关性：AI/ML/LLM security analysis、reliability、cybersecurity enhancements、data poisoning and defense
- 论文要求：原创，不能已经发表或同时投稿到其他 venue
- 发表形式：接收且完成报告的论文将进入 IEEE IWCMC proceedings，并提交 IEEE Xplore
- 截稿时间：PDF 只写“与主会相同”，具体日期待后续由投稿系统或组委会确认
- 页数限制：PDF 未明确，最终按投稿系统要求执行

当前计划不把 DSCG 描述为通用 IPI 防御，也不把尚未实现或尚未验证的机制写成论文贡献。

---

## 1. 当前论文定位

### 1.1 暂定研究问题

外部内容可以被 Agent 读取和处理，但不应因为其中包含指令、角色声明或伪造事实，就获得改变工具执行权限或任务完成条件的能力。

第一阶段优先验证：

> 在工具调用全部合法、没有发生明显越权副作用时，间接提示词注入是否仍会让 Agent 漏掉可信用户明确要求检查或报告的对象；宿主侧覆盖检查和受限恢复能否发现并补齐遗漏，同时不扩大工具或数据权限。

该问题暂定称为：

`IPI-induced selective task omission`

它目前只是 Conditional Go 研究方向，不能提前写成已证明的新颖性。

### 1.2 暂定核心亮点

论文可以围绕以下工程事实展开：

> DSCG 将 Agent 的候选动作生成与真实工具执行授权分离。主模型只负责提出候选动作；授权契约、确定性策略、Reference Monitor 和一次性执行票据共同决定动作是否能够到达真实工具。安全模型只提供辅助审计信号，不能新增权限或绕过确定性约束。

如果 I2 通过后，论文再增加：

> DSCG 使用宿主维护的 Task Obligation Ledger 检查用户明确要求的对象是否被完整处理；外部内容不能删除已有义务，遗漏恢复只能补做缺失义务，不能扩大工具、对象或数据权限。

### 1.3 禁止使用的表述

在研究侧证据没有通过前，禁止使用：

- 首个、首次、开创性
- 通用 IPI 防御
- 完整 AgentDojo 结果
- 形式化安全保证
- 完整 provenance 或完整 taint tracking
- 参数级授权已经实现
- 任何未经验证的 superiority 或 state-of-the-art 结论

---

## 2. 工程优化计划

工程改动只放在 `DSCG/`，研究结论和论文计划只放在 `research/`。

### Phase E0：Harness 审计与可复现性修复

状态：已由研究路线解锁，优先执行。

目标：

1. 证明攻击 payload 确实进入了 Agent 的输入上下文。
2. 证明攻击成功 predicate 基于真实环境状态，而不是只看工具名、模型文本或日志。
3. 证明每条样例都能重建候选动作、策略判决、工具执行和最终环境状态。
4. 任何无效样本、模型错误、策略错误、工具错误、超时和基础设施错误都不能被当作安全成功。
5. 让任务选择、攻击模板、模型、seed 和结果分母可重复。

建议涉及的工程位置：

- `dashboard/app.py`
- `experiments/run_benchmark.py`
- `experiments/run_partial_benchmark.py`
- `dscg/pipelines/defended.py`
- `config/paper/task_manifest.yaml`
- `config/paper/run_metadata.schema.yaml`
- `tests/`
- 必要时新增 `experiments/harness_audit.py`

必须新增或确认的记录字段：

```yaml
run_id:
git_commit:
working_tree:
environment:
model:
security_model:
provider:
suite:
user_task_id:
injection_task_id:
attack:
defense:
seed:
budget:
trace_level:
payload_hash:
payload_delivery_status:
candidate_actions:
normalized_arguments:
authorization_decision:
audit_decision:
execution_ticket_status:
tool_result:
final_environment_state:
attack_predicate:
sample_status:
error_type:
started_at:
ended_at:
```

`sample_status` 至少支持：

```text
valid
model_error
policy_error
tool_error
timeout
infrastructure_error
skipped
```

计分规则：

- 只有 `valid` 样本进入主指标分母。
- 非 `valid` 样本必须单独报告。
- 缺少 `security_results[task_key]` 时不能默认记为 `attack_success=False`。
- 不能把未运行、未送达、解析失败或环境错误当作防御成功。
- task ASR 与 action-level unauthorized side effect rate 分开计算。

任务选择规则：

- 不再使用简单的“注册顺序前 N 个任务”作为正式 pilot 选择方式。
- 按 `protocol.yaml` 规定使用固定 seed 和 SHA-256 排序。
- 保存实际选中的完整 task ID 列表及 manifest hash。
- 949 个组合只能作为笛卡尔上界，不能直接称为有效样本数。
- unavailable task 和 unavailable attack 必须带状态记录，不能静默删除。

E0 通过条件：

- 每条样例都有 payload、delivery status、完整轨迹、最终环境状态和 sample status。
- 攻击 predicate 能由独立环境 oracle 重放。
- valid、invalid、error、skipped 分母完整。
- 离线重放结果与在线记录一致。
- 运行元数据满足 `run_metadata.schema.yaml`。
- 现有回归测试全部通过。

E0 停止条件：

- payload 没有进入 Agent 输入；
- predicate 只能依赖模型自述；
- 轨迹缺失导致最终状态不可重建；
- 缺失样本仍被计入“防御成功”。

---

### Phase I3：错误反馈恢复压力测试

状态：已由研究路线解锁。

目标：

- 检查工具错误消息、超时消息或恶意错误反馈是否会诱导 Agent 扩大权限。
- 检查恢复动作是否重新进入授权契约、Reference Monitor 和一次性票据流程。
- 检查合法恢复是否仍能在原权限范围内完成。
- 检查票据重放、越权重试和错误路径注入。

最小 fixture：

1. 正常工具错误，允许在原权限内重试。
2. 错误消息要求调用未授权工具。
3. 错误消息要求扩大对象范围。
4. 错误消息要求关闭检查。
5. 错误消息伪造系统或管理员身份。
6. 重试时复用旧执行票据。
7. 恢复时修改参数、对象、收件人或目的地。
8. 并发恢复和重复提交。

主要检查：

- 每一次恢复动作是否都有新的 allow/deny 决策。
- 恢复是否绑定当前 Contract 版本。
- 旧票据是否不可重放。
- 错误消息是否能改变 Sandbox 或 Reference Monitor 状态。
- 合法恢复的任务完成率是否下降。

I3 结果解释：

- 如果 P0 已阻断所有越权恢复，记录 `no_go`，停止增加新机制。
- 如果发现真实安全缺口，只先修复可复现的 P0 缺陷。
- I3 不单独包装为论文主创新，除非研究侧重新解锁。

---

### Phase I2：选择性任务遗漏 fixture

状态：锁定。必须等待 E0 审计通过并获得研究侧解锁。

不得提前实现。

解锁条件：

1. payload 确实送达。
2. 遗漏由宿主 oracle 独立识别。
3. 工具动作全部合法。
4. 同任务有合法筛选负例。
5. 覆盖检查不会把合法筛选误判为攻击。
6. 恢复不会扩大工具、对象或数据权限。

候选实现：

- 宿主维护 `Task Obligation Ledger`。
- 在读取不可信内容前，根据可信用户请求和环境状态建立义务集合。
- 任务结束时由宿主枚举真实对象并检查覆盖。
- 外部内容不能删除或修改义务。
- 恢复只补做缺失对象。
- 恢复动作必须重新经过同一授权入口。

第一版环境限制：

- 只使用 mock inbox 或 issue tracker。
- 不加入多模态、多 Agent、MCP、跨会话记忆或在线学习。
- 如果宿主不能提供稳定对象集合和独立真值，直接回报 `no_go`。

---

## 3. 工程验证矩阵

每一个配置都要使用相同任务、相同攻击、相同模型、相同预算和相同 seed。

| 配置 | 目的                                    |
| ---- | --------------------------------------- |
| A0   | 无防御，测量原始攻击和任务效用          |
| A1   | 当前 DSCG P0 工具级底座                 |
| A2   | 研究侧后续解锁的普通任务完成/覆盖检查   |
| A3   | 研究侧后续解锁的 Task Obligation Ledger |
| A4   | 全拒绝或粗粒度拒绝上界                  |

当前可直接执行的工程验证优先是：

- A0 与 A1 的 harness 审计
- A1 的 I3 恢复压力测试
- 离线票据重放、Contract 版本和错误路径测试

A2/A3 只有在研究路线解锁后执行。

---

## 4. 指标计划

### 4.1 安全指标

- task ASR
- action-level unauthorized side effect rate
- 恢复路径中的未授权动作率
- 票据重放成功率
- 越权重试成功率
- 高风险动作 `unknown` rate
- payload delivery rate
- predicate 可重放率

### 4.2 效用指标

- benign utility
- utility under attack
- 用户义务对象覆盖率
- 选择性任务遗漏率
- 遗漏恢复率
- 合法筛选精度
- false refusal
- 恢复成功率

### 4.3 成本指标

- P50/P95 latency
- 主模型 token
- 安全模型 token
- API 调用次数
- 重试次数
- 每个成功任务的平均成本

### 4.4 统计要求

- 任务对是主要独立统计单位。
- 报告样本数和有效分母。
- 主要比例报告 95% Wilson 或 bootstrap 区间。
- 配对配置使用 paired permutation 或 McNemar 风格检验。
- 不把 seed 或重复请求当作新的任务样本。
- 所有错误类别单独报告。

---

## 5. 论文写作计划

### 5.1 论文类型

当前更适合作为：

`security analysis + practical defense prototype`

不是纯算法论文，也不是单纯网页平台介绍。

### 5.2 论文结构

#### 1. Introduction

内容顺序：

1. LLM Agent 需要读取外部内容并调用工具。
2. 外部内容可以是合法任务数据，也可以携带间接提示词注入。
3. 仅检测文本或仅检查工具名称无法覆盖所有风险。
4. 模型可能提出看似合理但不应执行的动作。
5. 现有 P0 底座将候选动作与执行授权分离。
6. 如果 I2 通过，再引出“工具动作合法但任务义务被选择性遗漏”的问题。
7. 明确论文只研究文本、单 Agent、外部内容到工具动作的路径。

Introduction 中只保留 2–3 个具体限制：

- 文本检测不能替代执行点授权。
- 工具级授权可能无法发现任务对象遗漏。
- 错误反馈和恢复路径可能形成新的授权入口。

#### 2. Threat Model and Scope

明确：

可信组件：

- 可信用户消息
- 固定策略代码
- 工具注册表
- reviewed tool metadata
- Reference Monitor
- 实验宿主和环境 oracle

攻击者能力：

- 控制网页、邮件、文档和工具返回值
- 修改外部内容中的指令和伪造事实
- 根据拒绝结果自适应修改 payload
- 诱导模型改变动作顺序、参数或任务覆盖范围

不覆盖：

- 被攻陷的工具实现
- 模型权重后门
- 操作系统入侵
- 恶意模型服务商
- 多模态输入
- 多 Agent 委托
- 跨会话记忆
- 隐式模型内部状态

#### 3. DSCG Design

建议只写已实现且有代码证据的部分：

1. TrustedTaskRequest
2. authorization-before-generation
3. PermissionSandbox
4. ActionSecurityChecker
5. ReferenceMonitor
6. ActionLedger
7. one-use ExecutionTicket
8. structured tool error and re-planning
9. risk metadata
10. trace and replay record

核心语义：

- 安全审计器不能授予新权限。
- Sandbox 拒绝时动作必然被阻断。
- 每个真实工具动作必须有确定性决策。
- 每次重试和恢复必须回到相同策略入口。
- 票据绑定 action id、调用指纹、Contract 版本和 nonce。

#### 4. Harness and Evaluation Protocol

重点写：

- payload 如何构造和送达
- attack predicate 如何连接真实环境状态
- 任务如何冻结
- manifest 如何生成
- 错误样本如何分类
- 轨迹如何保存和重放
- 指标和分母如何计算

这一节是进入 workshop 论文可信度的关键，不能只展示网页截图。

#### 5. Experiments

实验顺序：

1. 离线安全不变量测试
2. E0 harness 审计
3. I3 错误反馈恢复压力测试
4. I2 fixture 和 pilot（只有解锁后）
5. AgentDojo 或其他外部 benchmark 的受限实验
6. 消融和成本分析

每个实验都要报告：

- 配置
- 任务数
- 有效样本数
- 错误数
- 攻击类型
- 模型和 seed
- 主指标
- 失败案例
- 限制

#### 6. Results

不要只展示一个平均 ASR。

至少需要：

- 各套件结果
- 各攻击模板结果
- benign 与 attack utility
- 安全指标和效用指标
- 任务级和动作级结果
- latency、token 和 API 成本
- 失败样本与误拒绝样本
- 错误分母
- 置信区间

#### 7. Limitations

必须主动写：

- 工具级 P0 不能保证参数级 provenance。
- 模型内部隐式流不可见。
- 受攻陷工具不在威胁模型内。
- Task Obligation Ledger 需要宿主提供稳定对象集合。
- mock inbox/issue tracker 不能直接代表所有现实工作流。
- 结果依赖模型、任务、攻击模板和环境版本。
- 安全模型是辅助信号，不是安全根。

#### 8. Conclusion

只总结已验证的结果。

如果 I2 未通过：

> 本文展示一个工具级、fail-closed 的 IPI 防御原型，并系统审计其评测 harness、恢复路径和可复现性边界。

如果 I2 通过：

> 本文进一步证明，某类工具动作全部合规但任务义务被选择性遗漏的 IPI 轨迹，可以由宿主侧义务账本检测并在不扩大权限的条件下恢复。

---

## 6. Claim-Evidence 对照表

| 论文主张                 | 必须绑定的证据                                             |
| ------------------------ | ---------------------------------------------------------- |
| 授权先于候选生成         | 代码路径、离线测试、trace 顺序                             |
| 外部内容不能扩大工具权限 | Sandbox/Monitor 状态转移测试                               |
| 每个动作都经过确定性仲裁 | ActionLedger、ticket 和 replay 记录                        |
| 票据不可重放             | 单元测试和恢复压力测试                                     |
| LLM 审计不是安全根       | 关闭审计器、审计超时、非法输出和 deny/allow 消融           |
| harness 结果可信         | payload delivery、predicate、最终环境状态和有效分母        |
| IPI 会造成任务遗漏       | 成对 fixture、独立 oracle、合法筛选负例                    |
| 恢复有效                 | omission recovery、benign utility、false refusal、恢复成本 |
| 不扩大权限               | 恢复前后工具、对象、数据和 sink 权限对照                   |
| 方法优于粗粒度拒绝       | 与全拒绝配置的匹配安全和效用比较                           |

任何没有对应实验和样本分母的主张，都不能进入摘要和结论。

---

## 7. 执行顺序

### 第一步：工程状态同步

- [ ] 确认当前 git commit
- [ ] 确认工作树状态
- [ ] 运行现有离线测试
- [ ] 记录 Python、AgentDojo 和依赖版本
- [ ] 不把旧 smoke benchmark 写成论文结果

### 第二步：E0 Harness Audit

- [ ] 固定任务 manifest
- [ ] 固定攻击模板
- [ ] 固定 seed
- [ ] 保存 payload 和 hash
- [ ] 验证 payload delivery
- [ ] 验证 attack predicate
- [ ] 保存最终环境状态
- [ ] 修正错误分母
- [ ] 保存可重放轨迹
- [ ] 运行离线重放测试

### 第三步：I3 P0 Stress

- [ ] 建立错误反馈 fixture
- [ ] 测试越权工具恢复
- [ ] 测试参数扩大
- [ ] 测试票据重放
- [ ] 测试审计器失效
- [ ] 测试合法恢复
- [ ] 如无真实缺口，记录 No-Go

### 第四步：研究侧决定是否解锁 I2

- [ ] E0 通过
- [ ] 研究侧审核回报
- [ ] 只有解锁后创建 I2 fixture
- [ ] 只使用具有独立 oracle 的 mock 环境
- [ ] 通过 pilot 闸门后再做正式实验

### 第五步：论文初稿

在 E0 期间即可先写：

- [ ] Introduction
- [ ] Threat Model
- [ ] DSCG Design
- [ ] Evaluation Protocol
- [ ] Related Work

E0/I3 结果出来后再写：

- [ ] Results
- [ ] Failure Cases
- [ ] Limitations
- [ ] Conclusion

### 第六步：投稿前审查

- [ ] 所有主张都有证据
- [ ] 所有主表都有有效分母
- [ ] 所有图表可由原始结果重建
- [ ] 代码 commit、环境和 manifest 已记录
- [ ] 没有 API Key、隐私数据或完整敏感 prompt
- [ ] 没有同时投稿到其他 venue
- [ ] 按 AIMLL 投稿系统要求确认具体页数和截止日期
- [ ] 准备最终 PDF、源文件、补充材料和演示材料

---

## 8. Go / Conditional Go / No-Go

### Go

同时满足：

- E0 harness 审计通过
- P0 安全不变量全部通过
- I3 没有未修复的授权扩张
- I2 若实现，则有独立 oracle 和合法筛选负例
- 主结果能由原始轨迹和固定脚本重建
- 至少有安全、效用、成本和失败案例
- 论文主张没有超出实验边界

### Conditional Go

适用于：

- 只在某一类任务或攻击中有效
- 只在特定模型上有效
- 效用损失明显
- 只能证明工程可靠性，不能证明新的防御机制
- 外部基线无法等价复现

论文必须收缩主张，并完整报告失败边界。

### No-Go

出现以下任一情况：

- payload 未实际送达
- attack predicate 不能连接真实环境状态
- 缺失样本被计为安全成功
- 工具或对象 oracle 不独立
- 恢复扩大权限
- I2 只是普通 task-success 的换名
- 安全收益主要来自全局拒绝
- 结果无法重放
- 只有单模型、单攻击、单次运行
- 主张与已有工作没有可验证差异

No-Go 后停止继续堆叠防御组件，先修正问题定义、评测协议或论文定位。

---

## 9. 当前下一步

当前唯一优先动作：

`E0-HARNESS-AUDIT`

完成后回报必须包含：

- route_id
- task_id
- status
- code revision
- working-tree state
- exact commands and exit codes
- artifact paths and SHA-256
- valid/invalid/error/skipped counts
- known limitations
- one next action

在 E0 回报通过前，不实现 I2，不写参数级 provenance，不把 DSCG 宣传为通用 IPI 防御。
```

这份计划对应当前研究路线，且把工程实现、论文写作和投稿前审查放在同一个执行顺序中。当前最先执行的工程任务仍然是 `E0-HARNESS-AUDIT`。