# 实验配置与安全评测工作台更新（2026-10-10）

用户要求按当前框架调整“实验配置”和“安全评测工作台”，并优化前端。已对齐已实施的 `three-layer-v1`，本阶段只改 Dashboard 接线、展示、指标汇总与验证，不修改防御引擎、默认机制或正式研究路线。

## 已实施

- 配置栏按评测对象/模型、场景/攻击、防御组合分组；启动按钮固定，高级连接与日志设置折叠。新增独立 L1 和 L2 前置检查开关，提供完整三层、移除 L1/L2/L3、V2 对照与自定义预设。控件实际传入 factory；依赖关系与原生 baseline 归一化在服务端再次校验。授权使用主模型，L3 可配置独立审计模型。
- 工作台区分待启动配置与已保存运行的实际配置；默认展示结果概览，统一运行选择器，保留日志、图表、任务明细、对比与报告。桌面配置栏和窄屏纵向布局均已验收；窄屏增加工作台/配置跳转。
- 保存实际任务 IDs、场景完成进度、有效安全分母及缺失数量；TSR 按任务数、ASR 按有效布尔判定加权，良性评测 ASR 不适用。旧结果仅在逐任务记录完整且唯一时恢复 ASR 分母，否则显示未记录；使用副本派生展示指标，不改写旧文件。
- 概览、图表、对比与报告统一合计已记录主模型和审计模型 Token。主模型包含授权与攻击预检；历史缺审计使用量时显示成本覆盖限制。关闭 L3 / baseline 的 HTML 报告显示审计模型“未使用”，未知历史开关显示“未记录”。
- 三层统计从已计分任务 trace 读取 L1 重复呈现/新增字符、L2 允许/拒绝批次、L3 公开读取免审/语义调用，并显示 trace 覆盖；不纳入攻击生成预检。历史缺统计时不猜测为零。
- 攻击选项来自安装的 AgentDojo 定向自动攻击注册表；网页仍为单攻击入口。manual 和使用独立分母/计分口径的 DoS 不在此入口。网页有限子集保留 seed 排序，partial CLI 保留注册顺序前缀；跨入口仍须核对实际任务 IDs。

## 验收与证据

源代码基线为 `7d1e1ed27791cc87685bc512ba1b8fb5c1182d25`，开始时工作树干净；交付为未提交修改。精确工作树清单、源码/日志/截图/样例 SHA-256 见 [validation.json](../artifacts/20261010_dashboard_framework_ui/validation.json)。未创建 commit 或 PR。

在 DSCG 根目录执行：

| 命令 | 退出码 | 结果 / 日志 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 217/217；[offline_regression.log](../artifacts/20261010_dashboard_framework_ui/offline_regression.log) |
| `node --test tests/test_history*.cjs tests/test_dashboard_ui.cjs` | 0 | 26/26，其中历史 21、配置/报告 5；[node_tests.log](../artifacts/20261010_dashboard_framework_ui/node_tests.log) |
| `node --check dashboard/static/js/app.js` | 0 | [syntax_check.log](../artifacts/20261010_dashboard_framework_ui/syntax_check.log) |
| `git diff --check` | 0 | [diff_check.log](../artifacts/20261010_dashboard_framework_ui/diff_check.log) |
| `git diff --exit-code -- dscg experiments config` | 0 | 引擎、runner、配置文件无差异；[runtime_diff.log](../artifacts/20261010_dashboard_framework_ui/runtime_diff.log) |
| `python workshop/artifacts/20261010_dashboard_framework_ui/validate.py` | 0 | 本阶段文档链接/原文归档 hash/检查日志一致性；[validation.log](../artifacts/20261010_dashboard_framework_ui/validation.log) |

新增行为回归覆盖配置严格校验与依赖归一化、factory 接线、计分任务 trace 路径和预检排除、任务加权及未知 ASR、旧文件不改写、良性 ASR 不适用，以及各展示入口主模型+审计成本一致。新 Node 回归执行真实 `app.js` 的配置与报告函数。分母和报告问题均保留先失败后通过日志；独立限定审查的阻塞问题均已修复。

浏览器使用隔离的 localhost:9451 临时服务，仅从本阶段 `browser_results/` 加载验收样例；服务已停止，临时视口恢复。用户 8888 服务未重启，root `results/` 与 `download/` 未用于测试输出。

- [桌面截图](../artifacts/20261010_dashboard_framework_ui/desktop.jpg)：1440px 视口，配置预设、实际配置、指标与路由统计。
- [窄屏截图](../artifacts/20261010_dashboard_framework_ui/mobile_workspace.jpg)：390px 视口，页面导航与工作台跳转。
- 样例是 **2 条运行 × 2 条人工记录 = 4 条 UI 记录**，用于显示检查；截图中的 50% 和 1,300 Token 均为人工数据。此阶段 **0 模型调用、0 真实 benchmark rollout**。

修改前六份文档的原始字节保存在 [原文目录](../archive/dashboard_framework_ui_20261010/originals/)，映射见 [originals_manifest.json](../artifacts/20261010_dashboard_framework_ui/originals_manifest.json)。历史 manifest、结果、研究证据哈希均未重写。未运行全量迁移验收；已知旧兼容链接/展示快照限制见前阶段[文档交接报告](./framework_docs_cleanup_20261010.md)，本阶段只做当前变更的链接与原文校验。

## 限制与下一步

L1 字符增量不是 Token；路由记录和 native ASR 不构成独立安全真值。旧记录缺失项不能重建。未实现 CSA、独立失败片段浏览器或新防御层；真实 E0、I3 partial、I2 locked 和关闭路线状态保持。

下一步：重启 Dashboard 后刷新页面，用新运行名称验证所需配置；做正式匹配对照时核对模型、攻击、实际 task IDs 和安全分母。此 UI 验收不宣称 ASR/TSR 或总成本改善。
