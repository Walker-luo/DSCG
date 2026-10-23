# 历史分析柱顶标记与图例调整（2026-10-15）

用户要求解决A3/A4等柱顶标记重叠，并把图例小字改成只显示attack_name、增大字号。本次只改历史分析展示和Node回归；保留现有框架/文档脏修改，不修改防御、评分或用户结果。

- 原绘制器直接在每根柱顶写字，无碰撞检查；现按Canvas实际文字宽度检查矩形，优先柱顶，其次上下错层，并保持在绘图区内。移位标记使用同色引线，零值也保留标记。
- 密集柱图按标记长度和数据集数保留最小绘图区宽度，在卡片内横向滚动，避免小屏把所有柱子压到同一位置。
- 图例小字只显示攻击名；攻击缺失保持“未记录攻击”。小字10→12px、主标题14→15px，小字对比度提高；完整模型/目录身份留在悬停和可访问名称中。颜色、字母/攻击编号、曲线样式和导出身份不变。

基线revision为 `2dcc3d18af59de0136286d1c7090dba7624f6f8f`，有预先存在的L1/runtime/dashboard/docs修改；[before.json](../artifacts/20261015_history_labels/before.json)记录精确工作树和保护输入。本次未提交/创建PR。

| 检查命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `node --test tests/test_history*.cjs` | 0 | 23/23，含新增密集标记/图例身份两项；[node.log](../artifacts/20261015_history_labels/node.log) |
| `node --test tests/test_history*.cjs tests/test_dashboard_ui.cjs` | 0 | 33/33；[node_all.log](../artifacts/20261015_history_labels/node_all.log) |
| `conda run -n ipi python -m unittest discover -s tests -p test_dashboard_history.py -v` | 0 | 17/17；[python_history.log](../artifacts/20261015_history_labels/python_history.log) |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 303/303；[offline.log](../artifacts/20261015_history_labels/offline.log) |
| `node --check dashboard/static/js/history_charts.js` / `node --check dashboard/static/js/history.js` | 0 / 0 | 语法检查 |
| `git diff --check` | 0 | [diff_check.log](../artifacts/20261015_history_labels/diff_check.log) |
| `python workshop/artifacts/20261015_history_labels/validate.py` | 0 | 保护源码hash、用户输出size/mtime、日志及本报告链接；[validation.json](../artifacts/20261015_history_labels/validation.json) |

新增回归先失败（A1/A2重叠、副标题含多余模型名），后通过；RED为 [red.log](../artifacts/20261015_history_labels/red.log)。密集回归对0%/100%两端各绘制24个标记，验证数量、两两不相交及边界，同时保留隐藏/缺失观察与颜色身份原检查。

独立限定复核未发现确定的重要问题，另跑图表Node回归16/16通过；不把代码审查或模拟Canvas检查称为浏览器视觉验收。

视觉验收限制：临时服务仅绑定127.0.0.1:9451，读取本阶段48份人工场景汇总（3版本×4攻击×4场景）。浏览器首开早于服务就绪而连接失败，随后错误页的data URL被浏览器工具策略阻止；未能完成真实页面视觉复核或截图，不以自动回归代替视觉验收。没有切换浏览器/原生控制来绕过该限制。服务已停止，人工样例未进入用户results/download。0模型调用、0真实benchmark rollout，研究路线/闸门无变化。

下一步：刷新历史分析页重新生成图表；浏览器连接恢复后，以实际窗口核对密集标记和图例字号。所有本阶段源码/日志SHA、初始/交付工作树和限制见validation.json；原历史证据不改写。
