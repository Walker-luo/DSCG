# 历史分析下载功能验收（2026-10-06）

用户请求：将“历史分析”中选择的对比测试结果下载，用于后续 agent 分析和框架改进，重点保留 ASR 与 TSR。此项是面板结果导出工程功能，不新增研究机制，不改变 I2/I3 状态。

## 使用与导出契约

勾选实验、选择场景后，点击“下载分析数据”。无需先生成图表，下载始终包含 ASR 和 TSR。ZIP 固定包含 `analysis.json`、`summary.csv`、`task_records.csv` 和 `README.md`。

JSON 是 agent 的推荐入口：源汇总指标统一为百分比，明细中的模型、攻击类型、任务 ID、布尔 outcome 和样本状态支持对齐比较；明细计算的分子、分母与百分比单独存储。原汇总保留原口径，不由任务数反推有效安全分母。

缺失指标为 null，CSV 中为空单元格；明确的模型、策略、工具、超时、基础设施错误及无效/跳过记录不计入观察性明细分母。旧记录状态为 unknown，并提示无法推定其已经通过 harness 审计。每个下载的明细上限为 50,000；上限耗尽后仍逐场景标注截断或无明细，不静默省略字段。

下载只读取 results/ 内已有实验，按目录生成的 ID 校验选择；不接受任意磁盘路径。ZIP 不打包原始配置、凭据、prompt 或工具轨迹；CSV 文本公式转义，JSON 保留原文本。所选场景无匹配数据、非法选择、消失的实验返回错误，前端恢复按钮并显示错误。

实现：[共享读取与下载接口](../dashboard/app.py)、[导出打包](../dashboard/history_export.py)、[页面交互](../dashboard/static/js/history.js)。

## 验证

命令均在 `/Users/luo/Desktop/AgentDefence/DSCG` 执行：

```bash
conda run -n ipi python -m unittest discover -s tests -v > examples/results/history_export/20261006_01a10ff4/tests.log 2>&1
conda run -n ipi python examples/results/history_export/20261006_01a10ff4/verify_export.py > examples/results/history_export/20261006_01a10ff4/export-check.log 2>&1
node --check dashboard/static/js/history.js
git diff --check
```

以上退出码均为 0。全套离线测试 **111/111 通过**，包含历史分析测试 13 项，其中本功能新增 9 项。覆盖所选实验/场景、0–1 到百分比换算、错误/缺失分母、CSV-only 旧记录、全局明细上限、非法请求、重复选择、空匹配和 CSV 公式文本转义。

新增下载测试在实现前因缺少接口失败；复核发现 canonical `policy_error` / `timeout` 被降为 unknown，新增测试先复现，再改为复用 `SampleStatus` 定义。最终回归无失败。

真实历史结果的导出附件检查使用 workshop_2.0、workshop_1.1 的 workspace：**2 实验 / 2 场景结果 / 8 明细**，各自观察性 ASR 分母为 4，TSR 为 75% 与 100%，ASR 均为原记录的 0%。这只验证结果读取与导出，不是新评测或防御结论。

浏览器验证了下载入口、当前场景选择、无选择时禁用、下载打包反馈，以及原有图表/表格继续正常。Browser Use 对 IAB/Chrome 的下载事件等待未返回保存路径，内部下载记录页面也受工具 URL 策略限制，因此不把浏览器反馈宣称为保存到用户下载目录的独立证据；附件状态、ZIP 可解压与内容由 Flask 真实路由验证。

## 证据与边界

- [示例 ZIP](../examples/results/history_export/20261006_01a10ff4/comparison.zip) / [agent 入口 JSON](../examples/results/history_export/20261006_01a10ff4/analysis.json)
- [离线测试日志](../examples/results/history_export/20261006_01a10ff4/tests.log) / [附件检查日志](../examples/results/history_export/20261006_01a10ff4/export-check.log)
- [验收截图](../examples/results/history_export/20261006_01a10ff4/preview.png)
- [代码版本](../examples/results/history_export/20261006_01a10ff4/code_revision.json) / [SHA256 清单](../examples/results/history_export/20261006_01a10ff4/artifacts.sha256)

明细 outcome 无法替代攻击投递、宿主 predicate 或完整工具轨迹。原汇总可能含默认零值或与明细不同的分母，导出分别保存并给出告警；历史 smoke 数据不转为正式 benchmark 结论。代码未新增 commit，base HEAD 与文件哈希标识本次工作树实现。既有结果及 sibling research 的其他修改保持原样。

下一步：用户用所需真实对比实验生成下载包，将 `analysis.json` 与需要归因的原始轨迹交给 agent 分析。
