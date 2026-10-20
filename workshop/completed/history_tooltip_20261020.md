# 历史图表提示框短名称（2026-10-20）

用户要求去掉提示框的完整地址，避免遮挡TSR／ASR数值。根因是普通图表和散点图的tooltip回调使用fullLabel，包含原始来源路径。两处回调现使用既有短label，例如DSCG；同版本多个攻击时保留攻击名以区分数据。完整身份仍保留在原元数据、图例身份提示和导出中，未改指标或目录读取。

基线revision：`45b4acd1e8b9427978371da830b8f794ed6a1fb7`，工作树已有用户框架／兼容性修改。本任务仅改history_charts.js和对应测试，新增本报告；无提交。初始工作树和原字节见[before.json](../artifacts/20261020_history_tooltip/before.json)，当前源码、产物SHA及交付状态见[validation.json](../artifacts/20261020_history_tooltip/validation.json)。831份其他已跟踪文件SHA不变，11915份用户results/download文件大小和修改时间不变。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/test_history_charts.cjs`，修复前 | 1 | 新增2项失败，复现长路径；[RED](../artifacts/20261020_history_tooltip/red.log) |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 47/47；[Node日志](../artifacts/20261020_history_tooltip/node.log) |
| `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v` | 0 | 557项，556通过、1跳过；[日志](../artifacts/20261020_history_tooltip/ipi.log) |
| `conda run --no-capture-output -n ipi-agentdyn python -B -u -m unittest discover -s tests -v` | 0 | 561项，560通过、1跳过；[日志](../artifacts/20261020_history_tooltip/ipi_agentdyn.log) |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空输出 |
| `python workshop/artifacts/20261020_history_tooltip/delivery.py` | 0 | 保护输入、日志、源码和交付清单检查 |

回归直接调用生产tooltip回调，覆盖柱状／折线／雷达的TSR、ASR、0值、缺失值和Token单位，以及散点同时显示ASR／TSR、多攻击区分；完整来源元数据保持原值。当前shell没有node命令，已使用应用自带Node，未安装依赖或更改环境。

视觉限制：已有连接错误测试页在reload时被浏览器URL策略拒绝（frame authority／protocol）；停止浏览器尝试，未换页面／浏览器绕过，也未取得视觉截图。临时本机9451服务已停止，人工summary仅存本阶段artifacts。见[浏览器记录](../artifacts/20261020_history_tooltip/browser_qa.json)。1份人工summary、0模型调用、0真实rollout；测试数量不是效能分母，研究路线和闸门不变。

下一步：刷新历史页并重新生成图表，确认实际窗口下短名称和数值的显示；浏览器工具恢复后补视觉检查。旧数据、凭据、运行器及已有证据不改。
