# 历史分析多指标与图表范围

日期：2026-10-06。范围：用户请求的面板改动，支持指标多选并修复 0%／100% 边界显示；沿用历史数据下载功能。

## 行为

- 四项指标改为复选框，默认选择 TSR 与 ASR。全部场景按“实验 × 指标”生成独立序列；单场景按指标比较实验。缺失值保持 `null`。
- 百分比折线、柱状、散点图默认范围 −5～105；数据超出通常范围时再扩展。刻度固定显示 0、25、50、75、100%，避免 Chart.js 用留白边界替换端点刻度。横轴与画布增加留白。
- 雷达图外圈为 110%，仅支持全部场景的百分比指标。选择 Token 或单场景时回退到柱状图。
- Token 以千为单位；与百分比混选时使用右侧独立纵轴。空选时禁用生成按钮；散点、热图保持固定指标并禁用指标选择。

## 验证

所有命令从 DSCG 仓库根目录执行。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `node --test tests/test_history_charts.cjs` | 0 | 6/6，覆盖多序列、单场景、缺失值、百分比范围及刻度、双轴和雷达限制 |
| `node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `conda run -n ipi python -m unittest discover -s tests -v > /tmp/dscg-history-multi-python-tests.log 2>&1` | 0 | 118/118；包括当前工作区已有的 baseline 测试与 13 项历史分析测试 |
| `git diff --check` | 0 | 无空白错误 |
| `shasum -a 256 -c examples/results/history_metrics/20261006_01a10ff4/artifacts.sha256` | 0 | 本次证据完整 |

Node 测试先观察模块缺失及端点刻度回归失败（退出码 1），实现后通过。使用本地 Flask 面板和实际 Chart.js 4.4.0，在默认 1280×720 浏览器视口核验：双指标折线；散点边界；雷达外圈；单场景 TSR/ASR/Token 柱状与独立轴；空选→散点→热图→折线的控件状态；雷达混选 Token 的回退。浏览器 error/warn 日志为空。

UI 使用已有 `deepseek-flash_baseline_new` 与 `deepseek-flash_workshop_2.0`，共 2 项实验、8 个场景汇总；单场景检查使用 travel 的 2 个汇总。未生成新的 benchmark 样本，未调用模型，也未改写结果数据。

## 版本、证据与限制

基准提交 `e4862aeaaa4c2e674b02877c7bec9fb7fe983727`，工作树为 dirty；保留已有下载功能和其他 baseline/AGENTS 改动。源文件哈希、工作树状态、输入汇总哈希见 [`code_revision.json`](../examples/results/history_metrics/20261006_01a10ff4/code_revision.json)。所有本次证据哈希见 [`artifacts.sha256`](../examples/results/history_metrics/20261006_01a10ff4/artifacts.sha256)。前一次下载验收目录保持原样。

截图：[`controls.png`](../examples/results/history_metrics/20261006_01a10ff4/controls.png)、[`preview.png`](../examples/results/history_metrics/20261006_01a10ff4/preview.png)、[`scatter.png`](../examples/results/history_metrics/20261006_01a10ff4/scatter.png)、[`radar.png`](../examples/results/history_metrics/20261006_01a10ff4/radar.png)、[`mixed_tokens.png`](../examples/results/history_metrics/20261006_01a10ff4/mixed_tokens.png)。本次仅核验默认桌面视口；历史数据的 smoke 限制继续适用。图表需点击“生成分析”更新；下载仍包含全部 ASR/TSR 汇总，不受图表指标选择影响。

下一步：重启面板并刷新页面，勾选所需指标后生成对比图。
