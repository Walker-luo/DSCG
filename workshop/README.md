# Workshop 优化材料

本目录统一保存 DSCG 的 workshop 框架优化方案、调研、阶段报告、诊断脚本和证据。当前运行框架仍是 V2 两层；三层是待验证候选，未实现。正式论文路线、Go/No-Go 与工程状态回报仍在 [`research/`](../../research/technical_route.md)。

| 材料 | 内容与状态 |
| --- | --- |
| [三层优化候选](./3_layer_opt.md) · [来源核验目录](./3_layer_sources_20261008.json) | 最新调研：来源标记、任务条件化局部净化、最终交付核验；候选尚未实现。 |
| [V2 后续优化报告](./framework_v2_followup_report.md) | 当前保留必要前置读取的审计补修；执行提示候选已撤回。 |
| [V2 实施记录](./framework_v2_report.md) | 2026-10-07 两层优化、探针和历史对照。 |
| [初轮优化报告](./framework_optimization_report.md) | 历史 P0 修复与消融；不代表当前默认全部启用。 |
| [初轮方案](./framework_optimization_20261007.md) · [结果复核](./framework_optimization_review_20261007.md) | 旧结果分析及优化建议，按日期保留。 |
| [简化约束](./framework_optimization_direction_20261007.md) · [V2 提案](./framework_optimization_v2_proposal_20261007.md) | 每层保持简单；提案是当时状态，以最新报告为准。 |
| [早期 workshop 报告](./workshop_optimization_report.md) · [工程计划](./2026-10-05-workshop-engineering-optimization.md) | 早期 harness/trace 工作；八例 I3 `no_go` 已被后续 `partial` 证据取代。 |
| [阶段证据与诊断脚本](./results/framework_optimization/) | 原 `examples/results/framework_optimization/` 的完整目录，历史数据和脚本内容保留。 |
| [迁移清单](./results/materials_migration_20261008/migration_manifest.json) | 旧位置、新位置、迁移前后 SHA-256、原版本与兼容路径。 |

原始 benchmark 结果仍在 [`results/`](../results/)，历史分析输入仍在 [`download/`](../download/)；通用实现、测试、runner、dashboard 保留原目录。正常 partial 命令继续从 `DSCG/` 执行，见[项目 README](../README.md)。

旧位置保留符号链接，供历史命令和哈希记录读取。仅修正了三份当前文档的相对链接/归属文字；这些文档修正前的完整字节保存在 `archive/original_documents/`，旧路径指向原版本，当前阅读使用上表入口。历史 evidence 的命令与哈希没有批量重写。历史诊断脚本可能绑定当时的代码或候选补丁，不应直接重跑并覆盖已有输出。

本次归档检查（已进入 `ipi`，在 `DSCG/` 执行）：

```bash
python workshop/verify_migration.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s workshop/results/framework_optimization/20261007_v2_followup \
  -p test_evidence_scoring.py -v
```

第一条核对归档哈希、兼容路径、文档链接和运行代码/研究路线；第二条核对搬迁后的离线证据评分工具，不调用模型，也不表示 benchmark 防御有效。
