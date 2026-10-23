# 图表目录

用户绘图入口在 [experiments/plots/](../../experiments/plots/)，既有默认输出仍为 `docs/figures/benchmarks/`；本轮不改绘图运行行为。

旧图表已保留在 [workshop 历史归档](../../workshop/archive/project_structure_20261008/docs/figures/)，不作为当前结果展示。

Agent 生成的测试/诊断图表必须使用 `workshop/artifacts/<YYYYMMDD>_<task>/figures/`。运行绘图入口前确认支持显式输出覆盖；没有覆盖能力时使用可指定输出的调用方式，避免落入当前文档目录。
