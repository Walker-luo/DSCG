# 结果目录精简与运行级L3汇总交付（2026-10-19）

已完成用户批准的展示与统计改造；无模型调用，没有改变防御、阈值、评分、配置绑定或缓存身份。原始证据保持原位。本报告不说明TSR/ASR或安全收益。

## 交付

- CLI full/partial/cohort取消场景report.txt、攻击/根all_report.txt及攻击错误TXT；保留CSV、原生JSON/full附件、summary、绑定/cohort/执行/快照。
- 根summary.md每攻击/场景一行，最多10个失败链接；failure_cases.jsonl完整保留。CLI中断可生成部分报告；Dashboard正常完成后同样生成根摘要与共享L3报告，历史/CSV/下载API不变。
- 新共享routing_reports只用Python标准库、从存储元数据获得声明范围，不加载活动后端/模型；精确读取计分轨迹，排除GOAL预检及旧快照。按实际模式、配置和候选分别列出分数/阈值、原因、延迟和判断交叉。
- 未校准及缺失/无效输入时整体shadow有效节省未知；已知部分小计单列。公开读取与新增选择性免审分开；selective实际Token节省始终未知。交叉判断不是安全真值，审计Token不能再加进运行总量。
- 离线工具默认只新增两份L3报告；默认拒绝覆盖，refresh只替换schema/标记匹配的本工具文件。目录锁及现有CLI锁校验、越界符号链接拒绝、每文件原子替换均有回归。

用户指南：[docs/result_files.md](../../docs/result_files.md)。[实施账本](./result_reports_20261019_plan.md)。README、测试/平台/工具索引与AGENTS同步。

## 指定旧目录回填

`results/benchmarks/agentdojo/qwen3.7-flash_DSCG`只新增l3_router_summary.md/json。任务开始时建立1279文件SHA256清单；回填后逐文件核对，原文件0变化，仅新增2文件，重复默认调用退出1且两份新文件也未改变。

| 项目 | 数量 |
| --- | ---: |
| 计划/读取计分轨迹 | 1167/1167 |
| 含事件/明确无候选 | 1135/32 |
| 候选批次/原公开免审 | 4309/1826 |
| 路由适用/缺校准 | 429/429 |
| 语义审计调用 | 2483 |
| 已记录审计Token | 5035179 |
| 费用未知批次 | 1 |

无缺失/损坏/身份冲突/越界记录。该运行shadow未校准，不能将模拟免审0解释为零收益，报告的有效模拟节省为未知。旧summary.md及所有原始JSON、TXT、CSV、cohort/manifest/执行记录均未覆盖。这里只改善查阅与重复输出；原任务JSON占大多数，不承诺大幅减小磁盘占用。

## 验证和可复核命令

基点`e8546dd2214717868b26ba3a5b0c7c287bac5980`，开始工作树干净；交付为当前未提交改动，无自动commit。日志统一在`workshop/artifacts/20261019_result_reports/`。两环境Python均3.10.21，Node v22.23.1。

| 命令（DSCG目录执行） | 退出码 | 结果/日志 |
| --- | --- | --- |
| conda run -n ipi python -B -m unittest discover -s tests -v | 0 | 531项，530通过/1按后端跳过；delivery_ipi.log |
| conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v | 0 | 535项，534通过/1按后端跳过；delivery_agentdyn.log |
| node --test tests/*.cjs | 0 | 45/45；delivery_node.log |
| python -S -m experiments.diagnostics.summarize_results --run-dir results/benchmarks/agentdojo/qwen3.7-flash_DSCG | 0 | backfill.log；不加载site-packages/活动后端 |
| python -B workshop/artifacts/20261019_result_reports/verify_delivery.py | 0 | validation.json；保护1279文件、两个新增文件及目标计数 |
| git diff --check | 0 | 无空白错误 |

新路由测试19项，覆盖多配置、加权计数/分位数、off/baseline、shadow/selective、缺失校准与成本、空候选、损坏/缺失/冲突元数据、缺少范围、跨目录符号链接、锁与刷新所有权、Dashboard真实原生路径适配。已有runner回归覆盖clean/攻击、full/partial/cohort、错误/中断/续跑、缓存/sidecar及历史/导出。新增36失败案例回归核对JSONL36条、根摘要仅10入口。专项RED/GREEN过程保留日志。根摘要另外保留实际模式/候选/免审和未知节省的一行结论，root_conclusion_red/green.log记录该接线回归；最终两环境及Node检查在此之后重跑。

独立只读复核发现两项重要完整性问题：未知范围被当成0调用、缺失轨迹时shadow已知小计被当成完整节省。已新增RED→GREEN测试并修复；保留review_routing_tests_ipi.log和review_completeness_red/green.log。完整回归在修复后运行。

## 限制与下一步

目录锁是协作式，不能仅凭文件锁识别另一Dashboard进程所有活动；离线汇总前应停止运行。每文件原子替换并非两个文件事务，极端中断后可refresh重建。未知范围不能给出完整计划分母，报告status/issue明确标识；部分计数仅表示已记录事件。

本轮模型调用0、真实rollout0、效用/安全新样本0。1167是旧计分轨迹核对分母，4309是路由事件分母，不是独立安全样本。研究闸门保持E0 pending、I3 partial24valid/8scope、I2 locked。下一步由用户新运行检查根级报告；真实校准、重复clean/攻击和独立终态核查仍另行验收。
