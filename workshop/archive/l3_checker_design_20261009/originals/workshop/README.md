# Workshop 待优化方案

顶层仅保留待优化方案及相关来源。当前运行框架仍为 V2 两层，已实施部分见 [completed/](./completed/README.md)；下列候选均未实现，正式路线以 [research](../../research/technical_route.md) 为准。

| 待优化方案 | 状态 |
| --- | --- |
| [三层架构候选](./3_layer_opt.md) · [来源目录](./3_layer_sources_20261008.json) | 2026-10-09 主候选：工具返回隔离 → 可信任务授权 → 按风险动作审计；复用现有编译/审计，无新增独立推理调用；未实现 |
| [授权对照校准](./original_framework_direction_20261008.md) | 旧的两层重构候选，保留参考；本轮复用现有编译/审计语义，不推进对照校准 |

按用户的低开销与 AIMLL workshop 定位，来源隔离重新作为便宜输入层考虑；确定性权限检查前置、已有公共读取免审计和一次动作审计协同。来源标记已有直接近邻，必须用消融证明组合值得保留；零新增调用不等于零新增 Tokens，也不承诺私有/写入任务极少触发审计。

三次影子提议的 [DRV 前版](./archive/3_layer_low_cost_20261009/originals/workshop/3_layer_opt.md)撤下在线主推荐，保留离线诊断参考；[更早版本](./archive/3_layer_redesign_20261008/originals/workshop/3_layer_opt.md)也保留。新候选仍未获研究侧实现解锁，运行时不变；新文档证据在 `artifacts/20261009_low_cost_three_layer/`。

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
