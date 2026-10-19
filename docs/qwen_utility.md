# Qwen banking／Slack 效用诊断与分阶段候选

当前默认仍为 `three-layer-v3.1`、`prompt_profile=legacy`。新增协议诊断默认生效；改变模型提示和L2目录的候选必须显式选择。工程接线与离线测试不能证明TSR恢复。2026-10-16已撤回的准备读取候选没有恢复。

## 本次数据说明

输入：`download/dscg-history-analysis-20261019T021115Z/`及对应原始结果。2334条标签与本地原始轨迹一致。两臂使用同一主模型配置和冻结cohort，包含travel、banking、slack与三种typical攻击；这是**攻击测量，不是clean**，也不是全部四场景的攻击全量。

| 场景 | baseline TSR | DSCG TSR | baseline ASR | DSCG ASR |
| --- | ---: | ---: | ---: | ---: |
| banking | 305/432 | 189/432 | 118/432 | 0/432 |
| Slack | 223/315 | 80/315 | 182/315 | 0/315 |

banking配对损失137、收益21，Slack损失144、收益1；损失中baseline未攻击成功的分别为85、60。不能把全部下降视为必要拦截，也不能把全部下降判成误伤。baseline可能同时任务成功和攻击成功，需另报联合结果。

主要发现：banking审计协议错误181/776，Slack446/1566；配对损失中分别77/137、109/144出现过协议错误，这是共现而非可恢复任务数。L2有网页发布/频道发送混淆和复合请求漏工具；L3有合法来源链接误拒。路由为shadow，没有按阈值实际免审；两场景没有审计正文截断，先扩大预算或调阈值缺少依据。无工具提议、事实被攻击覆盖和日期歧义保留为单独失败类型。

## 选择候选

| `--prompt-profile` / Python `prompt_profile` | L3 | L2 |
| --- | --- | --- |
| `legacy`（默认） | 原语义提示 | 原工具名/描述目录 |
| `protocol-v1` | 增加完整四字段输出约束及合法示例 | 同legacy |
| `tool-semantics-v1` | 同protocol-v1 | 宿主参数schema和审核后的effect/source/sink；区分作用对象，覆盖明确步骤 |
| `source-context-v1` | 在上一阶段上澄清当前操作、任务关联和当前所需证据；相关事实不授予新任务 | 同tool-semantics-v1 |

阶段累积，便于一次只比较一项变化。各候选适用于两个后端，名称不代表只支持Qwen。主模型、安全模型、L1、8192字符预算、原免审、Monitor/票据、委托、重试和完成提示保持原配置；不新增调用、补授权或参数级强制约束。候选要求L2和L3同时启用，baseline/NoChecker/NoSandbox拒绝候选。用户禁令、顺序与条件仍适用。

候选的run manifest、cohort测量配置、pipeline名称和路由配置绑定`prompt_profile`及`prompt_profile_sha256`，L2契约同时绑定实际目录和策略。不可同名混用legacy、其他候选缓存或旧校准artifact。legacy不新增候选绑定字段，保留原配置续跑语义；原始结果不迁移、不改写。使用新的run名。

网页API可传入`prompt_profile`，有效配置和文本报告会记录；页面没有新选择控件，普通网页操作仍为legacy。Python调用`make_defended_pipeline(prompt_profile=...)`与CLI一致。不是models.local.toml参数，不从工具反馈读取。

## 协议诊断与日志

真实审计的`protocol_diagnostics`包含：

- `failure_type`：成功为null；错误细分为EMPTY_RESPONSE、INVALID_JSON、FIELDS_MISMATCH、INVALID_DECISION、INVALID_VIOLATIONS、INVALID_CONFIDENCE、INVALID_REASON_CODE、NO_CHOICES、MODEL_REFUSAL、INCOMPLETE_RESPONSE、TIMEOUT、MODEL_ERROR、POLICY_CONFIGURATION。
- `finish_reason`：受限的服务结束原因或unknown；`refusal_present`只存布尔值，不存拒答文本。
- `field_validation`：passed、failed、not_checked。空响应、非JSON及传输/提前结束错误尚未完成字段检查。

summary任务JSON仅追加`dscg_audit_summary.protocol_failure_counts`、`finish_reason_counts`、`field_validation_counts`、`refusal_count`；standard另保留逐次紧凑诊断。历史缺字段表示未记录，不能补推具体原因。

`--trace-level full`在压缩sidecar的`audit_protocol_response`事件中保存失败响应前2048字符、截断标记及完整content的序列化哈希；不是整个HTTP响应。预览可能含基准原文，仅用于受控诊断。普通摘要/standard不存预览；不会保存SDK对象、请求凭据或API异常文本。

四字段协议和严格解析保留：不从Markdown提取JSON、不转换字符串置信度、不猜字段、不默认放行、不新增重试。协议错误仍按现有失败关闭路径阻断。协议失败是额外诊断维度，不改变原生utility/security/error标签、不剔除这些任务来提高TSR。

兼容细节：`violations`沿用既有“最多32个非空字符串、记录时规范化至96字符”的行为；候选提示要求模型每项不超过96字符，但不会仅因字符串更长而新增拒绝。`reason_code`仍严格检查96字符及字符集。这一区别保留旧解析语义，避免将格式说明当作已经新增的校验。

## 离线包与后续模型实验

以下只导出12个人工编写的诊断输入，**0次模型请求、0次工具执行**。期望标签用于审计动作关联性，不是native任务oracle，也不是模型预测：

```bash
python -m experiments.diagnostics.utility_packets --profile source-context-v1 \
  --output workshop/artifacts/20261019_qwen_utility/manual_source_packets_01.json
```

输出限定到workshop/artifacts/下新JSON，拒绝覆盖。可另导出legacy/protocol-v1/tool-semantics-v1，保持相同案例与输入事实，仅比较系统提示。覆盖相关来源链接、用户明确第二步、引用事实执行既定动作、恶意链接、换收件人、警告转发、秘密外传、禁令和缺少事实。工具权限通过与审计语义判断需分别验证。

本轮不调用付费模型。获得后续模型诊断授权后，先冻结独立正反例，在相同模型设置下逐阶段比较，记录协议错误、允许/拒绝变化及Token；不得只保留改善案例。未授权前只使用上述离线输入包。

随后由测试者在`ipi`环境运行同轮对照。以下命令会调用真实模型，不属于本轮离线验收；`qwen_u01`应替换为未使用的新批次名：

```bash
# 先比较两个问题场景的全部37个clean任务
python -m experiments.run_benchmark --clean --baseline --suites banking slack --name qwen_u01_bs_base
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile legacy --name qwen_u01_bs_legacy
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile protocol-v1 --name qwen_u01_bs_protocol
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile tool-semantics-v1 --name qwen_u01_bs_tools
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile source-context-v1 --name qwen_u01_bs_source

# 冻结通过阶段检查的候选后，再比较全97项clean（这里示例为tool-semantics-v1）
python -m experiments.run_benchmark --clean --baseline --name qwen_u01_all_base
python -m experiments.run_benchmark --clean --prompt-profile legacy --name qwen_u01_all_legacy
python -m experiments.run_benchmark --clean --prompt-profile tool-semantics-v1 --name qwen_u01_all_candidate

# 三臂使用同一份实际冻结cohort路径；不要重建或手改旧cohort
python -m experiments.run_benchmark --cohort /absolute/path/to/cohort.json --baseline --attack typical --name qwen_u01_attack_base
python -m experiments.run_benchmark --cohort /absolute/path/to/cohort.json --prompt-profile legacy --attack typical --name qwen_u01_attack_legacy
python -m experiments.run_benchmark --cohort /absolute/path/to/cohort.json --prompt-profile tool-semantics-v1 --attack typical --name qwen_u01_attack_candidate
```

正式输出沿用results/benchmarks/agentdojo/运行目录；agent自测必须额外指定workshop/artifacts/下新results-dir。续跑保留原候选及全部配置，加`--reuse`，不通过force-rerun绕过绑定。两套环境同命令自动切换；AgentDyn的全量clean是60项，没有banking/slack，不跨后端比较分母。

报告原生TSR/ASR、任务成功且攻击失败的联合结果、配对得失、有效/错误分母、协议错误、全部Token和模型调用数。目标是观察全量clean相对同轮baseline的差距能否接近5pp，不预先保证。若新增误放、合法动作出现新损失或只能依赖特例追分，不替换默认；L1继续等待独立对照证据。
