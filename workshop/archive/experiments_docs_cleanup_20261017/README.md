# 2026-10-17 experiments / docs 清理归档

本目录保留从当前入口退役的文件，以及本次修改文档前的完整字节。路径、理由、SHA-256与当前文档身份见 [relocation_manifest.json](./relocation_manifest.json)。归档不产生新实验结果，也不修改原生评分或研究闸门。

## 从当前目录退役

| 原路径 | 原始文件 | 退役原因 |
| --- | --- | --- |
| experiments/plots/draw_comparison.py | [原文](./originals/experiments/plots/draw_comparison.py) | 固定旧模型/旧统计数组，不读取当前结果 |
| experiments/plots/draw_combined.py | [原文](./originals/experiments/plots/draw_combined.py) | 同一旧数据的组合绘图，重复维护 |
| experiments/plots/draw_ablation.py | [原文](./originals/experiments/plots/draw_ablation.py) | 旧框架消融硬编码数字，无当前运行绑定 |
| experiments/plots/draw_cost.py | [原文](./originals/experiments/plots/draw_cost.py) | 固定旧Token/人民币数组，不是实时成本测量 |
| experiments/plots/__init__.py | [原文](./originals/experiments/plots/__init__.py) | 退役绘图包入口；当前代码无导入依赖 |
| experiments/payload_reporting_probe.py | [原文](./originals/experiments/payload_reporting_probe.py) | 10月12日阶段模型探针，依赖当时fixture/历史trace |
| experiments/payload_reporting_frozen_cases.py | [原文](./originals/experiments/payload_reporting_frozen_cases.py) | 绑定10月12日诊断文件、旧run名称与固定回放集合 |
| docs/figures/README.md | [原文](./originals/docs/figures/README.md) | 指向退役绘图入口的说明 |

以上脚本按原始字节归档，内部ROOT/输出路径仍按原位置编写，不能直接在归档位置运行。复现历史阶段需在独立检出中恢复原目录，并准备相应历史输入；有些脚本会请求模型。不要将硬编码图表当作当前测量或将其旧成本数组套用到新模型服务。

原图表仍在 [2026-10-08历史图表归档](../project_structure_20261008/docs/figures/)，用户results/download和既有报告、模型凭证不移动。10月12日报告仅调整两个阅读链接并标注迁移，原报告也保存在originals中；旧命令保持其原日期上下文。

## 当前入口与保留项

日常入口见 [experiments索引](../../../experiments/README.md) 和 [文档索引](../../../docs/README.md)。benchmark、injection预检、L3校准、工具目录生成、E0/I3审计均保留；trace_diagnostics仍有离线测试使用，只输出启发式标注，不能取代原生评分。

`docs/framework_v2_followup_report.md` 是现有旧证据兼容链接，仍保留原目标，不作为当前指南。当前共享runner、名单兼容映射、dscg、tests及原始结果字节不因本次整理改变。

旧 `workshop/verify_migration.py` 针对早期固定文档快照，在本轮开始前已因README历史哈希不匹配失败。保留原校验器和旧manifest，新的清理验证单独记录；不宣称旧迁移全量通过。
