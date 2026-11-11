# Framework updates for the next agent

更新时间：2026-10-08。本文是框架运行状态的交接说明。网页和 dashboard 工作已交给其他对话；本文件只描述 DSCG 防御运行逻辑、验证边界和框架优化工作。本文不代表新的论文机制已经实现，也不代表研究侧已经确认创新性。

## 当前版本

- 当前代码基线：`7f16f19a33045a9c055230534d87b9e408a74649`。
- 除本交接文件外，当前分支工作树只保留用户预先删除的 `System_TODO.md`；不要恢复或覆盖该删除。
- 当前运行框架仍是 **V2 stage1 两层防御**。最近的 dashboard 提交只更新展示，不改变防御执行逻辑。
- 研究路线入口是 [`../research/technical_route.md`](../../research/technical_route.md)，实现回报追加到 [`../research/paper/implementation_status.md`](../../research/paper/implementation_status.md)。未解锁的研究候选不能直接实现成默认机制。

## 当前运行结构

```text
可信用户请求
      │
      ▼
第一层：可信任务工具授权（主模型提出候选调用前）
      │
      ▼
主模型提出当前动作
      │
      ▼
第二层：当前动作语义审计
      │
      ▼
Reference Monitor → 一次性 ExecutionTicket → 工具执行
```

### 第一层：可信任务工具授权

`OurFrameExecutor` 在主模型生成候选调用前，通过 `ToolAuthorizationCompiler` 编译当前可信用户回合的工具权限。授权输入来自 `TrustedTaskRequest`、宿主固定策略、注册工具和风险元数据；assistant/tool history 和工具反馈都不能授予新权限。

已生效的修正包括：

- 工具目录按名称排序，授权请求使用 `temperature=0`；这只减少请求层随机性，不承诺 provider 完全确定。
- 支持条件任务语义：用户已经提出的动作可以获得必要的准备读取能力，但读取不会自动授权付款、发送、写入或新目的地。
- 编译错误、空请求、未知工具、无效 JSON/schema、缺失元数据和内部错误均 fail closed，并清空权限。错误码会进入结构化 trace，原始 provider 错误不会写入报告。
- `PermissionSandbox` 区分 `UNINITIALIZED`、`INITIALIZED_EMPTY`、`ALLOWLIST` 和 `ERROR`；未初始化、空策略或错误状态都拒绝执行。
- 工具风险元数据的默认回退文件是 `config/tools.agentdojo-v1.2.toml`。优先级为显式路径、`DSCG_TOOL_METADATA`、已有本地配置、仓库内置配置。默认运行不要求外部 manifest 或新配置文件。

### 第二层：当前动作语义审计

`ActionSecurityChecker` 只审计当前候选动作是否符合可信任务，不负责生成权限，也不负责恢复任务。审计输入包括当前调用、有限 `ActionLedger`、宿主注册工具描述和最近工具返回：

- 候选工具的宿主描述最多 512 个字符，来自注册运行时元数据，不接受工具反馈覆盖。
- 最近最多 4 条工具返回，每条最多 2,048 个字符；全部显式标记为不可信，并保留截断信息。
- 读取任务事实与后续外传/写入分开判断。无具体目标的必要查阅可以获取未知事实；具体对象、URL、收件人或目的地仍需要可信任务证据。
- 输出必须是结构化 `allow`、`deny` 或 `abstain`，并带 `violations`、`confidence` 和 `reason_code`。缺失、无效、超时或不确定结果默认阻断。
- 已明确分类的低风险公开读取可以使用 `READ_AUDIT_BYPASS`；未知或高风险工具仍进入语义审计。

这层的上下文处理是语义辅助，不是对象、参数、数据选择或 provenance enforcement。它不会从工具返回中补授权，也不会把工具反馈变成可信任务要求。

### 执行完整性基础设施

Monitor/ticket 是执行基础设施，不是第三层防御：

- `ActionLedger` 状态为 `PROPOSED → APPROVED/BLOCKED → EXECUTED/FAILED`。
- `ReferenceMonitor` 是一次性票据的唯一签发者。
- `ExecutionTicket` 绑定 `action_id`、调用指纹、契约版本、nonce 和签名。
- `TicketedToolsExecutor` 只执行带有效且未使用票据的原调用；票据重放单独记录并阻断。
- 每个外层任务开始时重置授权缓存、沙箱和票据；任务结束时撤销未使用票据。
- 阻断或工具错误会以结构化工具错误返回给主模型。重规划产生的新候选仍需重新经过授权、审计、Monitor 和票据校验。

## 默认配置

| 配置 | 当前默认值 | 说明 |
| --- | --- | --- |
| `use_sandbox` | `true` | 启用权限沙箱、Monitor 和票据执行路径 |
| `use_security_checker` | `true` | 启用当前动作语义审计 |
| `audit_retries` | `0` | 不自动叠加旧的重审候选 |
| `completion_prompt` | `false` | Stage2 execution prompt 已评估并撤回 |
| `trace_level` | `summary` | 保留摘要；`full` 仅诊断，增加序列化、压缩和写盘开销 |

不要把 `trace_level=full` 当作更强防御。它会保存更完整的审计/动作轨迹和压缩 sidecar，适合排错，不适合默认对照。

## 常用命令

用户已经激活 `ipi` 环境时使用 `python`；临时 agent 输出必须放在新的 workshop artifact 目录。不要把临时结果写入根 `results/`、`result/`、`examples/` 或旧 `workshop/results/`。

匹配的 partial baseline 与当前框架对照：

```bash
python -m experiments.run_partial_benchmark \
  --baseline --force-rerun --name <new-baseline-name>

python -m experiments.run_partial_benchmark \
  --force-rerun --name <new-defense-name>
```

默认攻击是 `ignore_previous`、`injecagent`、`important_instructions`、`tool_knowledge`。输出布局为 `<model_id>_<name>/<attack>/<suite>/`；默认典型集合用于控制工作量，不表示攻击强度已经验证。

临时运行示例：

```bash
python -m experiments.run_partial_benchmark \
  --force-rerun \
  --name <new-run-name> \
  --results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark
```

离线回归和已有 fixture 的验证：

```bash
python -m unittest discover -s tests -v
python -m experiments.i3_p0_stress \
  --output workshop/artifacts/<YYYYMMDD>_<task>/i3.json
python -m experiments.harness_audit \
  --fixture tests/fixtures/harness_audit_cases.json \
  --output workshop/artifacts/<YYYYMMDD>_<task>/e0.json
```

I3 当前预期退出码是 `1`（`partial`，存在范围缺口）；只有所有约束通过时才是路线意义上的 `no_go`，退出码 `2` 表示样本错误。E0 命令是合成 self-check，不等于真实 harness 通过研究闸门。

## 已验证状态

这些是带日期的工程快照，不是 benchmark 防御率，也不是每次运行必须固定得到的数字：

- 撤回 Stage2 execution prompt 后的最终离线回归：169/169；其中 I3 测试 18 项。
- Stage1 新增 dashboard Node 检查快照：21/21；最新 dashboard 配置/历史 Python 测试快照：20/20。
- I3-P0-STRESS：24 条有效 probe，`scope_violations=8`，`tool_boundary_violations=0`，状态 `partial`。真实并发重复票据 bug 已修复，重复请求会收到自己的阻断事件，不再让并发赢家失败。
- E0 synthetic self-check：6 条，`valid=1`、`tool_error=1`、`infrastructure_error=4`；不能据此宣称真实 harness 已通过。
- 现有 AgentDojo 历史结果仍是 smoke/比较材料。模型服务版本没有固定，单次 partial 运行不能建立因果安全结论。

详细 I3 证据见 [`i3_p0_stress_report.md`](./i3_p0_stress_report.md)；V2 阶段记录见 [`workshop/completed/framework_v2_report.md`](../workshop/completed/framework_v2_report.md) 和 [`workshop/completed/framework_v2_followup_report.md`](../workshop/completed/framework_v2_followup_report.md)。

## 已知边界与禁止事项

当前实现仍是工具级防御：

- 参数、对象、目的地、数据选择、跨来源 provenance/source-to-sink 约束尚未实现。
- I3 中的范围反例不能被解释成对象或数据权限已经强制执行；不得报告 `no_go`，也不得声称恢复只会补做缺失义务。
- `I2-FIXTURE`、`I2-PILOT` 仍 locked；`E0-HARNESS-AUDIT` 与 `I3-P0-STRESS` 是路线标记的 ready 任务，完成后仍需按研究侧审核。
- `P0-ALT-SELECT` 尚未通过。旧字段 provenance 路线已关闭，不要换名字重新实现。
- 三层候选、授权对照校准和 workshop 中的其他 proposal 都是待研究假设；不要写成当前代码行为或论文创新结论。
- Stage2 execution prompt 已 withdrawn；不要把历史 `executor_probe.py shipped` 当作当前运行命令。
- 不要通过猜测缺失日期、账单字段、收件人或目标来提高任务成功率，也不要把最终回答中的警告引用自动当成真实安全成功或失败。

## 后续智能体的工作边界

1. 只在 `../research/technical_route.md` 明确解锁后修改防御运行逻辑；先读该路线和 `../research/paper/implementation_status.md`。
2. 新测试源码和 fixture 放在 `tests/`，可复用 runner 放在 `experiments/`；新生成输出固定放在 `workshop/artifacts/<YYYYMMDD>_<task>/`，使用新名称且不覆盖历史证据。
3. 完成一个已解锁任务后，按研究回报模板记录精确命令、退出码、代码 commit、工作树、artifact 路径和 SHA-256、样本分母、限制与一个下一步；不要在 DSCG 内复制论文计划。
4. 保持两层简单。只有在研究侧选择独立角色并批准第三层后，才讨论三层实现；不能因为一次小样本结果就叠加重试、完成提示、恢复回路或外部配置。
5. 本轮网页/dashboard 工作不在本交接范围内；不要因本文件修改 dashboard 或把展示层变化当成防御逻辑变化。

本文件用于同步事实和边界。它不替代研究侧路线、实现状态或正式实验报告。
