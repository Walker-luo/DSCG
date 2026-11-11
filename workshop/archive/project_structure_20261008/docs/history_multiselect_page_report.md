# 独立历史页与模型多选验收

日期：2026-10-07。状态：`pass`，仅表示页面、选择和导出工程验收通过。上一轮目录 / 攻击筛选证据见 [`history_attack_filter_report.md`](./history_attack_filter_report.md)，旧 artifact 保留。

## 页面与比较流程

- `/` 保留实验配置和当前运行工作台；`/history` 独立承载历史分析。共享导航并列显示“实验配置”和“历史分析”，标记当前页面。主页面不再加载历史分析脚本，历史页不加载实验运行脚本。
- 选择结果目录后，模型 / 运行名称提供复选框、“全选模型”和“清空模型”。可以同时勾选 baseline、P0 或 workshop 等版本，无需组合键。
- 更新目录、模型或攻击筛选后，默认勾选全部匹配结果，方便直接生成比较图；仍可在结果列表逐项取消。定时刷新保留当前手动选择。清空模型明确表示不选任何模型，刷新后保持为空并禁用分析 / 下载。
- 多个版本继续分别显示 TSR、ASR、Token 等指标，不合并不同实验分母。切换攻击也保留所选模型的全部匹配结果；筛选变化使等待中的旧分析失效。
- 保留场景选择、分图、独立图例、热图、散点和 ZIP 下载。API 与导出身份字段沿用上一轮格式。

比较框架改进时，可先清空模型，勾选 baseline 与待比较版本，再指定同一攻击和场景。图表用于找差异，归因前仍需核对任务 ID、配置和原始轨迹；界面选择不自动证明实验匹配或改进有效。

## 验证

证据目录：[`examples/results/dashboard_history/20261007_multiselect_page/`](../examples/results/dashboard_history/20261007_multiselect_page/)，含红阶段、回归日志、只读导出快照、代码 revision 和截图；`artifacts.sha256` 记录哈希。当前用户 `.gitignore` 忽略 `examples/`，证据为本机文件。

| 命令 | 退出码 / 结果 |
|---|---|
| `conda run -n ipi python -m unittest discover -s tests -v` | 0；132/132 |
| `conda run -n ipi python -m unittest discover -s tests -p test_dashboard_history.py -v` | 0；17/17 |
| `node --test tests/test_history*.cjs` | 0；17/17 |
| `node --check dashboard/static/js/history.js` | 0 |
| `conda run -n ipi python examples/results/dashboard_history/20261007_multiselect_page/verify.py` | 0 |
| `shasum -a 256 -c examples/results/dashboard_history/20261007_attack_filters/artifacts.sha256` | 0；旧证据完整 |
| `git diff --check` | 0 |

新增一个 Python 独立页面测试，并更新原页面断言；新增两个模型集合测试和一个执行实际前端事件接线的 Node VM 回归。VM 使用小型 DOM 适配器，验证全选两版本后换攻击仍选中两者、旧请求失效、清空模型后重新渲染保持空选择；图表像素由浏览器检查。

浏览器实际操作验证：两页导航正确，实验配置正常；勾选 baseline 与 workshop_new 后，在 `important_instructions` 下选中 2 个实验、8 个场景并分别成图；空模型选择禁用按钮；全选模型后连续切换 `injecagent` → `tool_knowledge` 仍选中当前 2 项匹配结果。复核发现并修复了全选模型使用 `null` 状态时换攻击只选中一项的遗漏。控制台无警告 / 错误。

390 × 844 窄屏检查：页面 scrollWidth 383，不超过视口；模型筛选与图表均为单列，导航文字可见。临时视口已恢复。

API 只读检查确认 `/`、`/history` 返回 200、页面 ID 无重复、脚本隔离正确。选中已有 baseline 与 workshop_new 的 `important_instructions/workspace`，ZIP 包含 2 个实验、2 个场景、18 条历史任务明细；JSON 和 CSV 保留两组身份，没有混入其他攻击。

## 边界

新目标模型样本数为 0（有效 / 无效 / 错误 / 跳过均为 0）。18 条导出明细来自已有数据，不是新评测或已审计的安全分母。没有运行模型 benchmark、迁移历史目录或修改原始结果；缺失 / 混合攻击和未知样本状态继续按原规则标记。导航到另一页面会载入该页面；当前筛选与图表不持久化。

下一步：用多个版本和同一攻击找出 TSR / ASR 差异，再对齐任务 ID 并核查原始轨迹，为后续框架改进提供依据；真实投递、predicate 与有效分母仍须 E0 审计。

以下截图仅展示历史数据的页面布局：

![多个框架版本的历史比较](../examples/results/dashboard_history/20261007_multiselect_page/comparison.jpg)
