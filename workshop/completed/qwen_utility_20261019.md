# Qwen banking / Slack 效用诊断与候选工程报告

日期：2026-10-19。工程已实现，真实模型验收待授权；**默认仍为legacy / three-layer-v3.1**。没有付费请求、正式clean/攻击执行或TSR恢复结论。

## 实现及边界

1. 默认增加审计协议诊断。区分空响应、非法JSON、字段/类型错误、拒答、未完成、无choice、超时及模型异常；summary只计数，standard增加紧凑元数据，full压缩sidecar可保留失败content前2048字符及完整content的序列化哈希。SDK异常和拒答文本不进入诊断元数据。严格解析、失败关闭、原始标签/分母保留；错误decision为list时正确归类为schema错误，仍阻断。
2. `prompt_profile`提供legacy、protocol-v1、tool-semantics-v1、source-context-v1累计阶段。候选分别补全四字段输出契约、宿主工具schema/审核风险目录及多步骤任务提示、当前动作与合法来源事实区分。默认legacy提示与目录保持原样；未直接恢复已撤回候选。
3. 候选通过factory、full/partial/cohort及Dashboard API传递，名称/内容摘要进入配置、pipeline和路由身份；legacy不额外增加候选绑定字段，配置兼容规则不变。不同候选/legacy同名配置冲突拒绝，原manifest保留。baseline/NoChecker/NoSandbox拒绝候选。API提供的候选hash由宿主重算，不接受客户端冒充。
4. 12项人工编写正反例可离线导出真实audit packet；没有客户端创建或工具执行，标签只是后续配对诊断预期，不是模型判定或独立native oracle。没有参数/对象/数据授权机制、补授权、重试、免审或L1扩展。

L1继续等待独立模型对照证据，没有为未提出工具调用、被覆盖账单事实或日期歧义补规则。源码范围未进入I2或其他关闭路线；E0 pending、I3 partial24valid/8scope、I2 locked不变。

## 数据与归因限制

复核输入download/dscg-history-analysis-20261019T021115Z/，2334条导出utility/security标签与本地原始轨迹一致。两臂相同cohort，实际范围为travel/banking/slack三个场景、typical三攻击；不是clean，不能从汇总的比较警告直接推断不可配对，也不能据此称后端源码逐字节认证。

banking baseline305/432、DSCG189/432，原生ASR118/432→0/432；Slack223/315→80/315，ASR182/315→0/315。配对损失/收益137/21、144/1；其中baseline未攻击成功的损失85、60。banking审计schema错误181/776、Slack446/1566；77/137、109/144配对损失出现过该错误。共现不证明全部可恢复，也不代表模型一般安全性能。

L2存在网页发布/频道发送混淆、复合动作漏项。L3存在正常事实来源链接被拒，且有协议错误和错误参数叠加。路由shadow未实际绕审；无正文截断证据，不以扩大预算/阈值优化解释本批结果。详细使用和后续37/97clean、冻结cohort三攻击命令在[指南](../../docs/qwen_utility.md)。

## 验证记录

基点e9b494e6c13fcc0d0fee9885f5eadbdc58147e85，workshop分支；开始工作树干净，交付代码未提交。本轮没有切换分支、推送、安装环境或修改本地凭据。与正式结果分离的日志根为`workshop/artifacts/20261019_qwen_utility/`。

| 精确命令（DSCG目录） | 日志 | 退出码与含义 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -v > workshop/artifacts/20261019_qwen_utility/baseline_ipi.log 2>&1` | baseline_ipi.log | 0；496项，1跳过 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/protocol_red.log 2>&1` | protocol_red.log | 1；新增7项观察到1失败/15子用例错误，诊断/候选接口尚不存在 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/protocol_green.log 2>&1` | protocol_green.log | 0；7项 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/bindings_red.log 2>&1` | bindings_red.log | 1；预检/真实factory身份及网页候选校验缺失 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/bindings_green.log 2>&1` | bindings_green.log | 0；10项 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/edge_red.log 2>&1` | edge_red.log | 1；错误decision=list未正确归类 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/edges_green.log 2>&1` | edges_green.log | 1；新增无效metadata测试暴露None未处理，随后修正为unknown/critical |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_utility.py -v > workshop/artifacts/20261019_qwen_utility/edges_green_fixed.log 2>&1` | edges_green_fixed.log | 0；15项 |
| `conda run -n ipi python -B -m unittest discover -s tests -v > workshop/artifacts/20261019_qwen_utility/final_ipi.log 2>&1` | final_ipi.log | 0；511项，510通过/1跳过 |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v > workshop/artifacts/20261019_qwen_utility/final_agentdyn.log 2>&1` | final_agentdyn.log | 0；515项，514通过/1跳过 |
| `node --test tests/*.cjs > workshop/artifacts/20261019_qwen_utility/final_node.log 2>&1` | final_node.log | 0；45/45 |
| `conda run -n ipi python -B -m experiments.diagnostics.utility_packets --output workshop/artifacts/20261019_qwen_utility/source_packets.json` | source_packets.json | 0；12人工预期包，0模型/0执行工具 |

两次阶段完整回归日志stages_ipi.log/stages_agentdyn.log保留，分别506/510项、各1跳过；后续加入了5项测试。包构造时已存在的TaskResults/FunctionCall重建警告同样出现在基线日志，本轮没有把它误记为新增测试失败或修复相关代码。

新15项测试包含多类型协议错误仍阻断、无自动重试、摘要无原文、full预览有界与hash、无choice/服务异常不泄露文本、不同候选预检和实际factory一致、CLI/full/partial/cohort转发、真实runner离线绑定/拒绝同名异配置、宿主目录身份、无效metadata与未知工具、来源事实原样和Monitor拒绝、客户端hash不能冒充。模型传输/评分mock的成功不算TSR/ASR。

## 交付与后续

独立只读复核未发现Critical/Important问题，新增测试独立复跑15/15通过（reviewer_qwen_tests_01.log）。Minor：候选提示要求violations每项不超96字符，原解析器接受长字符串再规范化至96字符。选择保留旧解析行为，不新增默认拒绝，已在指南明确；reason_code仍严格校验。复核未修改源文件或调用模型API。

代码/日志/fixture哈希及保护校验见[清单](./qwen_utility_20261019_manifest.json)。正式results/download和本地local配置的保护清单在最终回归前建立，核对9930份文件大小/mtime；不是任务开始时的全量字节快照。输入导出另有SHA256，原始标签重新核对；不宣称对历史全部文件完成哈希认证。

交付验证命令：`python -B workshop/artifacts/20261019_qwen_utility/verify_delivery.py workshop/artifacts/20261019_qwen_utility/validation_final.json`（exit0）；`git diff --check`（exit0）。清单记录实际代码文件/日志/输入hash；代码未提交，Git基点不等于这些变更已经形成commit。研究交接仅追加工程证据，不改变technical_route或论文闸门。

下一步：先授权有限模型配对，分别验证协议阶段、L2目录阶段和来源语义阶段，再选择是否进入37/97clean及同cohort攻击；有新增误放或合法动作新损失不替换默认，不保证5pp目标。不实施L1或模型能力特例。
