# banking／Slack 分阶段诊断工程交付（2026-10-21）

**工程准备完成；真实诊断、候选选择和TSR恢复尚未验证。** 用户批准先验证现有短提示和累积候选，不修改输出协议或追加默认机制。本轮未创建真实模型客户端、未执行工具、未进行付费调用，也没有替换默认防御。

## 已交付

- 新增离线入口 `python -m experiments.diagnostics.utility_stages`，支持export、compare及显式traces检查。复用当前审计输入构建、四字段解析和真实授权编译器，本地捕获/重放通过独立无网络对象实现。原utility_packets的12例入口和默认行为保持。
- audit固定24例：原12例＋banking12例（6合法、4拒绝、2证据不足），legacy与protocol-v1各重复2次，共96份未来请求模板。
- authorization固定12例：6合法任务及6对应禁令/无关动作，protocol-v1与tool-semantics-v1各重复2次，共48份模板。覆盖频道/私信/网页修改、退款、修改已有定期付款及复合任务。标签来自明确用户要求和人工定义的宿主能力，不取原生参考路径。
- source使用同24个审计输入，tool-semantics-v1与source-context-v1共96份模板，仅在确认残留来源语义误拒后才考虑模型诊断。导出模板不消耗预算，也不代表条件已经通过。
- 比较器拒绝被改写/过期的输入、标签、提示和请求身份，拒绝重复/未知响应及非法成本；响应仅接受公开模型字段。模型身份和Token是收集方声明，不认证服务器实际配置/计费。无在线收集器，本轮没有模型执行开关。
- 每个profile分别报告计划/已读响应、协议错误、执行错误、合法动作语义拒绝、漏工具、额外放行及已知/完整Token。缺失保持未知，原始content不进入默认结果。按case＋重复逐项检查新增不安全放行，不能用总数抵消。
- 仅在完整响应、无执行错误、目标错误严格减少、协议错误不增加且无新增不安全放行时，通过组件诊断门槛；授权/来源还要求合法样例的配对响应有效。解析失败保持未知，不能当作“漏工具或误拒已经消失”。selected_default始终null，不自动改默认。
- traces仅读取显式文件：支持精简summary及详细ledger，区分原始审计deny与实际AUDIT_DENY，P/D/无调用可以重叠；缺少证据保持未知，不指定唯一根因、不重算原生标签或全运行分母。

## 设计裁定与限制

授权阶段原目录使用protocol-v1作为控制：它与legacy的L2相同，且与tool-semantics-v1的L3相同。当前profile是累计配置，无法任意拼接L2/L3；没有新增运行时分拆接口。如果短版legacy获选而L2语义候选通过，整个累计候选仍须验证，不能把端到端变化全部归因于L2。

所有新增样例是人工期望和合成宿主目录，不是原生AgentDojo工具执行、独立安全标签或正式TSR/ASR样本。诊断门槛不是安全证明，需真实clean/攻击和独立终态检查后才能讨论默认晋升。现场的banking读取成功后停止、Slack合法链接被拒等类别保留待核查；没有根据任务ID、人物、金额或标准答案加入运行规则。

## 验证

基点 `99d2117647d0e3b0ed8b5ad038891df7eb790013`，workshop分支，任务开始工作树干净；本轮未提交。证据在 `workshop/artifacts/20261021_utility_stages/`，manifest记录源码/日志SHA256和完整命令。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_stages/run_offline_tests.py --pattern test_utility_stages.py` | 1→0 | 初始缺模块RED；最终10/10；review_red/green保留“移动解析失败造成假通过”的两项反例 |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_stages/run_offline_tests.py` | 0 | 最终611项：602通过、9跳过；final_ipi.log |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261021_utility_stages/run_offline_tests.py` | 0 | 最终615项：614通过、1跳过；final_agentdyn.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 47/47；node.log |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_stages/prepare_evidence.py` | 0 | 三组输入和未测量报告、两条原始轨迹的重叠信号；prepare.log |
| `conda run -n ipi python -B workshop/artifacts/20261021_utility_stages/verify_delivery.py` | 0 | 原始结果/导出SHA256保护、运行源码与原12例不变、链接检查；validation.json |
| `git diff --check` | 0 | 无空白错误 |

模型相关测试在导入及运行期阻断socket连接，最终network_attempts=0；真实模型请求/工具执行/效用或安全样本均0。独立只读复核发现并修复“解析失败移到合法样例却减少语义错误”的假通过问题；补齐授权和来源两项RED反例后10项定向通过，复核无剩余Important/Critical问题。三组真实诊断状态均not_measured，未从fixture回放生成真实效果结论。

## 交接与下一步

`plan.md`分别标记工程完成与模型待测，保留TSR目标和AgentDyn独立事项；当前指南、AGENTS和workshop索引同步。用法、响应格式及限制见[诊断指南](../../docs/qwen_utility.md)。

下一步需单独授权模型预算：先96次审计，再48次授权，只有确认残留来源语义误拒才追加96次；不执行工具。然后以新name固定shadow/0.70，比较同轮baseline、短版legacy与已选候选的全部37项banking/Slack clean；改善后再做同cohort三攻击、97项clean，最后单独检查selective收益。约5pp是目标，非保证。E0 pending、I3 partial24valid/8scope、I2 locked不变。
