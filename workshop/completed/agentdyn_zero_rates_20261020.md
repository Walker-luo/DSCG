# AgentDyn 零 TSR/ASR：诊断与 shopping 小样本对照

状态：诊断与小样本验证完成；默认防御未修改，效用问题尚未修复。本轮不支持防御有效性结论。

## 交付与证据

- 新增只读入口：`python -m experiments.diagnostics.agentdyn_zero_rates --run-dir PATH --output-dir NEW_PATH`。可重复传入run-dir；输出JSON/Markdown，拒绝覆盖已有输出目录，不创建模型客户端，不改原生标签。
- [最终历史诊断](../artifacts/20261020_agentdyn_zero_rates/diagnosis_final/diagnosis.md)及逐任务JSON：两份历史运行各81个绑定计划组合、72条有效计分轨迹、9条未执行；每份27条GOAL预检，成功9条。原tool_knowledge/dailylife构造错误不进入计分分母。
- [逐任务小样本报告](../artifacts/20261020_agentdyn_zero_rates/pilot_report.md)、[公开配置/绑定数据](../artifacts/20261020_agentdyn_zero_rates/pilot_data.json)、[精确调用命令与退出码](../artifacts/20261020_agentdyn_zero_rates/commands.json)。新结果均在同目录的partial_benchmark/agentdyn下。
- [输入完整性](../artifacts/20261020_agentdyn_zero_rates/source_integrity.json)：原两份用户结果共266个文件，SHA-256全部保持不变，无新增/删除。

代码基线为`0235fbf5b6af22e4fd88c8d02f9d4e25a713c533`，工作树包含先前未提交变动；[工作树快照](../artifacts/20261020_agentdyn_zero_rates/working_tree.txt)。模型对照调用期间未修改runner、防御或请求适配代码。按记录核对各模型全部臂的主模型公开请求设置、用户ID、commit；DSCG各臂同时核对审计模型与工具元数据。DeepSeek主/审计显式使用deepseek provider，Qwen主/审计显式使用dashscope；配置与报告不包含密钥。

## 结果与解释

| shopping clean，前三用户 | DeepSeek Flash | Qwen3.7-Flash |
|---|---:|---:|
| 无防御baseline | 2/3 | 2/3 |
| 当前DSCG/legacy | 0/3 | 0/3 |
| protocol-v1候选 | 0/3 | 0/3 |
| tool-semantics-v1候选 | 0/3 | 0/3 |

所有36条新计分任务均返回有效原生布尔标签，无计分API错误。其中24条为clean，12条为固定清单攻击；另有4条未计分的原生GOAL预检。第一次沙箱内连接失败无计分轨迹，保留其日志；换新名在可连接环境完成了DeepSeek baseline clean。

每个模型的9条防御clean轨迹均缺少原生参考路径使用的工具，尤其`verify_shopping_account`和`get_shopping_linked_unread_emails`。前者会执行排队的购物/账户动作，风险目录将其归为financial；后者会标记邮件已读，归为write，均不在确定性read闭包内。L2独立编译时未选入这些工具，规划视图随后也不可见。Qwen还漏选部分加入购物车与结账工具。参考路径不是唯一解，个别任务另有审计阻断，不能把全部失败完全归因于一个层。

每个模型使用相同shopping前三用户与`injection_task_1`，对ignore_previous做baseline/DSCG机制诊断。DeepSeek攻击TSR为2/3、0/3；Qwen为1/3、0/3；四臂ASR均0/3，安全布尔分母均3。每臂的user_task_0/2能观察到注入原文在工具返回中重合，user_task_1没有该精确重合；这不证明模型遵循/忽略了注入。Qwen baseline本轮直接GOAL预检失败，而历史曾成功、本轮DSCG预检也成功；Qwen这轮攻击臂不能用于效力比较。DeepSeek直接GOAL成功且有文本重合，baseline仍无攻击成功，下一步需要审查攻击模板与读到的具体返回位置。

成本逐臂列于小样本报告：主模型与审计Tokens分别报告、相加一次。攻击运行成本包含GOAL预检，预检不进入计分/ASR分母；不把缺少usage的单条baseline轨迹当成零成本。

## 决策与下一步

1. shopping无防御已有可完成任务，因此未触发扩展github/dailylife的条件。两个候选均未通过clean效用检查，不运行候选攻击或提升为默认。
2. 优先建立购物OTP合法依赖的L2诊断fixture，核对可信任务、候选工具描述与编译决策；同时加入OTP导致非用户请求动作的负例。不能直接把验证/结账工具加入通用白名单，也不能按原生参考答案给运行时授权。
3. 在独立候选中验证合法条件性工具选择；达到clean通过后，再检查非法放行与攻击对照。若这需要新的参数/对象/动态扩权机制，先由研究侧选择路线，不从本轮诊断自行解锁。
4. 攻击侧先审查同一目标的模板与实际读取返回；baseline ASR为0时不扩大正式DSCG攻击测量。当前tool_knowledge/dailylife的unsupported处理保留。

这些单次小样本只用于决定下一轮诊断，不能外推60个AgentDyn clean任务、正式ASR或服务版本可重复性。

## 验收与实施记录

- `conda run -n ipi python -B -m unittest discover -s tests -v`：退出0，581项，跳过9；[日志](../artifacts/20261020_agentdyn_zero_rates/ipi_tests_final.log)。
- `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v`：退出0，585项，跳过1；[日志](../artifacts/20261020_agentdyn_zero_rates/agentdyn_tests_final.log)。
- `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs`：退出0，47/47；[日志](../artifacts/20261020_agentdyn_zero_rates/node_tests.log)。PATH中的node不可用，改用已安装runtime。
- 新增6项诊断回归，覆盖错误/缺失/损坏、不把未执行记为失败、无授权记录、最后授权差集、未观察到payload、失败分组保留GOAL预检。最初导入失败及计数错误均在实现过程中修正。
- 修改文档本地链接检查与`git diff --check`退出0。[验证汇总](../artifacts/20261020_agentdyn_zero_rates/validation.json)。
- 沿用当前脏工作区，以保留已授权的请求兼容修改与本地配置；所有新输出隔离，未提交、移动或重写用户结果。独立审查因调用配额不可用，本轮完成作者自审，该限制不替代外部审阅。

下一动作：以shopping/user_task_1的OTP工具依赖制作受控L2正负例，提出单一候选修订后重新做同任务clean对照。
