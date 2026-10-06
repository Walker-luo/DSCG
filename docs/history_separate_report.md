# 历史分析分图与实验颜色

日期：2026-10-06。用户要求：多选指标分别成图，确认线条颜色对应。

每个选择的指标生成独立卡片、画布和图例，桌面端两列，860px 以下一列。TSR、ASR、防御率、Token 均单独展示；Token 图使用千单位纵轴。百分比边界留白继续保留。

颜色、点形和线型按实验 ID 分配，页面内缓存，在指标切换、场景切换、实验子集变化与目录刷新时保持对应。实验列表显示颜色标识；图例标识使用与线条相同的颜色。超过五项实验时生成额外颜色。重新生成或切换热图前销毁所有旧图表。

## 验证

命令均从 DSCG 根目录执行。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `node --test tests/test_history_charts.cjs` | 0 | 10/10：独立指标数据、颜色与图例、重排/子集、缺失值、Token 单位、范围、雷达限制与长名称换行 |
| `conda run -n ipi python -m unittest discover -s tests -p test_dashboard_history.py -v` | 0 | 历史分析与导出 13/13 |
| `conda run -n ipi python -m unittest discover -s tests -v > /tmp/dscg-history-separated-python-tests.log 2>&1` | 1 | 118 项中 117 通过；下述已有 baseline 采样测试失败 |
| `node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空白检查 |
| `shasum -a 256 -c examples/results/history_separate/20261006_01a10ff4/artifacts.sha256` | 0 | 本次证据哈希 |

全量失败项：`test_baseline_and_dscg_use_identical_actual_catalog_subsets`。当前工作区已有的 `experiments/run_partial_benchmark.py` 使用 `selection_seed = 7`、3 个 injection task，而 `tests/test_partial_baseline.py` 仍预期 seed 20260927、2 个 injection task；断言显示实际 `user_task_16/user_task_33` 与预期 `user_task_7/user_task_27` 不一致。该工程变动不属于本次界面任务，相关代码及测试保留。失败原始输出见本次 `python-tests.log`，不将全量回归报告为通过。

浏览器实际验证 1280×720 与 768×900：3 项历史实验、12 个场景汇总；两张独立 TSR/ASR 折线，四指标四画布，独立 Token 轴；单 travel 场景 3 项实验颜色；两张雷达；散点一画布→热图零画布→折线两画布；取消蓝色实验后绿色/黄色保持对应；窄屏卡片纵向且无重叠。ASR 数据全为 0 时曲线重叠，通过图例先隐藏蓝色、再隐藏绿色，分别确认绿色、黄色曲线及点形与实验图例匹配。error/warn 日志为空。

## 证据与限制

基准提交 `e4862aeaaa4c2e674b02877c7bec9fb7fe983727`，工作树 dirty。当前源文件、相关 baseline 代码/测试及 UI 输入哈希见 [`code_revision.json`](../examples/results/history_separate/20261006_01a10ff4/code_revision.json)，证据哈希见 [`artifacts.sha256`](../examples/results/history_separate/20261006_01a10ff4/artifacts.sha256)。上一轮多指标与下载证据文件保持原样。

截图与测试日志位于 [`本次证据目录`](../examples/results/history_separate/20261006_01a10ff4/)。未生成 benchmark 样本或调用模型。单场景每个实验仅有一个观测值，折线形式显示独立彩色点；柱状形式显示各实验的彩色柱。相同值会真实重叠，可点击图例核对；不偏移数据。颜色缓存持续至页面刷新，新打开页面按当前实验目录分配颜色。下载格式与指标范围不变。

下一步：重启面板并刷新页面，选择所需指标生成独立图表；baseline 工程任务后续应同步采样预期。
