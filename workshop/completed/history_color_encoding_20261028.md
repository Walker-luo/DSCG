# 历史分析整体卡片配色（2026-10-28）

用户要求区分攻击底色和不同数据的数字颜色。本阶段为攻击分组标题与卡片填入不同底色；TSR、ASR、Token数字分别使用蓝、粉、黄，卡片边框和版本标记仍对应图表的运行颜色。页面提示说明配色含义，表头和注释提高对比度；同一目录中切换攻击筛选不改变颜色。场景数据、计数、导出和分析接口不变。

基线`workshop`／`89864f73f9a4a53a78872e3f65560e37f9ec3799`，开始时已有前一阶段未提交的历史汇总卡片变更；在其上调整前端、相关Node测试及项目状态，未提交。原阶段报告及证据不改。初始工作树和原字节在[before.json](../artifacts/20261028_history_color_encoding/before.json)及before_sources；本阶段工作树、源码和产物SHA见[validation.json](../artifacts/20261028_history_color_encoding/validation.json)。用户results/download文件大小和修改时间不变。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/test_history_charts.cjs tests/test_history_ui_selection.cjs`，修改前 | 1 | 两项预期失败；red.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 51/51；node.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空输出 |

桌面1440×1000及窄屏390×844使用上一阶段8份隔离人工summary验收，确认不同攻击底色、三指标颜色、筛选后颜色稳定和窄屏局部横向滚动；浏览器无错误、测试页关闭、viewport恢复、临时本机服务已停止。前20个底色与数字／表头文字的计算对比度最低5.253，见[contrast.json](../artifacts/20261028_history_color_encoding/contrast.json)。[桌面截图](../artifacts/20261028_history_color_encoding/desktop.png)与[窄屏截图](../artifacts/20261028_history_color_encoding/mobile.png)为人工数据，不是模型成绩。

本阶段0模型调用、0真实rollout；未重跑Python全量回归。前一阶段的两环境历史API各24项结果是其独立快照。攻击颜色在同次加载目录和筛选中稳定；新增攻击导致目录排序变化时可能重新分配。下一步：刷新Dashboard历史页并重新生成分析。
