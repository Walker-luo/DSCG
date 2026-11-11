# 历史分析：攻击筛选与布局验收

日期：2026-10-07。状态：`pass`（展示、筛选与导出工程验收）。不新增防御机制，不代表真实 benchmark 或 E0 有效性审计通过。

## 改动

历史结果按实际目录 → 模型 / 运行组 → 攻击名称联动筛选。`partial_benchmark/`、`benchmark/`、`benchmarks/` 等保持原名称，模型组保留 `ablation_study/` 等中间目录以避免重名。新 `<model>_<name>/<attack>/<suite>/` 路径和旧平铺、`__attack` 路径均可读取。

攻击优先读取已保存的 `task_selection.attack`、`attack_type`、CSV 和逐行记录；没有记录时才使用配置。明确关闭攻击的配置归为 `none`；无法识别的旧记录为 `unknown`；含多种攻击的旧汇总为 `mixed`，不拆分或猜测其汇总分母。

“全选当前结果”、分析与下载只使用当前可见且勾选的实验。JSON、汇总 CSV 和任务 CSV 均保留 `result_folder`、`model_group`、`model_suffix`、`attack_name`。复核发现的旧响应覆盖新筛选问题已修复：选择变化和新请求会使旧分析失效，旧错误也不能覆盖当前状态。

桌面采用筛选侧栏和分析主区域，默认分组柱状图；图例位于画布外且支持点击显示 / 隐藏。超过 6 项对比自动改为单列，窄屏堆叠；表格固定表头并保留独立滚动。原百分比范围、Token 独立轴、颜色对应及下载分母口径保留。

## 验证

证据目录：[`examples/results/dashboard_history/20261007_attack_filters/`](../examples/results/dashboard_history/20261007_attack_filters/)。当前 `.gitignore` 忽略 `examples/`，证据保存在本机；哈希清单位于该目录 `artifacts.sha256`。

| 命令 / 检查 | 退出码 / 结果 |
|---|---|
| `conda run -n ipi python -m unittest discover -s tests -v` | 0；131/131 |
| `conda run -n ipi python -m unittest discover -s tests -p 'test_partial*.py' -v` | 0；17/17 |
| `node --test tests/test_history_selection.cjs tests/test_history_charts.cjs` | 0；14/14 |
| `node --check dashboard/static/js/history.js` | 0 |
| `conda run -n ipi python examples/results/dashboard_history/20261007_attack_filters/verify.py` | 0；真实目录只读扫描和单项导出 |
| `git diff --check` | 0 |
| 本机浏览器：目录、模型、攻击联动；全选；图例；热图和散点 | 通过；控制台未发现警告 / 错误 |
| 390 × 844 窄屏 | 页面宽度 390，无横向溢出；筛选与图表单列 |

新增 dashboard Python 回归 3 项（该文件共 16 项）；Node 筛选与异步请求回归 4 项，原图表测试 10 项。红阶段日志记录良性配置误分类和缺少异步请求门控的失败。

首次完整回归为 128/131，3 项失败来自旧测试仍预期 seed 排序，但共享工作树中的 partial runner 已改为注册顺序前 3 个注入任务。保留当前 runner 代码，仅同步任务匹配、真实日志 / 缓存测试的预期和文档。baseline 与 DSCG 的精确 ID 匹配断言保留；旧证据不改写。当前 `seed: 7` 是保留的元数据，不参与 prefix 选择。

浏览器下载操作已返回“开始下载 ZIP”；自动化下载事件等待超时，未据此声称验证了浏览器下载文件落盘。改用当前 Flask API 获取并验证 ZIP，JSON / CSV 的目录、模型和攻击字段一致。只读验证选中已有 baseline 的 `injecagent/workspace`，导出 1 个实验、1 个场景、9 条历史明细；这不是 9 条新模型评测，也不证明其有效安全分母。

## 限制与下一步

- 新目标模型样本：0；有效 / 无效 / 错误 / 跳过模型样本均为 0。已有结果仅用于显示和导出，沿用原缺失值、状态与分母。
- 浏览器检查期间已有结果仍在增加；截图和目录快照是当时状态，不是冻结的实验 manifest。旧模型结果与已记录哈希均保留。
- 没有攻击元数据的旧结果显示“未记录攻击”；混合旧汇总只能作为整体选择。未迁移目录，也未凭路径猜测攻击或重新计算原汇总。
- 真实 payload 投递、predicate 误报、trace 重建与有效分母仍属于 E0。下一步按同一任务 ID 和同一攻击筛选两组结果，再审计对应原始轨迹；界面可视化不能替代这项审计。

截图仅展示既有结果的布局，不支持防御效力结论：

![按攻击筛选并比较两组结果](../examples/results/dashboard_history/20261007_attack_filters/charts.jpg)
