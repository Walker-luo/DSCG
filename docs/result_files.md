# 结果文件与诊断

对应v3.5.4。历史结果保留各自配置和标签，不按当前版本重标。CLI默认目录：

```text
results/{benchmarks,partial_benchmark}/<backend>/<model>_<name>/
  benchmark_plan.json 或 screened_run_manifest.json
  attack_manifest.json
  summary.json / summary.md
  failure_cases.jsonl
  l3_router_summary.md / l3_router_summary.json
  <attack>/<suite>/
    run_manifest.json / summary.json / detailed_results.csv
    dscg_config.<摘要>.json
    <user>/<attack>/<injection>.json
    <user>/<attack>/<injection>.dscg.jsonl
    <user>/<attack>/<injection>.dscg.responses.jsonl
```

clean使用 `none/<suite>/<user>/none/none.json`；GOAL预检独立保存。Dashboard目录结构保留，历史读取器按声明范围找轨迹，不搬移文件。

## 从哪里开始看

| 文件 | 用途 |
| --- | --- |
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

## 如何确认使用了两阶段L2

历史正式v3.5.2为legacy：单次`authorization`。v3.5.3为static-task-v352，v3.5.4默认static-task-v354（视图协议v2）；均通常先记 `authorization_intents`，再记 `authorization_tools`，授权记录含static_task_view／protocol；规划与审计共享辅助视图。

legacy的profile绑定可能为空，须联合版本、配置及实际调用核对；不要从目录名判断。纯读零调用或受限host路径可有例外，缺失诊断也不能当作零调用。

L2记录中tool_permissions／allowed_tools表示冻结工具权限；static_task_view的原文位置仅证明字面匹配，不证明语义完整或执行完成。历史authorization_steps及intent-evidence-v35的assessment按原协议解释，不能当作当前完成证据。

## 审计与请求诊断

默认L3为 `dscg.audit-decision.v2`，四字段decision／violations／confidence／reason_code。协议、记录校验和回执交接失败分开统计；不能只凭AUDIT_SCHEMA_INVALID断定模型JSON格式失败。

v3.5.2补充实际审计输入摘要／历史引用及 `model_request` 的实际采样字段；模型对象temperature=0不代表请求发送了0。公开模型配置记录sdk_max_retries=0，但原生generation可自带重试。

L2_BLOCKED／L3_BLOCKED／MONITOR_BLOCKED区分来源，旧DSCG_BLOCKED继续可读。来源含注入、模型解释或一次allow都不是独立安全／完成证明；最终文本没有单独动作审计。

## 如何理解L3统计

当前sink-free-read-v4在三模式均固定免审授权、参数有效的无sink public/internal读取；其他调用继续审计。off不关闭L3，shadow也不是全量审计，阈值不改变免审。

报告按实际策略／配置分组，区分固定免审、实际审计、Monitor决定、协议失败和未知覆盖。历史threshold-read-v1、read-purpose-v2、独立校准记录保留原含义，不重解释成当前规则。

would_bypass／actual_bypass及审计分歧不是安全标签；已知候选审计Token只是相应范围小计，没有反事实就不报告实际节省。缺轨迹／usage为unknown，不能从零计数推断零成本。只统计声明计分任务，不混入GOAL、reuse快照或其他运行。

## 成本与评分

TSR／ASR以原生标签的有效分母计算，错误／缺失／unsupported另列，clean ASR不适用。分别核对main（含L2）、security、计分与GOAL、invocation与缓存／整轮成本；不能重复累加路由Token或将未知usage补零。cost_comparison_ready=false时不算节省比例。

API／超时／输入和内部错误按基础设施错误处理；共享读取器合并当前attempt后，若已记账`failed_calls>0`，派生效用／安全标签为null，保留原生等级、实际效果与未知usage；旧attempt不污染新attempt。旧持久汇总不自动回写，未记账的失败无法推断。新投影策略绑定reuse身份，须使用新名称。协议阻断也不能仅凭“框架失败”删出TSR；保留原评分及实际效果。

## 工具参数错误记录

CLI full／partial／cohort的 `task_errors.jsonl`追加主模型工具参数JSON错误：调用／任务ID、阶段、错误码、位置、长度、结束原因和有限堆栈，不存参数正文。当前任务整批不执行、不修补／重发；派生标签为空，计分与GOAL错误分开，有错误退出1。

历史错误文件不反推覆盖当前成功结果，旧完整错误缓存不自动重跑。该隔离不适用于screen／Dashboard及其他JSON异常，详见[运行指南](benchmark.md#工具参数-json-解析错误)。

## 给旧目录补充报告

离线命令，不需Key或相同后端安装：

```bash
python -m experiments.diagnostics.summarize_results --run-dir /absolute/path/to/run
```

默认仅新增两份l3_router_summary，不改原始轨迹／summary／CSV／manifest／cohort；报告已存在则拒绝覆盖。`--refresh`仅替换本工具产物，运行须已停止。不自动扫描修改整个results。新运行不生成多层重复TXT，旧文件保留。
