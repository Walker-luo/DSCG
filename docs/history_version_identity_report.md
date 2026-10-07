# 历史比较的版本视觉区分

日期：2026-10-07。状态：`pass`，仅表示显示工程验收通过。沿用独立历史页与模型多选；此前证据保持不变。

图表顶部突出 `baseline`、`workshop_new` 等短版本名，配合彩色字母标记。同一模型 / 运行名称在模型选择、结果列表、各图、热图表头和明细表中共用颜色与字母。柱状图在每个有数据的位置标出字母，包括零值；缺失数据和被隐藏的实验不绘制标记。点击图例仍可隐藏对应实验。

多攻击比较使用版本字母加攻击编号，例如 A1、A2；轴标签和提示保留攻击名，曲线 / 散点使用攻击级线型和点形。编号依据完整 catalog 的攻击名称排序，同一页面内切换子集不会重新排序。单攻击比较只显示版本字母，图例小字显示攻击及完整模型 / 运行名称，悬停提示包含完整来源。TSR / ASR 数值、分母及下载格式沿用原数据，不聚合不同实验。

## 验证

证据目录：[`examples/results/dashboard_history/20261007_version_identity/`](../examples/results/dashboard_history/20261007_version_identity/)。包含红 / 绿阶段日志、完整回归日志、截图、UI 检查记录、code revision 和 SHA-256 清单；用户当前 `.gitignore` 忽略 `examples/`，这些证据为本机文件。

| 命令 | 退出码 / 结果 |
|---|---|
| `conda run -n ipi python -m unittest discover -s tests -v` | 0；132/132 |
| `node --test tests/test_history*.cjs` | 0；21/21 |
| `node --check dashboard/static/js/history.js` | 0 |
| `node --check dashboard/static/js/history_charts.js` | 0 |
| `shasum -a 256 -c examples/results/dashboard_history/20261007_multiselect_page/artifacts.sha256` | 0；旧证据完整 |
| `git diff --check` | 0 |

新增 4 个 Node 回归，验证跨攻击的版本身份、零值 / 缺失 / 隐藏状态、多攻击二级身份及旧样式兼容。原有前端事件接线回归继续执行实际选择逻辑。只读复核发现多攻击样式复用会导致图形归属不清，补充编号与攻击样式后通过复核。

浏览器使用已有 baseline 与 workshop_new 数据验收：同一 `important_instructions` 下为 2 项实验、8 个场景结果，两张柱状图与列表共用 A / B；0% 与 100% 标记可见，顶部图例名称清楚，点击隐藏功能正常。全部攻击折线图显示 8 项实验、32 个场景结果，A1–A4 / B1–B4 区分四个攻击，模型主颜色保持一致。热图表头和明细表继续标出版本身份。控制台无警告 / 错误。

390 × 844 视口的页面 scrollWidth 为 383，图例和图表单列，没有页面横向溢出；临时视口已恢复。

## 边界与下一步

新目标模型样本数为 0（有效 / 无效 / 错误 / 跳过均为 0）。显示的历史指标没有经过本轮安全有效性审计，不能据此判断框架改进有效。没有运行模型 benchmark 或改写历史结果。

短名称按现有 `<model>_<name>` 目录约定提取；不同模型可能出现同名短版本，需要结合完整名称和来源。版本颜色 / 字母在本次页面 catalog 内稳定，不保证不同浏览器或重新载入后仍有相同分配。攻击点形 / 线型是有限集合，大量攻击比较应结合编号或选择少量攻击；相同坐标的散点仍可能重叠。

下一步：选择同一攻击和场景，核对不同框架版本的任务 ID，再检查配对原始轨迹与 E0 有效分母，决定后续改进方向。

![baseline 与 workshop_new 的版本标记](../examples/results/dashboard_history/20261007_version_identity/comparison.jpg)
