# L3纯算法选择性审计工程报告

日期：2026-10-10。工程实现完成；真实校准/部署阈值和模型收益验收待完成。用户明确选择纯算法，原逻辑回归训练路线被替代。当前默认off，不附部署artifact。

## 改动与边界

[dscg/audit_router.py](../../dscg/audit_router.py)实现单个注册/授权/internal/idempotent/read/sink-none硬门控、8个明确完整性标记、固定字符三元组max评分、JSON版本/哈希/分母校验、按独立组校准及一次性进程内凭据。固定信号为任务—工具距离、参数新颖度、不可信词面支持增量和近期失败比例，无训练系数、embedding或生成模型。

[checker/Monitor](../../dscg/pipelines/defended.py)支持off/shadow/selective；开启路由后所有checker输出均认证交接，绑定任务、精确候选、完整动作历史/source-ID状态、policy/contract、catalog/schema/函数/依赖、上下文、artifact和运行配置。default off保留原路径；public/L2不计作新增节省。保留READ_ONLY_SOURCE_ALLOW有效读取deny例外、abstain/错误阻断与原执行ticket，无对象/数据权限扩展。

[数据准备](../../experiments/l3_router_dataset.py)读取显式独立标注JSONL，检查组/相关key/同包/标签/输入hash/完整性，输出数值rows与manifest；原任务/返回正文不重复输出。[校准入口](../../experiments/calibrate_l3_router.py)再核对实际行与manifest，按组any风险、CP上界和delta/K筛选冻结grid；不足输出null。数据与artifact均拒绝覆盖。独立标签、组独立和grid预注册需外部核查，程序不能从hash证明。

[partial runner](../../experiments/run_partial_benchmark.py)新增显式模式/artifact配置，缓存绑定模式、artifact和运行配置；原任务/攻击选择保持。scored trace成本账区分原public、L2拒绝、合格内部读、would/actual、已知/未知usage和参考轨迹潜在成本。真实总节省保持null直到匹配实验。网页专门CSA控件待接线，既有基础三层网页实现不在本任务修改范围。

完整规格与输入示意见 [当前L3文档](../L3_checker_opt.md)，[实施计划](./l3_algorithm_implementation_plan_20261010.md)与 [工件目录](../artifacts/20261010_l3_selective_impl/) 可复核。

## 验证

基准revision：`7d1e1ed27791cc87685bc512ba1b8fb5c1182d25`。开始时已有网页/文档工作树改动；本任务未提交、未修改用户结果/导出，精确状态/hash见before/evidence。新增27项测试（244项总数包含既有/用户网页工作），不把总测试数量当防御率。

| 命令 | exit | 结果/分母 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 最终244/244；日志regression_final.log |
| `node --test tests/test_history*.cjs tests/test_dashboard_ui.cjs` | 0 | 26/26，包含既有网页UI检查；没有新模型评测 |
| `conda run -n ipi python -m experiments.i3_p0_stress --output workshop/artifacts/20261010_l3_selective_impl/i3_final.json` | 1，预期partial | total/valid24，scope8，tool-boundary0，错误/无效/跳过0 |
| `conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output workshop/artifacts/20261010_l3_selective_impl/e0_final.json` | 0 | 合成6：valid1/tool_error1/infrastructure_error4；真实E0未通过 |
| `conda run -n ipi python workshop/artifacts/20261010_l3_selective_impl/microbenchmark.py` | 0 | CPU合成2种输入×300次，assess p95 0.142/1.290ms；1627-byte合成artifact；不是端到端耗时 |
| `python workshop/verify_migration.py --l3-current` | 0 | 本轮显式原文/hash/link链检查；不认证历史全迁移 |
| `git diff --check` | 0 | 差异格式通过 |

统计数值独立参考：60位Decimal组合数二项CDF，与非零k的CP反解4点最大差5.69e-16。合成artifact仅作单元/CPU诊断，不是64个真实独立安全样本，不用于部署。默认没有真实校准集/阈值；benchmark rollout=0，defender model calls=0，实际Token收益未知。

初轮测试失败均保留：未接入功能的RED、fixture中错误sink枚举/runner替身返回类型已纠正；微基准初轮脚本路径与缺失SciPy错误保留，最终改用无新增依赖的Decimal参考。旧结果不重写。历史迁移完整校验另有已有路径/快照限制，本轮只认证新修订。

## 独立审查

Critical0、Important5、Minor2。重要项均进入一次修正并通过最终全套测试；未再次派审查：

1. 删除公开路由字段降级allow：active所有checker结果使用宿主认证，不靠公开reason识别。对应降级/普通shadow伪造回归RED→GREEN。
2. 历史遗漏：绑定完整动作历史/source-ID状态；审查原复现确认，额外进程内省略该绑定的旧语义探针exit1/FAIL1，当前历史回归通过。探针不修改checkout。
3. 控制配置遗漏：绑定隔离/前置/重审/完成、提示版本、温度/推理与输入界限；配置区别回归RED→GREEN，默认CSA缓存身份同步。
4. 校准内部证据不一致：实际rows重算label/split/group与manifest，artifact严格检查组/动作/错误计数关系；两项回归RED→GREEN。
5. 完整性缺失当完整：共享固定8项boolean schema，缺失/未知字段拒绝；回归RED→GREEN。

保留小项：`router_total_latency_ms`目前只测assess，不含凭据/Monitor复核；异常中断的未消费凭据尚未在外层任务边界统一清理，正常消费/跨状态绑定有效。它们没有被描述为已修复。

未判定项均保持限制：off普通审计认证是既有实现；读取deny例外按任务范围保留；标签真实性、组独立/近重复和grid预注册靠外部证据；真实ASR/TSR/收益与selective轨迹尚无评测；用户既有网页工作不纳入本次算法变更。

## 状态与下一步

README、AGENTS、平台交接和workshop索引已同步；原文/路径/hash见 [归档修订](../archive/l3_selective_impl_20261010/revision_manifest.json)。本规格仍留顶层，是因为真实标签、部署阈值和端到端验收未完成；已完成工程阶段/计划放completed。

下一步：对真实internal-read成对样本独立标注并核对group关系，预先固定风险目标/grid，先shadow，再冻结selective与off做匹配试验。未证明收益时继续完整审计；不解锁I2，不重开闭合provenance/I1/I4/exactly-once路线。
