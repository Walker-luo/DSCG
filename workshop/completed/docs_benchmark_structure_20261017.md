# 测试文档结构整理与CLI路由默认值

日期：2026-10-17。基准revision：`8c591e27390c77614dbf4d1ff46f98428c8b5e30`。开始时已有两项docs删除，均保留；本次工作树改动尚未提交。

## 交付

- [benchmark指南](../../docs/benchmark.md)承接完整任务测量，集中维护公共攻击表、参数、结果字段和指标口径；历史成绩只链接现存报告。
- [partial指南](../../docs/partial_benchmark.md)单独说明默认3×3、baseline/DSCG、clean、场景选择、cohort前缀交集、shadow及续跑。
- [evaluation索引](../../docs/evaluation.md)只介绍测试指南、关键脚本、配置和结果文件，不介绍框架/平台或阶段成绩。
- 旧完整指南退出docs且不保留兼容页；项目/实验/当前文档/workshop可读报告的链接和锚点同步。被删除的旧V2别名/I3报告不恢复；当前引用改到仍存在的研究交接。

原文和哈希见 [本次归档](../archive/docs_benchmark_structure_20261017/README.md)与[映射](../archive/docs_benchmark_structure_20261017/relocation_manifest.json)。已归档的旧文件、历史清单和原始结果不改写；可读报告的本次改动只涉及链接。L3当前计划文档额外明确CLI/API默认值区别，校准/验收要求不变。

## 后续授权的运行调整

用户并行将CLI路由默认改为shadow，发现其与baseline校验冲突后，明确选择“采用shadow默认，同步调整默认行为与baseline兼容逻辑、文档及验证”。据此扩展原文档计划：

- full/partial DSCG CLI未显式指定模式时为shadow；baseline/NoChecker为off。
- 显式shadow/selective与baseline/NoChecker仍拒绝，不悄悄改写用户指定模式。
- Python API/factory及网页配置仍默认off，DSCG显式off保留原L3；shadow仅观察，不新增免审。
- 源码/模式身份变化的攻击测量用新name；直接GOAL预检只通过明确字节绑定兼容旧来源，旧manifest、attempt和cohort不覆盖。

dscg防御实现与任务选择代码未改动。新旧默认不作为费用或安全收益证据。

## 验证

工程产物根：`workshop/artifacts/20261017_docs_benchmark_structure/`。before.json记录初始工作树/文件身份，parallel_router_default.py保存并行中间版本，validation.json与link_validation.json保存精确命令、退出码、哈希和引用检查。

- 路由默认新回归先RED：6个baseline/NoChecker子场景触发原参数冲突；修复后4项契约测试全部通过，覆盖两个CLI入口、显式模式和不兼容拒绝。
- `conda run -n ipi python -B -m unittest discover -s tests -v`：exit0，389/389。未调用真实模型、未运行真实benchmark。
- 两测量入口及screen的help：exit0。参数与任务/攻击规模均按当前代码及注册表离线核对；模型命令仅解析验证，不执行。
- 当前新导航、更新报告的链接/锚点、原文与244个既有归档文件哈希检查；无新增失效引用。旧plan/report目标已有7处缺失引用（重复引用计次）保留并单列，未重建用户材料。
- `git diff --check`：exit0。独立只读审阅无发现。既有历史迁移校验器不用于认证本次新文档，也不改写其快照。

新增真实模型请求0、真实benchmark样本0；E0 pending、I3 partial、I2 locked及closed路线不变。下一步：按evaluation选择两份运行指南，用新name执行用户所需测量；off对照显式传模式，避免依赖旧CLI默认值。
