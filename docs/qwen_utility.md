# 提示候选与效用诊断

对应当前v3.5.4策略，后续作为v3.6优化基线保存；默认static-task-v354两阶段授权，legacy为显式单次授权对照。本页区分当前策略、历史候选和诊断工具。组件判断和人工期望不等于原生任务TSR／ASR。

## 当前默认两阶段L2

`static-task-v354`：完整可信请求→静态任务视图→一次全局工具权限表。视图含intent、原文引用位置、顺序／条件，供规划、L2和L3共享；原始任务仍保留。

- 通常多1次main调用：authorization_intents提取视图，authorization_tools编译权限。
- 宿主映射逐字片段ID并检查互斥关系分支；未知ID拒绝，不修补／重试／回退。这些检查不认证语义完整、业务条件或完成；不建立进度FSM、完成闸门或恢复链。
- `static-task-v352`保留v3.5.3逐字引用协议；v3.5.2正式结果为legacy。旧记录不迁移，专项收益不外推到全量。

以下会真实调用模型，示例仅为AgentDojo前缀范围：

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --prompt-profile legacy --name v36_legacy_diag_01 --progress
python -m experiments.run_partial_benchmark --suites banking slack \
  --prompt-profile static-task-v354 --name v36_static_diag_01 --progress
```

CLI／Dashboard API已支持static的NoChecker／NoL2（路由须off）；baseline仅legacy，其他历史候选仍要求L2／L3。profile是运行策略，不是模型TOML字段；页面无选择控件。新策略使用新运行名，不跨profile复用旧缓存。

<a id="task-alignment-v1"></a>

## 保留的历史profile

| profile | 原用途 |
| --- | --- |
| protocol-v1 | 加强四字段输出约束 |
| tool-semantics-v1 | 在protocol候选上增加原生schema及工具效果解释 |
| source-context-v1 | 在上一候选上澄清来源事实与当前任务关系 |
| task-alignment-v1 | 独立精简L2／L3提示，按当前动作判断对齐 |
| intent-evidence-v35 | 历史DSCG_v3.5候选，L3附assessment，与当前默认v3.5.4不同 |

profile同名不证明跨版本提示相同，以冻结输入／配置摘要为准。2026-10-21组件诊断和2026-10-23后续候选均未推广，详见[历史诊断](../workshop/completed/utility_diagnosis_20261021.md)及[后续报告](../workshop/completed/v35_followup_20261023.md)。历史预算已关闭，不作当前调用授权。

## 离线分阶段诊断

下列命令不创建模型客户端、不执行工具，输出路径须新建且位于workshop/artifacts。示例日期／任务占位符请替换。

```bash
python -m experiments.diagnostics.utility_stages export --stage audit \
  --output "workshop/artifacts/<YYYYMMDD>_<task>/audit.json"
python -m experiments.diagnostics.utility_stages compare \
  --bundle "workshop/artifacts/<YYYYMMDD>_<task>/audit.json" \
  --output-dir "workshop/artifacts/<YYYYMMDD>_<task>/comparison"
python -m experiments.diagnostics.utility_stages traces \
  --trace /absolute/path/to/task.json \
  --output "workshop/artifacts/<YYYYMMDD>_<task>/signals.json"
```

stage还有authorization／source；默认authorized-v2补齐合成授权、schema和逐项allowlist。它模拟已授权状态，不等于真实L2；legacy-v1用于旧包回放，不把旧响应重绑新提示。缺响应时为not_measured，不判通过。

响应导入须匹配bundle_sha256与request_sha256，保留原始content、finish_reason、拒答及usage；API错误不伪造回复，缺用量未知。人工标签不进入模型提示。比较器分别报告协议失败、合法动作误拒、额外放行、漏工具、完整性和成本；diagnostic_gate_passed仅为组件条件，不自动改默认或证明任务收益。

<a id="真实响应采集须明确授权预算模型与发送内容"></a>

## 真实响应采集

`utility_collect`是独立在线工具，只有显式execute、次数上限和新输出目录才发送请求；行为验证已有免逐次确认授权，但当前在线请求仍只允许qwen3.7-flash，历史阶段预算不可复用。先核对reference manifest的实际模型／provider，DeepSeek或其他模型的记录不得用于发送请求。参数先用 `--help`查看：

```bash
python -m experiments.diagnostics.utility_collect --execute --stage audit \
  --reference-manifest /absolute/path/to/run_manifest.json \
  --max-calls 96 --output-dir "workshop/artifacts/<YYYYMMDD>_<task>/audit_run"
```

96仅为命令上限示例，不代表当前批准量。按manifest的公开模型配置及当前凭据调用，不替换本地默认；SDK重试0，不执行工具。逐次保存attempt、响应、请求哈希与usage，不保存密钥或隐藏推理。首个接口错误即停，协议错误留证；不自动重试／续跑／换模型或覆盖目录。

## 从轨迹定位问题

先区分：漏授权、已授权但未提议、L3语义误拒、实际参数错误、工具执行错误、最终交付遗漏和输出污染。信号可重叠，不根据一条错误码指定唯一因果。

审计协议失败与Monitor记录／回执失败分开；原始L3回复见.dscg.responses.jsonl，实际动作看主JSON与最终ledger。来源含注入不自动证明当前动作违规；一次allow也不证明安全。旧READ_ONLY_SOURCE_ALLOW只解释历史轨迹，不覆盖当前私人读取deny。

后续任务评测应匹配baseline／legacy／候选的实际任务ID、注入内容、模型、fliter范围及实际保留任务键，并保留clean／攻击控制及全部错误／成本；partial前缀不能验证后续问题任务。最新失败类型见[v3.5.4结果分析](../analysis/v3-5-4.md)，详细文件见[结果指南](result_files.md)。
