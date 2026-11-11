# Workshop 待优化方案

顶层仅保留待优化方案及相关来源。当前运行框架仍为 V2 两层，已实施部分见 [completed/](./completed/README.md)；下列候选均未实现，正式路线以 [research](../../research/technical_route.md) 为准。

| 待优化方案 | 状态 |
| --- | --- |
| [授权对照校准](./original_framework_direction_20261008.md) | 新的两层重构候选；对照有效性、新颖性与收益待验证 |
| [三层架构候选](./3_layer_opt.md) · [来源目录](./3_layer_sources_20261008.json) | 来源标记、局部净化、交付核验；作为备选保留 |

## 存放规则

| 路径 | 内容 |
| --- | --- |
| `workshop/*.md` | 待优化方案；README 为索引，相关来源与检查脚本可留在顶层 |
| [completed/](./completed/README.md) | 已完成阶段的方案与报告；撤回、被替代部分在索引明确标注 |
| `artifacts/<YYYYMMDD>_<task>/` | 所有新 agent 测试产物，固定使用此位置 |
| `archive/` | 旧文档、投稿附件及迁移前的原始字节 |
| [results/](./results/framework_optimization/) | 已有阶段证据与诊断脚本，不新增运行输出 |

方案完成后连同阶段报告移入 `completed/`，更新两级索引及引用。归档不代表所有候选已启用；未落地部分必须注明状态。原始证据的命令、结果和哈希保持原样。

测试源码在 `tests/`，用户正式实验与导出保留在 [results/](../results/) 和 [download/](../download/)。Agent partial 测试必须显式指定 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。完整规则见 [AGENTS.md](../AGENTS.md)。

## 检查

`ipi` 已激活，在 `DSCG/` 执行：

```bash
python workshop/verify_migration.py
```

默认只读；需要新报告时传 `--output workshop/artifacts/<YYYYMMDD>_<task>/migration.json`，文件必须尚不存在。[本次搬迁清单](./artifacts/20261008_workshop_cleanup/relocation_manifest.json)记录新旧位置与原始哈希；旧迁移清单不改写。

这些检查不调用模型，不改变 I3/E0/I2 状态，也不证明 benchmark 防御有效。
