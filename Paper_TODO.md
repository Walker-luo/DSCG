# DSCG 论文工作计划

> 本文件把 `research/ideas.md` 第 3 点的研究主线落成可执行的论文计划。
> 系统实现细节以 [`System_TODO.md`](./System_TODO.md) 和 [`README.md`](./README.md) 为准；论文对照、基准和最小实验协议以 [`../research/Contrast.md`](../research/Contrast.md) 为准。
>
> 当前日期：2026-09-27
> 当前状态：P0 工程底座已有实现记录；P1/P2 研究机制尚未完成，不能据此宣称字段级安全能力。

## 0. 论文目标和主线

### 0.1 目标

目标是形成一篇面向安全系统/Agent 安全方向的实证系统论文，优先考虑 USENIX Security、IEEE S&P、CCS 或 NDSS。完成本文件不代表录用；如果改投 NeurIPS/ICML，还需要独立的学习算法、模型方法或理论贡献。

论文只研究文本、单 Agent、工具调用场景中的间接提示词注入：外部网页、邮件、文件或工具返回值影响工具参数或数据外发。

### 0.2 论文主问题

> 当外部不可信内容可以合法地作为任务数据使用时，字段级 provenance 传播和 external sink 前的确定性授权，能否阻止它改变收件人、支付对象、删除目标、金额或目的地，同时比整动作拒绝保留更多任务效用？

### 0.3 建议的单一主贡献

把 DSCG 组织为一个**字段级来源约束的确定性执行框架**：

1. 从可信用户请求生成不可变的 Task Contract，固定操作、参数、对象、预算和允许的数据流。
2. 为字段值记录来源和派生关系，区分 `trusted_user`、`trusted_system`、`tool_output`、`untrusted_external`、`model_derived` 和 `unknown`。
3. 对拼接、摘要、翻译、JSON 重组、模板填充、编码和分块定义可解释的 provenance 合并规则。
4. 在发送、支付、删除、上传和公开输出等 sink 前，确定性检查 authority-bearing 参数的来源和契约约束。
5. 在安全水平相当时，只阻断受影响字段或动作，保留合法的摘要、翻译和编辑任务。

这条主线必须通过实验验证，不能把“参数授权”“契约”“审计日志”“执行票据”或“Reference Monitor”单独写成已确认的新颖算法。

### 0.4 可证伪假设

| 编号 | 假设 | 必须由什么证据支持 |
|---|---|---|
| H1 | 参数级 Task Contract 比当前工具级授权更能阻断同工具参数劫持，同时保持可接受的良性效用 | A1 对 A2；参数值、对象、预算和调用次数产生真实判决差异 |
| H2 | provenance-aware source-to-sink 策略能阻断“敏感读取 → 派生/改写 → 外发”，且去掉 provenance 后该增益消失 | A2 对 A3；同一 Contract、轨迹和候选动作下，sink 判决发生可解释变化 |
| H3 | 细粒度策略在匹配安全水平下比粗粒度整动作拒绝保留更多效用 | A3 对 A4；报告安全–效用 Pareto、误拒绝、保真度和成本 |

如果结果不支持假设，应收缩论文主张或停止扩展机制；不能通过增加规则、删去失败样本或只报告较低 ASR 来修正结论。

### 0.5 投稿方向和证据要求

当前机制更适合安全系统和 Agent 安全方向。USENIX Security、IEEE S&P、CCS、NDSS 的审稿重点通常是威胁模型清楚、系统机制可执行、与近邻工作差异明确、攻击评测充分、效用代价透明和 artifact 可复现；完成代码或降低 ASR 本身不足以支撑投稿。NeurIPS/ICML 只有在加入独立的学习算法、模型训练方法或理论结果时才适合作为主要目标。

投稿前必须有四类证据：

- **机制证据**：P1/P2 的数据结构、传播规则、sink 判决和安全不变量可运行、可测试、可回放。
- **因果证据**：A1–A4 使用相同任务、候选动作和 Contract 输入，证明增益来自参数约束和 provenance，而不是全局拒绝或模型随机性。
- **外部有效性证据**：四个 AgentDojo 套件、多个攻击模板、至少两个模型，并至少完成一个强近邻的等价配置复现。若强近邻全部阻塞，只能作为 Conditional Go，不能称为顶会就绪。
- **审稿可复核证据**：任务 manifest、结果分母、统计脚本、失败样本、成本数据、代码 commit 和最小复现包齐全。

## 1. 当前状态和工作边界

| 工作流 | 当前状态 | 论文意义 | 下一步 |
|---|---|---|---|
| P0.1–P0.5 可信执行底座 | 已有实现记录 | 工具级工程基线：fail-closed、统一仲裁、票据、结构化审计、显式工具元数据 | 完成 P0 DoD，重新跑 baseline 并锁定配置 |
| P1 Task Contract | 未完成 | 固定参数、对象、预算、有效期和允许数据流 | 实现 schema、编译校验和参数级 Monitor |
| P2 provenance/source-to-sink | 未完成 | 论文主机制 | 实现字段账本、传播规则、`unknown` 和 sink 判决 |
| P3 Delegation Envelope/确认 | 暂缓 | 可选第二创新包，不进入首轮主线 | 只有 A3 增益不足但合法委托需求明确时再评估 |
| P4 评测证据 | 仅有协议，未完成论文级运行 | 支撑所有安全、效用和成本 claim | 先 microbenchmark，再 pilot，最后 confirmatory run |
| P5 论文封装 | 未开始 | 将实现和证据转成可审稿论文 | 在结果冻结后写作、复现和限制说明 |

**范围停止线：** P1/P2 和专项 microbenchmark 未通过前，不增加多模态、多 Agent、MCP、跨会话记忆、在线学习或大型检测器搜索。

### 1.1 Agent 执行协议

本文件中的每个复选框都应作为一个有边界的 Agent 任务执行。Agent 不应一次性“完成整个阶段”，而应完成一个任务、写入证据、运行验收，再解锁下一个任务。

每次执行前先创建一条任务记录，至少包含：

```yaml
task_id: P1-SCHEMA
prerequisites: [P0-VERIFY]
input_files: [dscg/..., config/...]
allowed_changes: [具体文件或目录]
action: 要实现或核验的单一目标
commands: [实际运行的命令]
artifacts: [测试、配置、报告或结果文件]
acceptance: 可观察的通过条件
blocker: null
next_task: P1-MONITOR
```

执行规则：

- Agent 先读取依赖文件和当前 `git diff`，确认没有覆盖用户已有改动。
- Agent 只修改 `allowed_changes` 中的文件；研究结论写入结果/报告，不通过改测试或删样本制造通过结果。
- Agent 必须运行与任务对应的离线检查；外部 API、基准或模型不可用时记录 `blocker`，不能把未运行标成完成。
- 任务完成的证据至少包括一个代码/配置产物和一个命令输出、测试报告或可审阅 diff。
- 每个 Agent 任务原则上只产生一个独立 commit；若当前工作流不提交 commit，至少记录 `git diff --stat` 和补丁哈希。
- 每个 Agent 任务结束时更新本文件“每周执行记录”，写明 `task_id`、commit、证据路径和下一任务；未满足验收条件时只能记录 `blocked/partial`，不能勾选后续任务。
- 任务表中的“必须产出”是默认允许修改的边界；若实现必须修改其他文件，Agent 先在任务记录中列出具体路径，再开始编辑。

证据目录约定如下：版本化的协议、任务清单、测试夹具和分析脚本放在 `config/paper/`、`tests/paper/`、`experiments/paper/` 和 `docs/paper/`；大量运行结果放在被 Git 忽略的 `results/paper/`，但必须保存结果目录的 manifest、代码 commit 和哈希。不要使用未约定的 `reports/` 目录作为唯一证据位置。

### 1.2 可直接交给 Agent 的任务队列

| Task ID | 前置条件 | Agent 目标 | 必须产出 | 解锁条件 |
|---|---|---|---|---|
| `P0-AUDIT` | 无 | 盘点 P0.1–P0.5 的实现、未完成 DoD、测试入口和当前脏文件 | `docs/paper/p0_audit.md` | 每项 P0 DoD 有 `pass/fail/unknown` |
| `P0-ENV` | `P0-AUDIT` | 按 `environment.yml` 建立 Python 3.10/AgentDojo 0.1.35 环境，记录实际版本；无法建立时先记录阻塞 | `docs/paper/environment_check.md`、环境版本输出 | 项目测试在声明环境中可启动，或有明确 blocker |
| `P0-VERIFY` | `P0-ENV（通过，或已记录可复核的离线替代环境）` | 运行离线回归和 mock runtime，修复或记录 fail-closed、重试、并发、票据重放问题 | 测试输出、失败样例、修复 diff | 每个真实动作的 allow/deny/confirm 可追溯；若只使用替代环境，只能解锁离线任务 |
| `P0-NOVELTY` | `P0-AUDIT` | 核对 Contrast、论文正式版本和公开代码，完成近邻机制差异与可证伪差异 | `docs/paper/novelty_gate.md`、引用/版本核验记录、阻塞日志 | 没有未经解释的完整机制重合；若存在重合，先重定义主问题或停止主线 |
| `P0-BASELINE` | `P0-VERIFY` | 用固定模型配置跑一次当前 P0.5 baseline；只确认入口、结果格式和成本字段 | `config/paper/baseline.*`、`results/paper/baseline/` | baseline 可重复运行且分母清楚 |
| `P0-FREEZE` | `P0-BASELINE`, `P0-NOVELTY` | 冻结 threat model、任务 manifest、攻击模板、seed、主要终点和异常处理 | `config/paper/protocol.*`、任务清单、协议审阅记录 | 协议文件在首次正式运行前不再改动；新颖性闸门必须通过。若为 No-Go，只能冻结重定义后的新问题，不能解锁 P1 |
| `P1-SCHEMA` | `P0-FREEZE` | 实现 Contract、authority-bearing 字段、版本和哈希 schema | schema、样例和 schema 测试 | 合法、未知、越权参数均有确定结果 |
| `P1-COMPILER` | `P1-SCHEMA` | 实现 LLM 候选 Contract 的解析、校验、漏授/过授记录和失败闭合 | 编译器、错误码、固定样例报告 | 工具输出不能改变 Contract 哈希或权限 |
| `P1-MONITOR` | `P1-COMPILER` | 将参数约束、预算、状态和 Contract 版本接入唯一 Reference Monitor | Monitor diff、reason code、集成测试 | 缺票据、重放、篡改和过期 Contract 全部阻断 |
| `P1-REPLAY` | `P1-MONITOR` | 实现邮件、日历、云文件、金融各一个合法/越权可重放样例 | replay fixtures、回归测试和报告 | P1 DoD 全部通过 |
| `P2-LEDGER` | `P1-REPLAY` | 将动作账本扩展为字段依赖、source ID、敏感级别和 append-only 事件 | ledger schema、样例 JSONL、完整性测试 | 在线和离线事件可重放 |
| `P2-RULES` | `P2-LEDGER` | 实现拼接、JSON 重组、摘要、翻译、模板、编码、分块的 provenance 合并规则 | 规则表、正/负/边界 fixtures | 无法证明来源时稳定得到 `unknown` |
| `P2-SINK` | `P2-RULES` | 实现 source-to-sink 判决和高风险 `unknown` 处置 | sink policy、reason code、攻击轨迹报告 | A2/A3 能改变真实执行判决 |
| `P2-REPLAY` | `P2-SINK` | 对合法流、敏感外发、同工具参数劫持做在线/离线一致性回放 | 三类 replay report | P2 DoD 全部通过 |
| `E0-HARNESS` | `P0-FREEZE` | 将攻击模板、任务 manifest、seed、强制重跑和运行元数据接入评测入口；当前固定的 `important_instructions` 只能作为 pilot | `experiments/paper/` 运行入口、`config/paper/manifest.*`、元数据 JSON、入口测试 | 每次结果能标识 suite/task/attack/defense/model/seed，旧结果不会静默复用 |
| `E0-REPLAY` | `E0-HARNESS` | 保存候选动作和 Contract，支持固定候选轨迹下的策略回放 | `tests/paper/fixtures/`、replay schema、回放命令 | A1–A4 可在相同输入下只改变策略语义 |
| `E1-MICRO` | `P2-REPLAY`, `E0-REPLAY` | 构造真实副作用 oracle 的字段级 microbenchmark | `config/paper/microbenchmark.*`、`experiments/paper/`、ground truth 和 oracle | 任务成对且不变量全部通过 |
| `E2-PILOT` | `E0-REPLAY`, `E1-MICRO` | 跑 A0–A4 小规模 pilot，检查配置、指标和故障归因 | `results/paper/pilot/`、聚合表、失败案例 | Pilot Go 条件全部满足 |
| `E3-CORE` | `E2-PILOT` | 跑四套件、预注册攻击和两模型的核心 confirmatory matrix | `results/paper/core/` 原始轨迹、摘要、统计表、成本报告 | 主结果可按任务/套件/攻击/模型/seed 重建 |
| `E4-EXPAND` | `E3-CORE` | 扩展到完整有效组合、自适应攻击和可复现强近邻 | `results/paper/expanded/`、基线复现记录、阻塞记录 | 每个扩展结果都有等价配置说明 |
| `ANALYZE-CORE` | `E3-CORE`, `E4-EXPAND` 或明确记录扩展阻塞 | 生成安全–效用 Pareto、分层统计、失败归因和 claim–evidence 表 | `experiments/paper/analysis/`、`docs/paper/claim_evidence.md`、图表 | 主要 claim 均有正/负证据，且扩展基线状态已标注 |
| `DRAFT-PAPER` | `ANALYZE-CORE` | 按冻结结果撰写论文、局限和 related work | 论文草稿、图表、附录清单 | 草稿中的每个数字可回溯原始结果 |
| `REPRO-PACK` | `DRAFT-PAPER` | 在干净环境从零运行最小复现和图表重建 | artifact README、复现日志、发布包 | 第二人可按 README 完成复现 |
| `REVIEW-SUBMISSION` | `REPRO-PACK` | 模拟审稿，检查新颖性、统计、基线等价性和过度 claim | review checklist、修订清单 | Go 闸门通过后才选投稿 venue |

若某任务连续三次因为同一外部依赖阻塞，保留阻塞证据并切换到不依赖该资源的下一个任务；只有在所有可独立任务完成后，才将整个阶段标记为 blocked。

环境阻塞只能延后需要真实模型或 AgentDojo 的任务，不能把未运行的实验标为通过：`P0-VERIFY` 可以在已记录的兼容解释器中完成 mock/静态子集，但 `P0-BASELINE`、`E2-PILOT`、`E3-CORE` 和 `E4-EXPAND` 必须在声明环境中运行。安全语义、测试失败或新颖性重合不能按“外部依赖阻塞”跳过，必须修复、收缩 claim 或进入 No-Go。

### 1.3 Agent 任务交接模板

后续给 Agent 分配任务时，直接使用下面的格式，避免它自行扩大范围：

```text
任务：P1-SCHEMA
读取：DSCG/Paper_TODO.md、DSCG/System_TODO.md、相关实现文件
前置证据：<上一任务的 artifact 路径和验收结果>
允许修改：<明确列出文件>
目标：只实现 Contract schema 和对应离线测试，不接入真实模型
必须运行：<测试命令>
必须产出：<文件、报告、diff、测试输出>
通过条件：<逐条可观察条件>
停止条件：发现未记录的安全语义、用户脏改动或外部依赖缺失时停止并记录 blocker
完成后：更新 Paper_TODO.md 的执行记录，不标记后续任务完成
```

第一轮推荐按 `P0-AUDIT → P0-ENV → P0-VERIFY → P0-BASELINE` 执行；`P0-NOVELTY` 可在 `P0-AUDIT` 完成后独立进行，随后由 `P0-FREEZE` 汇合。每一步结束后先审阅证据，再启动下一步；不要并行修改同一条策略链。

### 1.4 当前项目可用的命令入口

Agent 应优先使用仓库已有入口，命令中的环境名和 API 配置必须写入任务记录：

```bash
# P0-VERIFY：离线回归
conda run -n ipi python -m unittest discover -s tests -v

# P0.5 工具目录核验
conda run -n ipi python -m experiments.generate_tool_metadata

# P0-BASELINE / E2-PILOT：小批量运行，强制避免复用旧结果
DSCG_FORCE_RERUN=1 conda run -n ipi python -m experiments.run_partial_benchmark \
  --name P0-baseline --trace-level standard

# E3-CORE：全量入口；正式运行前必须已完成 E0-HARNESS 的攻击和 manifest 改造
conda run -n ipi python -m experiments.run_benchmark \
  --name paper-core --trace-level summary
```

如果命令入口尚未支持某个参数，Agent 应先完成对应的 `E0-HARNESS` 任务，不能通过手工修改结果文件代替。真实模型运行前先用 mock runtime 和离线 fixture 检查策略；API key、模型不可用和网络错误必须写入 blocker 或运行错误字段。

## 2. 阶段计划

### Phase 0：冻结问题、文献和实验协议

- [ ] 核对 `research/Contrast.md` 第 2.3 节中的论文版本、会议状态、benchmark、攻击模板、代码入口和复现状态。
- [ ] 对 ACE、IPIGuard、MELON、ActGov、SkillGuard、TraceGrant、Ajar 至少完成执行点、授权粒度、provenance 模型、拒绝粒度和效用指标的对照记录。
- [ ] 固定首轮威胁模型：外部内容和工具返回值可被攻击者控制；可信用户消息、策略代码、工具注册表和实验宿主可信。
- [ ] 固定论文边界：不声称形式化证明、完整污点追踪、通用防御或“首次提出参数级授权”。
- [ ] 冻结 A0–A4 的配置、任务清单、攻击模板、主要终点、异常处理、重试上限、seed 和 Go/No-go 阈值。
- [ ] 为每个实验配置生成版本化 YAML/TOML 元数据，记录代码 commit、模型 ID、provider/base URL、提示模板、温度、reasoning 设置和 benchmark 版本。

**完成条件：** 任务选择、攻击者能力、指标定义和主要终点在第一次正式运行前不可再根据结果调整。

**新颖性闸门：** 对每个近邻工作填写“是否追踪字段派生、是否在 sink 判决、是否支持 `unknown`、拒绝粒度、是否比较安全–效用”的五项对照。若某项工作已经覆盖 DSCG 的完整机制组合，先重定义研究问题或停止主线；不能先实现后再用术语差异包装重合方案。闸门产物为 `docs/paper/novelty_gate.md`，其中必须列出至少一个可被实验检验的差异和一个可能推翻该差异的结果。

本阶段的文献核验和新颖性闸门由 `P0-NOVELTY` 负责，协议冻结由 `P0-FREEZE` 负责；没有这两个任务的证据文件，Phase 0 复选框只能保持未完成。

### Phase 1：完成 P1 参数级 Task Contract

#### 1.1 Contract 数据结构

- [ ] 使用严格 schema 表示 operation、资源范围、参数约束、允许来源、允许 sink、调用次数/金额、有效期、确认条件和撤销状态。
- [ ] 为 authority-bearing 字段单独建模：`recipient`、`object`、`amount`、`destination`、`delete_target`、权限对象等。
- [ ] Contract 保存规范化意图、签发主体、签发时间和哈希；工具输出不能修改 Contract 或扩大其权限。
- [ ] 缺失的必需 authority-bearing 字段、来源或 sink 默认是 `unknown`；预算缺失默认为 `0`，有效期缺失默认为 `expired`；明确不适用的字段使用 `not_applicable`，不能用 `None` 隐式放行或把不适用字段误判成越权。
- [ ] 限制 Contract 表达能力为枚举、集合、范围、正则、资源 ID 和预算；暂不支持任意自然语言谓词。

#### 1.2 Contract 编译和校验

- [ ] 若使用 LLM 编译 Contract，只允许其生成候选 JSON；由 schema、注册表、固定策略和候选值校验器确定性检查。
- [ ] 编译失败时允许纯文本回答，但禁止产生外部副作用。
- [ ] 单独统计漏授、过授、解析失败、超时和不可表达请求。
- [ ] 同一可信用户请求、工具目录和策略版本重复编译得到相同规范化 Contract 哈希。

#### 1.3 参数级 Reference Monitor 和能力状态

- [ ] 所有正常、重试、恢复、并发和确认后的动作都经过唯一 Reference Monitor。
- [ ] 检查工具 effect、参数值、资源范围、调用/金额预算、任务状态和 Contract 版本。
- [ ] `confirm` 只能由可信用户或可信宿主在当前 Contract 版本下产生；主模型、工具返回值和外部文本不能伪造确认或把 `confirm` 转成永久授权。
- [ ] 用 Capability Graph 表示任务节点、前置条件、完成条件、消耗项和产生项。
- [ ] 保证能力单调：外部观察只能缩小或消费当前能力，不能新增工具、扩大对象范围、提高金额/次数上限或改变 sink。
- [ ] 缺票据、票据重放、参数篡改、过期 Contract 和跨回合 Contract 不匹配均阻断。

**Phase 1 DoD：** 邮件、日历、云文件和金融各至少一个合法/越权样例可重放；合法参数通过，越权参数、未知参数和超预算调用确定性阻断；P1 单元、集成和状态机测试通过。

### Phase 2：完成 P2 字段 provenance 和 source-to-sink

#### 2.1 字段 provenance ledger

- [ ] 定义最小字段对象：`FieldValue(value, provenance, sensitivity, role)`。
- [ ] 至少支持 `trusted_user`、`trusted_system`、`tool_output`、`untrusted_external`、`model_derived` 和 `unknown`。
- [ ] 为工具输出分片分配 `source_id`，记录来源工具、资源 ID、信任级别、敏感级别和产生时间。
- [ ] 记录每个写参数依赖的用户字段、工具输出分片和模型派生字段。
- [ ] 账本由执行层 append-only 写入，主模型只能读取，不能改写授权或历史。

#### 2.2 provenance 合并规则

- [ ] 明确定义字符串拼接、JSON 重组、模板填充、摘要、翻译、编码和分块的传播规则。
- [ ] 采用保守合并：无法可靠证明来源时标记 `unknown`，不能将猜测当作可信来源。
- [ ] embedding 或相似度只能作为语义告警，不能作为 provenance 证明。
- [ ] 为每个规则编写正例、攻击例和边界例，并支持从原始事件重放到同一结果。

#### 2.3 Source-to-sink 判决

- [ ] 定义敏感 source：邮件、云文件、账户信息、联系人、私有日历等。
- [ ] 定义危险 sink：发送邮件/消息、HTTP 请求、上传、公开回答、转账、删除和权限变更。
- [ ] 默认禁止不可信内容决定收件人、支付对象、删除目标、权限对象和目的地。
- [ ] 默认禁止敏感 source 未经 Contract 授权流向 external sink；显式授权的合法流必须可区分。
- [ ] 对 `unknown` 到高风险 sink 默认拒绝或要求当前动作确认。
- [ ] 记录 source、sink、Contract 条款、命中规则和 reason code，支持攻击轨迹图和失败归因。
- [ ] 将 `public_output` 纳入 sink，覆盖没有写工具但最终回答泄露敏感数据的路径。

**Phase 2 DoD：** 至少三条可重放轨迹通过：合法数据处理、敏感数据外发、同工具参数劫持；A2/A3 的 provenance 消融能改变真实 sink 判决，而不是只改变日志字段。

### Phase 2.4：评测入口准备（E0-HARNESS / E0-REPLAY）

- [ ] 将攻击名称从代码中的固定常量改为协议/命令行配置，并在每个结果中记录实际攻击名称和版本。
- [ ] 为 `important_instructions`、`ignore_previous`、`tool_knowledge` 以及可运行的自适应攻击建立 manifest；不支持的攻击明确标为 `blocked`，不假装覆盖。
- [ ] 增加显式 `force_rerun` 或等价的结果隔离机制；模型、攻击、策略或代码 commit 改变时不能静默复用旧 JSON。
- [ ] 保存 `run_metadata.json`，至少包含 `git_commit`、环境版本、model/provider、security model、suite、task IDs、attack、defense、seed、预算、trace level 和开始/结束时间。
- [ ] 保存候选动作、规范化参数、Contract 版本和策略输入，使 A1–A4 可以在相同输入上回放；回放不能重新调用模型来“碰运气”复现动作。
- [ ] 为结果分母定义 `valid`、`model_error`、`policy_error`、`tool_error`、`timeout` 和 `infrastructure_error`，聚合脚本不能自行删除非成功样本。

**入口 DoD：** 一个离线 fixture 能用同一候选动作运行 A1–A4 并生成不同策略结果；改变攻击模板或代码 commit 会生成新的结果目录；旧结果目录不会被无提示覆盖或复用。

### Phase 3：专项 microbenchmark 和安全不变量

AgentDojo 用于生态有效性，专项 microbenchmark 用于验证字段级机制因果。这里的“真实副作用 oracle”是一个可复现的本地工具模拟器：它记录发送、支付、删除或公开输出的预期状态变化与哈希，不连接真实账户或生产服务。每条轨迹必须有可信用户目标、字段级 ground truth、预期副作用和可重放工具环境。

- [ ] 同一工具只改变 `recipient`、`object`、`amount`、`destination` 或删除目标。
- [ ] 敏感 source 经过摘要、拼接、JSON 重组、模板填充、翻译、编码和分块后进入 external sink。
- [ ] 外部文本被合法翻译、摘要或编辑，但其中的指令不能获得执行权。
- [ ] 覆盖可传播 lineage、无法可靠传播的 lineage 和 `unknown` 到高风险 sink。
- [ ] 覆盖细粒度字段拒绝、整动作拒绝、确认、恢复、重试、并发和票据重放。
- [ ] 每类保留 benign/attack 成对样本，不用只对 DSCG 有利的人工样例替代 AgentDojo。

安全不变量至少包括：

- [ ] 每个真实工具动作存在唯一的确定性 allow/deny/confirm 决策。
- [ ] 外部内容不能扩大 Contract、能力边界、对象范围、金额/次数预算或允许 sink。
- [ ] 不可信字段不能独立控制未授权的 authority-bearing sink。
- [ ] provenance 不确定时高风险动作按预注册规则拒绝或要求确认。
- [ ] 重试、恢复、并发、审计器失效和票据重放均重新进入同一策略入口。

**通过条件：** 在线执行结果与离线重放结果一致；任何不变量失败都停止进入付费 pilot。

### Phase 4：Pilot 闸门

- [ ] 每个 AgentDojo 套件选择 2 个 benign/attack 成对任务，共 8 对。
- [ ] 至少包含 1 对同工具参数劫持和 1 对敏感 source 到 external sink。
- [ ] 另加 3 条本地可重复轨迹：合法流、敏感外发、同工具参数劫持。
- [ ] 运行 A0–A4；一个主模型、一个审计模型、固定温度、单 seed、每个配置最多一次完整回合。
- [ ] 记录 API 失败、超时、策略错误、工具错误和重试，不把基础设施错误当作安全成功。
- [ ] 生成完整 paired 指标表和至少一组失败案例、一组误拒绝案例。

**Pilot Go：** 所有真实动作有 allow 决策；票据重放和越权重试被阻断；A2/A3/A4 有可解释差异；`unknown` 高风险处置可统计；没有已知不变量失败。

**Pilot No-Go：** A3 无法区分合法数据处理与 authority-bearing 参数控制；A2/A3 只有日志差异；或高风险 `unknown` 未按规则处理。

### Phase 5：Paper-grade confirmatory run

#### 5.1 固定实验臂

| 编号 | 配置 | 论文作用 |
|---|---|---|
| A0 | 无防御 | 模型和任务本身的攻击/效用基线 |
| A1 | 当前 DSCG P0.5 | 工具级 fail-closed、仲裁、审计和工具元数据工程基线 |
| A2 | 参数 Contract，无 provenance | 测量参数级授权增益 |
| A3 | 参数 Contract + 字段 provenance/source-to-sink | 主候选机制 |
| A4 | 粗粒度拒绝高风险/不可信动作 | 判断 A3 是否只是拒绝更多 |
| A5 | AgentDojo 原生防御 | tool filter、detector、spotlighting、repeat prompt 对照 |
| A6 | 外部近邻与检测器 | 仅在同任务、模型、预算和指标可复现时加入 |

A2、A3、A4 必须共享同一 Contract 输入、模型、任务、候选动作、预算和 seed；只允许策略语义不同。A4 的拒绝阈值在验证集预先固定，不得看完测试结果再调节。

A4 的策略必须在协议中写成可执行规则：只要一个高风险 sink 或一个 authority-bearing 字段的 provenance 为 `untrusted_external`、`model_derived` 或 `unknown`，就拒绝整个动作，不做字段裁剪、恢复或临时放行；低风险且不涉及 authority 的合法数据处理可以继续。这样 A4 才是可复核的粗粒度对照，而不是为了得到某个 ASR 临时调阈值。

A5 不是一个可以随意命名的“原生防御”总分：协议必须提前列出每个实际运行的配置（例如 `tool_filter`、一个可运行的 detector、`spotlighting_with_delimiting` 或 `repeat_user_prompt`），分别保存版本、任务清单和成本；未能运行的配置标为 `blocked`，不能用其他配置的结果代替。

外部基线按优先级执行，避免复现工作阻塞主线：

1. **必须项**：A0–A5，以及一个自适应攻击压力测试（Adaptive Attacks 或等价的固定攻击预算协议）。
2. **强近邻项**：ACE、IPIGuard、ActGov、SkillGuard、TraceGrant 中至少选择一个可以在相同任务和指标上运行的系统；优先选择有公开代码和清晰执行入口的工作。
3. **检测器项**：MELON、AgentDojo 原生 detector 或其他可运行检测基线至少选择一个，并把重执行、token 和延迟成本计入。
4. **不可复现项**：没有公开代码、版本不匹配或依赖无法安装时，保留论文版本、阻塞日志和不等价原因，不能把论文报告数字直接放进 DSCG 主结果表。

只有第 1 类和机制因果实验通过后，才启动第 2、3 类；外部基线不能替代 A2/A3/A4 的主消融。

#### 5.2 主实验覆盖

- [ ] AgentDojo Workspace、Slack、Travel、Banking 四套件。
- [ ] E3 核心实验使用冻结的核心任务 manifest 和全部适用的预注册攻击模板；结果只能称为核心矩阵。
- [ ] E4 扩展实验覆盖四套件的全部有效 user/injection 组合；只有完成后才可称为完整 AgentDojo 结果。若因资源或代码阻塞无法完成，论文标题、摘要和主表必须明确限定任务子集。
- [ ] 同工具参数劫持、多阶段外发、合法数据处理、改写/分块/编码/Unicode 混淆、伪造角色、错误消息和自适应搜索攻击。
- [ ] 至少 2 个主模型（较强和较小）及 1 个独立审计模型；完整配置写入元数据。
- [ ] 每个任务对、配置和重复运行使用相同预算、重试上限和停止规则；模型支持 seed 时使用至少 3 个独立 seed，不支持时使用至少 3 次独立请求并明确记录为 repeated runs。
- [ ] 模型不可用、API 限流或超时单独记录，不静默换模型、删除困难任务或改变分母。

#### 5.3 指标和统计

- [ ] task ASR 与 action-level unauthorized side effect rate 分开报告。
- [ ] benign utility、utility under attack、fidelity/source-preserving utility 和 false refusal 分开报告。
- [ ] 报告恢复成功率、确认次数、unnecessary open privilege、provenance coverage 和 `unknown` rate。
- [ ] 报告敏感 source 到 external sink 的阻断率、P50/P95 延迟、token/API/费用成本和额外重试。
- [ ] 按套件、攻击类型、模型和 seed 分层，保存样本数和 95% 区间。
- [ ] 任务对作为主要独立单位，使用 paired permutation/McNemar 风格检验或 bootstrap/Wilson 区间并报告效应量。
- [ ] 不把 seed 或重复请求当作新的任务样本；任务对是主要独立单位，重复运行只用于估计模型随机性和运行不稳定性。
- [ ] 将审计超时/解析失败、策略错误、工具错误和基础设施错误分开统计。

**主结果停止线：** 只有当 A3 相比 A1 的安全收益不是由更激进的整任务拒绝造成，且 A3 相比 A4 在相近安全水平下保留更多效用，结果才可支持主论文 claim。

### Phase 6：结果分析和论文写作

#### 6.1 结果资产

- [ ] 原始轨迹、摘要结果、完整安全事件侧车和聚合表分开保存。
- [ ] 结果路径包含 `model/provider/suite/attack/defense/seed`。
- [ ] 每张图表能由一个命令从原始 JSON 重建，不手工修改。
- [ ] 保留至少一组成功防御、一组失败攻击、一组合法任务误拒绝和一组基础设施失败案例。
- [ ] 把 negative result、`unknown` 来源和已知边界写入结果，而不是只保留最好配置。

#### 6.2 建议论文结构

1. **Introduction**：外部内容可以是合法任务数据，但不应因此获得权威参数控制权；指出工具级/文本级防御的缺口。
2. **Threat Model and Scope**：明确可信组件、攻击者能力、保护对象和不覆盖的系统边界。
3. **Design**：Task Contract、字段 provenance ledger、传播规则、source-to-sink policy、Reference Monitor 和执行票据。
4. **Security Semantics**：定义 authority-bearing 字段、`unknown`、允许/拒绝/确认和重试/恢复语义；只给条件性安全陈述。
5. **Implementation**：说明与当前 DSCG P0 底座的集成、数据结构、运行成本和故障处理。
6. **Evaluation**：microbenchmark、A0–A4、AgentDojo、攻击变形、强近邻基线和成本。
7. **Failure Cases and Limitations**：隐式流、模型内部状态、受攻陷工具、可信宿主和未覆盖扩展。
8. **Related Work and Conclusion**：逐项回应 ACE、IPIGuard、MELON、SkillGuard、ActGov、TraceGrant、Ajar 和检测器的差异。

#### 6.3 Claim–evidence 表

- [ ] 每个主要 claim 绑定至少一个主实验、一个消融、样本数、置信区间和失败案例。
- [ ] “字段 provenance 带来增益”必须绑定 A2/A3 真实 sink 判决差异。
- [ ] “比粗粒度拒绝更可用”必须绑定 A3/A4 的匹配安全比较。
- [ ] “LLM 审计不是安全根”必须绑定审计器超时、拒答、注入和关闭审计器的结果。
- [ ] “可重放和可审计”必须绑定 ledger replay、事件完整率和票据/契约版本检查。

### Phase 7：复现包和投稿前审查

- [ ] 固定代码 commit、环境文件、依赖版本、模型配置模板和数据版本。
- [ ] 不提交 API Key、真实隐私数据或未脱敏的原始请求；提供可公开的 mock runtime 和最小样例。
- [ ] 提供一条命令重建主要表格和图表，提供一条命令运行离线安全不变量测试。
- [ ] 为每个外部基线记录论文版本、代码 commit、benchmark 版本、攻击模板、任务数、指标定义和复现状态。
- [ ] 公开或随论文附带失败样本、误拒绝样本和边界条件说明。
- [ ] 投稿前由第二人按威胁模型、统计分母、任务配对、基线等价性和 claim–evidence 表做独立审查。

## 3. Go / Conditional Go / No-Go

这些是论文主线的工程闸门，不是录用保证。

### 3.1 顶会就绪的硬条件

即使工程实现已经完成，只有下面四条同时满足，才可以把结果称为“具备冲击安全顶会的证据基础”：

1. **差异可成立**：`docs/paper/novelty_gate.md` 证明主机制与至少一个最近邻在执行点、字段派生、`unknown` 语义或拒绝粒度上存在可检验差异，并且没有被新文献直接覆盖。
2. **因果可归因**：microbenchmark 和 A1–A4 在同一候选轨迹上显示 provenance/source-to-sink 真的改变了 sink 判决；A3 的效用优势不能由更激进的整动作拒绝解释。
3. **外部可推广**：四套 AgentDojo 套件、至少两个主模型、多个攻击模板和自适应压力测试完成；至少一个强近邻在等价任务、预算和指标下可运行复现。
4. **可复核可复现**：所有主表数字可从带 commit、环境、manifest、分母和失败状态的原始结果重建，第二人可以按复现包运行离线检查和最小实验。

缺少任一条时，仍可以形成工程报告或收缩后的 workshop/短文，但不得在摘要中使用“通用防御”“完整 AgentDojo 结果”或“顶会就绪”等表述。

### Go：继续主线并准备投稿

- [ ] P1/P2 DoD 全部通过，在线判决可从原始事件重放。
- [ ] microbenchmark 证明 A2/A3/A4 有真实且可重复的判决差异。
- [ ] A3 相比 A1 降低 task ASR 或 action-level 未授权副作用；A3 相比 A4 在相近安全下提高 utility/fidelity。
- [ ] benign utility、`unknown` 率、延迟和成本达到预注册范围。
- [ ] 至少一个强近邻基线完成等价配置复现；若所有强近邻均因外部依赖阻塞，只能进入 Conditional Go，不能宣称“顶会就绪”，并须把阻塞和不等价原因放在主文限制中。
- [ ] 主要 claim 均有安全、效用、成本、失败案例和原始轨迹证据。

### Conditional Go：收缩论文主张

- [ ] 机制只在同工具参数劫持或多阶段外发中的一个子集有效。
- [ ] A3 有安全收益，但 utility 损失超过预设范围，或只在特定模型/套件有效。
- [ ] 只能证明工程基线和条件性改进，不能主张一般性 IPI 防御。

此时论文应缩小为“特定 source-to-sink 场景的字段级策略研究”，完整报告失败边界和成本。

### No-Go：停止扩大机制

- [ ] A3 的安全收益主要来自比 A4 更激进的全局拒绝。
- [ ] 无法证明 provenance 改变真实 sink 判决。
- [ ] 高风险 `unknown` 不能按预注册规则处理，或安全不变量失败。
- [ ] 结果只来自单一任务、单一攻击模板、单一模型或单次 API 运行。
- [ ] 基线、任务选择、统计分母或指标定义无法复核。

No-Go 后先修正机制和协议，不通过增加检测器、扩大规则或删去失败样本掩盖结果。

## 4. 暂不做的事项

- [ ] 不把工具白名单、日志、票据、能力图或安全模型单独包装为新颖算法。
- [ ] 不把 LLM Checker 的 `allow` 当成授权来源；最终判决必须由确定性策略层完成。
- [ ] 不使用 embedding 相似度作为污点证明。
- [ ] 不把单一 `important_instructions` 结果称为完整 AgentDojo 结果。
- [ ] 不把降低 ASR 等同于安全性提升；同时报告效用、保真度和成本。
- [ ] 不在 P1/P2 未通过前扩展多模态、多 Agent、MCP、跨会话记忆或在线学习。
- [ ] 不因某个外部代码仓库存在就称其已复现；必须锁定 commit、环境和运行结果。
- [ ] 不在没有数据支撑时使用“首次”“彻底解决”“形式化保证”“通用防御”等表述。

## 5. 每周执行记录

每次推进只更新本节和相关代码/结果链接，保留日期、commit、完成项和阻塞原因。

| 日期 | 阶段 | 完成项 | 证据/commit | 阻塞与下一步 |
|---|---|---|---|---|
| 2026-09-27 | Phase 0 | 建立论文计划文档；明确 provenance 主线、A0–A4 和 Go/No-go | `Paper_TODO.md` | 待完成 P0 DoD、P1/P2 实现 |
| 2026-09-27 | Paper_TODO audit | 增加 Agent 任务队列、环境/新颖性闸门、固定 A4 粗粒度基线、本地副作用 oracle 和顶会硬条件 | `Paper_TODO.md` | 下一步执行 `P0-AUDIT`、`P0-ENV`、`P0-NOVELTY`；未完成证据前不启动正式实验 |
