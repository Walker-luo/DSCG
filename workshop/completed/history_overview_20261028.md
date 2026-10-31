# 历史分析整体数据卡片（2026-10-28）

按用户要求新增“整体测试数据”：攻击分组，同一攻击内按加载目录中的版本顺序排列；每个运行用与图表一致的版本颜色显示一张卡片，表格包含合计与已选场景的TSR、ASR成功数／有效数、百分比和已记录Token。单场景及多场景使用相同选择范围，旧指标明细仍可查看。

TSR、ASR合计分别累加已记录成功数及有效分母后计算，不对场景百分比求平均。当前CLI的`attacked_tasks`为有效攻击样本数；缺少直接成功数时，仅在已记录原始比率与有效数能唯一还原整数时显示并标`*`。缺失／矛盾／不唯一的计数显示未知，不把错误计为成功。跨场景仅在已记录基准ID、revision及suite version完整且一致时合计；否则保留逐场景数据。Token展示主模型加审计的已记录值，缺失组件或已知API错误／缺失usage标为部分已记录；零不是未知的替代值。基线明确没有审计时不要求审计Token。

基线revision `89864f73f9a4a53a78872e3f65560e37f9ec3799`，分支`workshop`，开始时工作树干净；交付时工作树未提交。完整变更文件、工作树和SHA见[验证清单](../artifacts/20261028_history_overview/validation.json)；修改前字节见同目录before_sources。31942份用户results/download文件大小和修改时间未变。未修改框架、评分或研究闸门。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/test_history_charts.cjs`，实现前 | 1 | 新增汇总回归失败；red_node.log |
| `conda run --no-capture-output -n ipi python -B -m unittest discover -s tests -p test_dashboard_history.py -v`，实现前 | 1 | 2项缺失字段失败；red_python.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 51/51；node.log |
| `conda run --no-capture-output -n ipi python -B -m unittest discover -s tests -p test_dashboard_history.py -v` | 0 | 24/24；green_python.log |
| `conda run --no-capture-output -n ipi-agentdyn python -B -m unittest discover -s tests -p test_dashboard_history.py -v` | 0 | 24/24；agentdyn.log |
| `conda run --no-capture-output -n ipi env PYTHONPATH=. python -B workshop/artifacts/20261028_history_overview/verify_api.py` | 0 | 8份人工summary、4个运行，验证加权计数和已记录Token；api.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空输出 |

日志及截图均在`workshop/artifacts/20261028_history_overview/`。生产函数和实际API回归覆盖有效分母、缺失与不唯一分子、缺失Token、混合身份、颜色、排序和清空选择。独立Sol只读复核无可行动问题，相关Node25/25通过。

桌面1440×1000、窄屏390×844人工数据验收：两种攻击各两个版本、两场景，确认卡片顺序及颜色与图例对应、场景切换后的计数、窄屏卡片内横向滚动和键盘可聚焦。浏览器无错误；本机临时服务已停止、测试页关闭、viewport恢复。见[桌面截图](../artifacts/20261028_history_overview/desktop.png)、[窄屏截图](../artifacts/20261028_history_overview/mobile.png)及[browser_qa.json](../artifacts/20261028_history_overview/browser_qa.json)。图中数据为人工样例。

0模型调用、0真实benchmark rollout；8份人工summary不是效能样本。未运行全量Python回归，已运行两个后端环境中与此次变更对应的历史API回归；已有全量套件的历史失败不因此被视为解决。下一步：重启正在运行的Dashboard服务并刷新历史页，以实际选中运行和场景查看卡片。
