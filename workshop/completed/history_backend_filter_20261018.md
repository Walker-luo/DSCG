# 历史分析目录／基准联动筛选（2026-10-18）

用户已批准“结果目录 → 基准 → 模型／运行 → 攻击”的方案。本次在历史侧栏增加基准下拉框，默认全部；选项来自当前目录记录中的benchmark_id。AgentDojo、AgentDyn、未记录和混合／身份不完整分别筛选，目录名或当前进程环境不提供缺失身份。

沿用已有递归读取和实际run ID，新后端子目录与旧扁平目录独立保留。模型、攻击、计数、场景和结果列表联动；筛选变化清除旧图表并勾选可见结果，自动刷新保留有效筛选和手动排除，明确清空模型不恢复全选。分析／下载继续使用可见勾选ID，原请求格式、目录接口、评分和导出身份不改。颜色、纹理及跨基准对齐警告保持现状。目录与基准在桌面、平板和窄屏均纵向排列。

代码基线：`d105c024b468206707107d694366b963c64c9e20`，开始时工作树干净。本阶段未提交；只改历史前端、样式／模板、两份Node回归和dashboard指南，增加本报告。精确前后状态、源码及产物SHA见[验证清单](../artifacts/20261018_history_backend_filter/validation.json)，原字节在before_sources；已有运行器、框架、历史证据和用户results/download不改。

| 检查命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `node --test tests/test_history_selection.cjs tests/test_history_ui_selection.cjs`，实现前 | 1 | 4项预期失败；[RED日志](../artifacts/20261018_history_backend_filter/red.log) |
| 同上，实现后 | 0 | 11/11；[GREEN日志](../artifacts/20261018_history_backend_filter/green.log) |
| `node --test tests/*.cjs` | 0 | 45/45；[日志](../artifacts/20261018_history_backend_filter/node.log) |
| `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v` | 0 | 496项，495通过、1后端专用跳过；[日志](../artifacts/20261018_history_backend_filter/ipi.log) |
| `conda run --no-capture-output -n ipi-agentdyn python -B -u -m unittest discover -s tests -v` | 0 | 500项，499通过、1后端专用跳过；[日志](../artifacts/20261018_history_backend_filter/ipi_agentdyn.log) |
| `node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `node --check dashboard/static/js/history_selection.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空输出 |
| `python workshop/artifacts/20261018_history_backend_filter/verify_delivery.py` | 0 | 原始文件、用户输出、日志、链接及证据核验 |

回归直接运行生产筛选器和事件／请求处理，覆盖新旧目录、同名运行、unknown/mixed、空目录、下游选项重置、明确空模型、手动排除和过期响应。请求回归确认真实分析和导出函数只发送选中的可见ID；旧分析完成后不能覆盖新基准筛选。限定独立复核无可行动问题，另跑相关Node28/28通过。

浏览器使用隔离人工数据：7份场景summary、6项运行身份；1440×1000桌面、1000×900平板、390×844窄屏。验证AgentDyn筛出2项新旧运行、unknown/mixed归类、切换partial目录重置不可用基准、自动刷新超过30秒后保留排除项、清空模型禁用按钮、分析表独立两行及下载ZIP。ZIP重新打开后确认仅两项AgentDyn且source路径不同。无浏览器控制台错误。详见[浏览器记录](../artifacts/20261018_history_backend_filter/browser_qa.json)、[窄屏截图](../artifacts/20261018_history_backend_filter/mobile.png)和[导出核验](../artifacts/20261018_history_backend_filter/browser_export_check.json)。截图和指标均为人工验收数据，不是模型成绩。

临时服务仅监听127.0.0.1:9451，已停止；测试页已关闭、viewport已恢复。浏览器自动生成的Downloads测试ZIP经逐字节校验归档后仅清理该自建副本，稳定产物保存在本阶段artifacts。0模型调用、0真实rollout；没有新效能分母、研究机制或闸门结论。现有身份不完整时仍可能出现配对比较警告，基准筛选不能替代身份／任务对齐检查。

下一步：刷新历史分析页，先选择结果目录，再用基准下拉框查看AgentDojo或AgentDyn；若服务缓存旧页面，重新加载静态资源。研究回报追加至technical_route当前链接的research/Experiments/implementation_status.md。
