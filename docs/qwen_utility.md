# v3.7 效用与消融诊断

默认 `static-task-v354`，运行标识 `DSCG_v3.7`。机制见 [架构](architecture.md)，排错时先检查实际配置、任务键和有效分母。

## 从失败轨迹定位

| 现象 | 核对证据 |
| --- | --- |
| 漏授权 | 原始用户请求、static_task_view、tool_permissions／allowed_tools；条件动作是否在授权范围内 |
| 已授权但未提议 | 主模型工具可见性、逐轮 tool_calls 和最终答复，确认是否存在查询或参数缺口 |
| 合法动作误拒 | 实际候选参数、相关原始返回、完整 L3 可见回复及 final_policy_decision |
| 调用未执行 | action_ledger 的最终 state、blocked_by、reason_code，以及原生工具返回 |
| 最终交付失败 | 成功工具效果与最终答复是否满足用户请求，不能只看工具调用成功 |
| 成本增长 | authorization_intents、authorization_tools、generation、audit 的实际调用与 Token |

L2 授权是工具能力集合，L3 判断当前具体调用，二者不能互相替代。来源含注入不自动证明当前动作违规；多个信号可能同时出现，需与 baseline 同键比较。原始证据、诊断引用与读取方法见 [结果文件](result_files.md)。

## 消融解释

`--no-checker` 关闭 L3，仍保留 L1、L2 和 Monitor；`--no-sandbox --audit-router-mode off` 关闭 L2 及相关前置、授权工具视图和委托处理，仍保留 L3。两者均使用新运行名，记录完整 manifest。

当前 NoL2 路径同时跳过工具元数据初始化，可能使所有候选变成 unknown／critical，导致 L3 大量 abstain。应先核对 ledger 的 metadata_state／effect，修复该干扰后再解释 L2 的独立贡献。最新消融事实见 [当前问题](framework_updates.md)。

NoL3 的零 ASR 只说明剩余组件和主模型在本批样本上没有原生命中。需同时查看攻击 baseline、TSR、实际动作和 L3 阻断；单轮结果无法独立确定各层贡献。

## 离线分阶段诊断

以下命令不创建模型客户端或执行工具，输出须为新路径。

```bash
python -m experiments.diagnostics.utility_stages export --stage audit   --output "workshop/artifacts/<YYYYMMDD>_<task>/audit.json"
python -m experiments.diagnostics.utility_stages compare   --bundle "workshop/artifacts/<YYYYMMDD>_<task>/audit.json"   --output-dir "workshop/artifacts/<YYYYMMDD>_<task>/comparison"
python -m experiments.diagnostics.utility_stages traces   --trace /absolute/path/to/task.json   --output "workshop/artifacts/<YYYYMMDD>_<task>/signals.json"
```

stage 还可选择 authorization／source。导出的 authorized-v2 输入模拟已授权上下文，人工期望和合成回复只能验证工程逻辑，不能证明真实 L2／L3 判断质量或任务 TSR／ASR。缺响应标为 not_measured，缺用量保持未知。

在线组件采集入口为 `experiments.diagnostics.utility_collect`，使用前核对其 `--help`、参考 manifest、实际模型和调用范围。日常验证只用真实 qwen3.7-flash；组件调用不计入至少 9 个不同计分任务的覆盖要求。
