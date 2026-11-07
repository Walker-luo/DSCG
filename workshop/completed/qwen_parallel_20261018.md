# Qwen3.7-Flash 接入与测试分组并发（2026-10-18）

按用户确认方案接入千问，并提供在线进程并发；不是阿里云异步Batch API，无Batch价格折扣。没有调用千问/DeepSeek服务，没有真实模型benchmark样本；离线fixture只验证接线、调度及原生缓存/评分流程。

## 交付行为

- 默认主模型、授权编译和审计模型为 `qwen3.7-flash`；既有显式配置/角色环境变量优先级保留。baseline、规划、授权与审计统一配置 `reasoning_effort="none"`；该设置写入模型公开身份。保留DeepSeek none适配。Dashboard两类模型列表新增千问，Local/Env仍走本地配置，选千问也不覆盖业务空间地址。
- 修正本地配置中的凭证字段：千问Key保留在dashscope共享段，DeepSeek原主模型Key保留在deepseek共享段；角色不再钉住另一服务的Key/endpoint。api_key_env仅接受变量名，错误不回显非法值。清除模板中的真实Key，保留其他用户模板改动和本地北京空间地址；敏感原模板及local原字节不进入归档、日志或报告。
- full/partial CLI新增 `--workers N`，Python API默认workers=1，cohort透传。按攻击×场景调度、clean每场景一组，实际并发不超过非空组数；screen仍顺序执行。任务注册前缀/full范围、DoS口径、原生GOAL预检、工具循环、评分和缓存接受规则不变。
- 父进程先检查全部配置/已有绑定，再在运行锁下提交完整计划和续跑快照；workers不是不可变身份，可在同源码续跑时调整。子进程只读审批绑定并只写本组目录；根清单、分攻击合并、失败索引和总报告由父进程生成。不扩展两份历史兼容映射，不迁移旧cache/cohort。
- 并发使用spawn，pipeline/环境/日志/Token tracker互相隔离；默认串行复用准备阶段构造的pipeline/attack对象，避免重复构造。Token沿用原来的场景/缓存/预检口径，execution/<ID>/execution.json和attack_manifest.execution另报实际wall_seconds，不能把API累计延迟相加当总耗时。失败组单列并继续其他组，不新加重试。
- 同一目录重复运行会被锁拒绝。中断停止调度、回收子进程并返回130；启动时暂缓SIGINT直到进程登记完成，子进程恢复原信号屏蔽集；接收结果/等待退出期间保留进程登记，防止漏回收。完整原生缓存保留，缺失/原生不完整任务仍按reuse原规则补跑。

命令及成本边界见 [partial指南](../../docs/partial_benchmark.md#并发运行)、[完整指南](../../docs/benchmark.md#进程并发提速)、[模型配置](../../docs/model_tool_configuration.md#24-最小可运行配置与角色复用)。本次源码和模型默认值变化要求新name、新screen名单；不以force-rerun绕过身份约束。

## 验证与审查

起点revision `fd4de3ec13412be0230e86653feb2b5b90014d38`，分支workshop；初始仅config/models.example.toml有用户修改。交付为本次代码/测试/文档改动，未提交、未变更分支或vendor环境。原字节归档见[originals](../archive/qwen_parallel_20261018/originals/)；敏感模板明确排除。详细命令、日志、哈希和完整校验见[任务产物](../artifacts/20261018_qwen_parallel/)。

| 验证 | 命令/结果 |
| --- | --- |
| Qwen请求及凭证 | `conda run -n ipi python -B -m unittest discover -s tests -p test_qwen_model.py -v`；初始3个预期断言失败，随后5项通过；native真实消息适配器配合Mock client验证请求参数，defended编译/审计LLM配置均检查 |
| 调度与中断 | `conda run -n ipi python -B -m unittest discover -s tests -p test_benchmark_execution.py -v`；7项通过，包含真实spawn重叠、崩溃、实际SIGINT及start/join边界回收 |
| 原生组执行 | `tests/test_parallel_runner.py` 的6项随两环境完整回归通过，覆盖真实子进程原生logger/cache、baseline/DSCG与clean/攻击的串并行指标/Token一致、full全部ID、cohort空场景/不补位和workers变化续跑、绑定冲突零派发 |
| AgentDojo完整回归 | `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v`；退出0，484项（483通过，1跳过），dojo_verified.log |
| AgentDyn完整回归 | 同上切换 `ipi-agentdyn`；退出0，488项（487通过，1跳过），dyn_verified.log |
| 前端 | `node --test tests/*.cjs`；退出0，41/41，node.log |
| CLI与私有配置 | `python -B workshop/artifacts/20261018_qwen_parallel/verify_interfaces.py`；退出0，双环境4个help、2份离线prefix清单导出、双角色/业务空间/DeepSeek保留检查；不创建远端请求 |
| 文档/保护检查 | `python -B workshop/artifacts/20261018_qwen_parallel/verify_delivery.py` 与 `git diff --check`；最终结果见validation.json |

执行过程保留RED和中间失败日志：早期回归暴露串行重复构造/无name重复命名及旧fixture绕过准备阶段的问题，已修复并保留任务/成本断言；新增cohort fixture的嵌套Mock/回调、注册顺序与串行wrapper问题也已修正。它们是离线fixture/工程问题，不是模型能力失败。

按executing-plans做一次fresh-context整体审查（gpt-6-astra）：1项Important是SIGINT时进程过早移出回收登记；新增测试在start/join两个阶段均RED失败后修复，原真实SIGINT测试继续保留。2项Minor为旧默认型号文案和重复占位注释，均已修正，无延期项。审查未发现其他Critical/Important；未判断真实服务兼容、加速或防御效果。

## 工程取舍与限制

- 在现有非main的workshop checkout实施，以保留用户模板修改及本地凭证；产物/进度账本使用仓库规定目录，不另建skill默认目录。未提交或推动远端。
- 串行使用准备好的对象，并发则在新进程重建；所有任务仍走同一原生循环。原来用未绑定stale summary模拟错误的测试改为先建立可核验绑定，否则新的全量预检查应直接拒绝执行。
- 模板敏感原字节不归档，不复制local文件；配置修正工具只输出布尔核验及公共信息。保留密钥的独立hash并非验收目标，避免扩散凭证。
- workers仅为执行策略；来源、后端、任务、模型、有效防御/审计/思考设置仍绑定，历史映射原字节不改。未知来源不因并发获准。
- 保留锁定原生适配器的温度序列化，未修改环境。流水线temperature=0配置不能单独保证服务确定性；Qwen关闭思考使用官方兼容参数none，实际服务鉴权/协议、远端修订、并发限流和速度须真实小规模运行验证。
- 并发不保证Token降低；失败/缓存/预检与API累计延迟沿原口径，未知不补零。失败组可能缺少完整成本，不能把该轮汇总当成完整新鲜成本对照。
- 工程测试数不是有效效用/安全分母；无真实benchmark收益或研究新颖性结论。E0 pending、I3 partial、I2 locked及关闭路线均不变。

下一步：在服务器同步代码，以新name运行小规模Qwen baseline/DSCG clean，再确认真实工具循环和审计协议后扩大workers及攻击测试。

最终保护检查：407份既有配置/历史文件哈希、14份非敏感原文归档、6681份用户结果文件集合/大小/mtime均保持；两份历史兼容映射原字节不变。核对264处有效本地链接，4处原有plan/report失效引用单列保留，未恢复已删除旧文档。凭证扫描通过。详见validation.json及归档change_manifest.json中的逐文件哈希。
