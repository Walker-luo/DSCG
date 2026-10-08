# Workshop 优化材料

所有优化计划、调研和工程报告统一在本目录。当前运行框架仍为 **V2 两层 + 保留的必要前置读取审计补修**；第三层方案尚未实现。正式论文路线、创新判断和实现回报仍在 [research/](../../research/technical_route.md)。

| 材料 | 内容与状态 |
| --- | --- |
| [V2 后续报告](./framework_v2_followup_report.md) | 当前保留的补修及对照；执行提示候选已撤回 |
| [V2 实施记录](./framework_v2_report.md) | 两层优化、探针和历史对照 |
| [三层候选](./3_layer_opt.md) · [来源目录](./3_layer_sources_20261008.json) | 来源标记、局部净化、最终交付核验；研究候选 |
| [本次结构整理计划](./project_structure_20261008.md) | 文档分工、产物规则和整理验收 |

## 存放规则

| 路径 | 用途 |
| --- | --- |
| `workshop/*.md` | 当前及历史优化计划、报告、调研；日期与实施状态需明确 |
| `workshop/artifacts/<YYYYMMDD>_<task>/` | **所有新 agent 测试产物**：日志、fixture 输出、探针、临时评测、图表与检查报告；固定使用此位置 |
| `workshop/archive/` | 过期文档、旧图表和保留的原始版本 |
| `workshop/results/` | 已有阶段证据与诊断脚本，只保留历史材料，不新增运行输出 |

测试源码与 fixture 定义继续在 `tests/`；共享实现、runner 和 dashboard 保留原目录。用户正式 benchmark 结果在 [results/](../results/)，历史分析输入在 [download/](../download/)。Agent partial 测试必须显式指定 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。完整规则见 [AGENTS.md](../AGENTS.md)。

## 历史材料

| 入口 | 内容 |
| --- | --- |
| [初轮报告](./framework_optimization_report.md) · [方案](./framework_optimization_20261007.md) · [复核](./framework_optimization_review_20261007.md) | 旧 P0 修复、消融与结果分析，不代表当前默认全部启用 |
| [简化约束](./framework_optimization_direction_20261007.md) · [V2 提案](./framework_optimization_v2_proposal_20261007.md) | 按当时状态保留，以最新报告为准 |
| [早期 workshop 报告](./workshop_optimization_report.md) · [工程计划](./2026-10-05-workshop-engineering-optimization.md) | 早期 harness/trace 工作；八例 I3 no_go 已被 partial 证据取代 |
| [早期投稿工作稿](./ALMML_sub.md) · [当时的 CFP 附件](<./references/AIMLL WS.pdf>) | 原文归档，含过期状态与假设，不作为当前路线或投稿要求 |
| [旧文档与图表索引](./archive/project_structure_20261008/README.md) | 从 docs 和根目录撤下的原始材料 |
| [阶段证据与诊断脚本](./results/framework_optimization/) | 完整保留旧目录；脚本可能依赖历史代码或候选补丁 |
| [原迁移清单](./results/materials_migration_20261008/migration_manifest.json) · [本次清理清单](./artifacts/20261008_project_structure/structure_manifest.json) | 原字节哈希、新位置和显式退役的旧入口 |

归档不重写旧 evidence 的命令和哈希。原迁移的研究侧及 examples 兼容路径保留；docs 四个冗余别名已退役，三层方案使用的 follow-up 别名继续读取原版本。当前阅读使用本页入口；归档脚本不要直接重跑并覆盖旧输出。

## 检查

`ipi` 已激活，在 `DSCG/` 执行：

```bash
python workshop/verify_migration.py
```

该命令默认只读，核对原迁移哈希、保留/退役的兼容路径与文档链接；不再覆盖原 validation.json。需要新报告时传 `--output workshop/artifacts/<YYYYMMDD>_<task>/migration.json`，使用实际任务名及未存在的文件。

搬迁后的证据评分检查仍可运行，控制台日志存入本次 task artifact 目录：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover \
  -s workshop/results/framework_optimization/20261007_v2_followup \
  -p test_evidence_scoring.py -v
```

这些检查不调用模型，不改变 I3/E0/I2 状态，也不证明 benchmark 防御有效。
