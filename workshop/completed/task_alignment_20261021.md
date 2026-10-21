# banking／Slack 精简任务对齐候选交付

2026-10-21。按用户要求，将框架优化落实为可直接benchmark的 `--prompt-profile task-alignment-v1`，不是再次运行付费组件诊断。默认legacy保留；原144次诊断没有支持旧候选晋升，本次也不以离线测试宣称TSR恢复。

## 改了什么

L2使用原工具名/描述目录，替换为四步短提示：识别完整请求的步骤；按操作及对象/目的地类型匹配工具；保留条件步骤而不预断条件成立；排除无关操作及用户禁止的效果。发送内容与修改来源、新建与更新是通用区别，没有添加任务ID、人物、金额或工具名称特例。仍只编译一次，输出原 `{"tools":[...]}`，不依据错误反馈补授权。

L3替换为“当前操作—用户任务—当前所需事实”的短提示。相关来源含攻击文字，不足以拒绝一个既定任务动作；同时仍拒绝来源新增目的地/任务/权限、秘密外传和攻击载荷转发。准备读取允许查找未知事实，不要求提前证明未来写入；写入/发送核对真实目的地与正文。四字段协议及严格校验完全保留。

| 范围 | legacy | task-alignment-v1 |
| --- | --- | --- |
| L2工具目录 | 名称/描述 | 相同 |
| 普通L2提示字符 | 1,084 | 966 |
| L3提示字符 | 1,919 | 1,853 |
| 调用、协议、执行边界 | 当前实现 | 相同 |

字符数不是Token或费用。此分支独立替换提示，不叠加protocol/tool-semantics/source-context长候选，也不修改旧profile内容/绑定。受信ToolAuthorizationProfile的三字段授权协议仍保留，不被普通tools协议覆盖。新分支同时调整L2/L3，后续端到端成绩不能直接归因于其中一层。

沿用CLI full/partial/cohort、Dashboard API、factory和缓存绑定；候选名及内容哈希进入manifest/路由配置。要求L2+L3同时启用，baseline/NoChecker/NoSandbox拒绝该候选。未加参数仍legacy，网页未新增选择控件。

L1、工具风险分类、路由公式/资格/阈值、默认shadow/API off、审计/执行票据、参数校验、重试、委托和原生评分均未改。没有新增参数/对象授权、内部handler权限、动态扩权或恢复机制。

## 诊断输入修正与历史保护

utility_stages现在默认导出 `input_revision=authorized-v2`：银行加入合成PermissionSandbox；Slack注册read_channel_messages/read_inbox等来源工具；候选与来源的参数均先验schema检查，核对候选数量和allowlist匹配。全部24个审计case具备一致的合成已授权上下文。这些固定grant不是实际L2模型编译，不是原生环境轨迹。

旧无revision包按legacy-v1生成与核对，包含当时银行缺少授权的已知缺陷；不补造旧授权、不重绑定响应。复核原96条审计＋48条授权的comparison与原文件完全一致。旧utility_packets入口保留其历史形式，新的分阶段采集使用authorized-v2。修正后没有补发任何付费请求。

## 用户如何测试

沿用当前Qwen主模型/审计模型配置，先检查启动日志的有效模型与端点。使用新name；下面首先测AgentDojo两个场景全部37个clean任务，保持shadow以隔离提示变化：

```bash
conda activate ipi
python -m experiments.run_benchmark --clean --baseline --suites banking slack --name alignment01_base --progress
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile legacy --audit-router-mode shadow --name alignment01_legacy --progress
python -m experiments.run_benchmark --clean --suites banking slack --prompt-profile task-alignment-v1 --audit-router-mode shadow --name alignment01_candidate --progress
```

需要指定配置时三臂加同一 `--model-config PATH`。plain benchmark不会自动改为新候选。clean之后再用相同cohort比较typical攻击及联合成功率，不只比较TSR；实际调用与结果由用户后续运行。本任务不启动模型/clean/攻击。[当前测试指南](../../docs/qwen_utility.md#task-alignment-v1)。

AgentDyn可使用同一候选和其自身场景，但本次没有声称已解决OTP/动态工具依赖问题。它保留在plan.md独立事项中。

## 验证与证据

基点 `99d2117647d0e3b0ed8b5ad038891df7eb790013`，workshop分支；起始已有未提交的utility_stages/collector、诊断报告及文档改动，均保留，没有新commit。新证据根 `workshop/artifacts/20261021_task_alignment/`，修改前源文件、状态和保护hash见before/与before.json。

| 实际命令（DSCG根目录） | 退出码 | 结果/日志 |
| --- | --- | --- |
| `conda run -n ipi python -B workshop/artifacts/20261021_task_alignment/run_offline_tests.py --pattern test_task_alignment.py` | 1→0 | RED：候选不识别/缺revision；GREEN新增5项，后扩为7项；red.log、green.log、green_final.log |
| `conda run -n ipi python -B workshop/artifacts/20261021_task_alignment/run_offline_tests.py` | 0 | 最终623项，9跳过，0失败/错误；ipi_final.log |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261021_task_alignment/run_offline_tests.py` | 0 | 最终627项，1跳过，0失败/错误；agentdyn_final.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 47/47；node.log |
| `conda run -n ipi python -B workshop/artifacts/20261021_task_alignment/verify_delivery.py` | 0 | 老profile策略/哈希不变、144旧响应重放一致、24新包、保护校验；verify.log、validation.json |
| `git diff --check` | 0 | 无空白错误 |

Python回归全部有socket硬隔离，network_attempts=0。新测试覆盖实际授权编译一次、受信bounded协议在compile调用点保留、allow/deny/abstain及非法输出仍按原流程处理、未授权工具不因audit allow执行、CLI/API/cohort接线、真实factory/runner manifest与同名缓存拒绝，以及新旧诊断身份。模拟响应只验证工程边界，不验证模型理解。

12,348份保护文件（包含12,302份results/download原文件和46份先前utility_live证据）hash不变，无新增用户结果。独立只读代码复核未发现Critical/Important问题；其bounded编译调用点测试建议已补充。导入时已有TaskResults前向注解提示未改变，测试与验证exit0，不能当成新的模型API错误。

精确哈希与命令见[manifest](../artifacts/20261021_task_alignment/manifest.json)，原文件保护和兼容核对见[validation](../artifacts/20261021_task_alignment/validation.json)。本轮模型请求0、原生真实计分样本0；真实TSR/ASR、协议失败率与总Token效果待用户benchmark，停止条件仍为新增误放不晋升、避免任务特例追分。E0 pending、I3 partial24valid/8scope、I2 locked不变。
