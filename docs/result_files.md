# 结果文件与诊断

适用于 **GrantBind v3.7**，默认 `static-task-v354 / DSCG_v3.7`，布局为 `flat-v1`。以 run_manifest.json 的实际配置判断运行身份，运行名只命名实验。CLI 默认目录如下。

```text
results/{benchmarks,partial_benchmark}/<backend>/<model>/<name>/
  run_manifest.json       # 单一根配置绑定（common/groups、任务范围与筛选设置）
  summary.json / summary.md  # GOAL checkpoint／筛选与测量汇总
  fliter.json             # 仅复制输入排除名单，不合并GOAL新增排除
  failure_cases.jsonl
  l3_router_summary.md / l3_router_summary.json
  goal/<suite>/<injection>.json  # 仅启用--goal时
  <attack>/<suite>/
    summary.json / detailed_results.csv
    dscg_config.<摘要>.json
    <user>/<injection>.json
    <user>/<injection>.dscg.jsonl
    <user>/<injection>.dscg.responses.jsonl
```

消融归档按**变体**（`full`／`noL3`／`noL2`）归并，与普通运行同样按攻击／场景展开；Dashboard 把 `ablation` 当作模型字段，变体名就是运行名（`model=ablation`、`run_name=full|noL3`），并额外记录 `is_ablation`／`ablation_arm`：

```text
results/<folder>/<backend>/ablation/<variant>/
  README.md                 # 变体说明、来源臂与版本注意事项
  derived_provenance.json   # 来源臂、commit、逐文件 sha256
  summary.json              # 聚合视图（derived=true），不是新运行
  <attack>/<suite>/         # 各臂数据原样移入
    summary.json / detailed_results.csv
    <user>/<injection>.json
  _arms/<suite>/            # 原臂根文件，改名 *.arm.* 以免被当成场景摘要
    summary.arm.json / run_manifest.arm.json / failure_cases.arm.jsonl / execution/
```

约束：

- 各臂数据原样移动，不重算、不改标签；不合成 `run_manifest.json`（来源不同，合成等于造记录），原始 manifest 保存在 `_arms/<suite>/`。
- 派生参考臂（例如从 `qwen3.7-flash/v3.6.3` 复制的 banking 子集）放在所属变体的 `_arms/<suite>/` 并带 `README.md`／`derived_provenance.json`；报告与 Dashboard 说明必须标注"派生"与源版本。
- 归档臂不可按旧路径 `--reuse` 续跑。

正式 workshop 测量指定 `--results-dir results/workshop`，路径为 `results/workshop/<backend>/<model>/<name>/`。agent 临时验证输出到新的 workshop/artifacts 任务目录。

clean使用 `none/<suite>/<user>/none.json`。GOAL原生JSON也保留同名诊断sidecar；结果逐目标写入根summary.json的selection_report.goal_checks，续跑不重试已开始目标。筛选与GOAL排除不算任务缺失、失败或已计分样本。

独立`screen`同样只生成根`run_manifest.json`（`dscg.fliter-screen.v1`）和`summary.json`／`summary.md`，另有最小`fliter.json`与`goal/<suite>/<injection>.json`。`summary.json.selection_report.goal_checks`使用`passed`／`failed`／`error`状态、GOAL相对路径和`cost.models`；usage未知时成本为null。`attempts/`只承载一次执行与恢复必需的状态、证据引用和记账，不重复轨迹或完整配置。旧`screen_manifest.json`／`status.json`只读复用，不在原目录迁移／写入续跑。

旧`benchmark_plan.json`／`attack_manifest.json`／`screened_run_manifest.json`、场景run_manifest与`<user>/<attack>/<injection>.json`继续可读；Dashboard／历史导出兼容两种布局。新运行不生成这些重复绑定，不迁移旧文件。

## 从哪里开始看

| 文件 | 用途 |
| --- | --- |
| 根summary.json | 结构化筛选报告、GOAL checkpoint、测量状态与场景汇总／配置引用 |
| 根summary.md | 实际配置、每攻击／场景指标、有效分母、错误、已知Token，最多10个失败入口 |
| failure_cases.jsonl | 完整失败／攻击成功／错误／缺失索引，片段仅作定位线索 |
| run_manifest.json与公共配置 | 实际模型、defense_version、profile绑定、任务ID、风险目录和执行控制 |
| 场景summary.json／CSV | 逐任务标签与聚合数据，供历史分析读取 |
| l3_router_summary.md／json | 实际路由、审计／Monitor统计、配置分组和缺失证据 |
| execution／reuse记录 | 运行进程状态、续跑校验与旧汇总／不完整轨迹快照 |

## 精简任务轨迹与独立诊断

- **主JSON**保留原生messages／injections、utility／security、error、时间和任务ID，只增加dscg_diagnostics引用。
- **`.dscg.jsonl`**保存授权、动作最终状态、L1／L2／L3／Monitor统计和实际成本；按attempt和字节位置绑定。task_end状态不是任务成功标签。
- **`.dscg.responses.jsonl`**在解析前保存完整L3 content／refusal、finish_reason、usage及响应引用，格式错误／截断同样保留；不保存隐藏推理、凭证、HTTP头或SDK对象，API无返回不伪造文本。
- **公共配置**每攻击／场景去重保存；L2只保存解析后的授权，不重复存完整提示和工具正文。新执行不生成旧full gzip，读取器仍支持历史inline／v1／gzip。

`trace-level=summary/standard/full`只控制诊断详细度，主JSON始终精简；full增加写盘成本。cache命中不改旧文件、不补回复；真实再执行追加新attempt，不混入旧错误。缺失／损坏／未结束诊断明确标未知，费用不补零。

```python
from dscg.task_diagnostics import load_task_trace
trace = load_task_trace('/absolute/path/to/task.json')
```

读取器在内存合并侧车，不写回原文件。跨分支历史intent／progress字段可读，**当前默认没有host意图进度FSM**。

## 如何确认使用了两阶段 L2

v3.7 默认通常先记录 `authorization_intents`，再记录 `authorization_tools`；授权记录包含 static_task_view／protocol，规划器和 L3 共享辅助任务视图。纯读目录和受限 host 路径可能有例外，缺诊断不能当作零调用。

核对根 manifest 的 defense_version、prompt_profile 绑定、authorization_input 和 audit_presentation，不能从目录名判断策略。当前默认后两项均为 v3。

L2 的 tool_permissions／allowed_tools 表示冻结工具权限；static_task_view 的原文位置证明字面匹配。具体条件、调用参数和任务完成情况仍需核对原生消息与 ledger，机制见 [架构说明](architecture.md)。

## 审计与请求诊断

默认L3为 `dscg.audit-decision.v2`，四字段decision／violations／confidence／reason_code。协议、记录校验和回执交接失败分开统计；不能只凭AUDIT_SCHEMA_INVALID断定模型JSON格式失败。

`audit_request` 记录实际审计输入摘要／历史引用，`model_request` 记录实际请求字段。模型对象 temperature=0 不代表请求发送了 0。公开配置记录 sdk_max_retries=0，原生 generation 仍可能内部重试。

L2_BLOCKED／L3_BLOCKED／MONITOR_BLOCKED区分来源，旧DSCG_BLOCKED继续可读。来源含注入、模型解释或一次allow都不是独立安全／完成证明；最终文本没有单独动作审计。

## 如何理解L3统计

当前sink-free-read-v4在三模式均固定免审授权、参数有效的无sink public/internal读取；其他调用继续审计。off不关闭L3，shadow也不是全量审计，阈值不改变免审。

报告按实际策略／配置分组，区分固定免审、实际模型审计、Monitor 决定、协议失败和未知覆盖。audit_decision_final 也可能是固定免审的宿主判决，不能把判决条数直接当作 L3 模型调用次数，应同时核对 model_request 与成本记账。

would_bypass／actual_bypass及审计分歧不是安全标签；已知候选审计Token只是相应范围小计，没有反事实就不报告实际节省。缺轨迹／usage为unknown，不能从零计数推断零成本。只统计声明计分任务，不混入GOAL、reuse快照或其他运行。

## 成本与评分

TSR／ASR 以原生标签的有效分母计算，错误／缺失／unsupported 另列，clean ASR 不适用。总 Token 优先读取根 summary.json 的 cost_summary.scored.known_total_tokens 并同时报告 unknown_usage_records；不能仅用 overhead 的主模型用量代替总量。分别核对 main（含 L2）、security、计分与 GOAL、本次调用与缓存／整轮成本，避免重复累加。cost_comparison_ready=false 时不算节省比例。

API／超时／输入和内部错误按基础设施错误处理；共享读取器合并当前attempt后，若已记账`failed_calls>0`，派生效用／安全标签为null，保留原生等级、实际效果与未知usage；旧attempt不污染新attempt。旧持久汇总不自动回写，未记账的失败无法推断。新投影策略绑定reuse身份，须使用新名称。协议阻断也不能仅凭“框架失败”删出TSR；保留原评分及实际效果。

## 工具参数错误记录

CLI full／partial的 `task_errors.jsonl`追加主模型工具参数JSON错误：调用／任务ID、阶段、错误码、位置、长度、结束原因和有限堆栈，不存参数正文。当前任务整批不执行、不修补／重发；派生标签为空，计分与GOAL错误分开，有错误退出1。

历史错误文件不反推覆盖当前成功结果，旧完整错误缓存不自动重跑。该隔离不适用于screen／Dashboard及其他JSON异常，详见[运行指南](benchmark.md#工具参数-json-解析错误)。

## 给旧目录补充报告

离线命令，不需Key或相同后端安装：

```bash
python -m experiments.diagnostics.summarize_results --run-dir /absolute/path/to/run
```

默认仅新增两份l3_router_summary，不改原始轨迹／summary／CSV／manifest／cohort；报告已存在则拒绝覆盖。`--refresh`仅替换本工具产物，运行须已停止。不自动扫描修改整个results。新运行不生成多层重复TXT，旧文件保留。
