# 当前交接残留清理（2026-10-27）

范围：仅DSCG的`workshop`分支，开始HEAD为`290b6a156b5a0eaed631171e105c45de7db39de7`，初始Git status为空。本次审查全仓库路径／文本引用，并按当前源码核对现行规则、状态、文档及计划入口；不是一次完整运行算法或安全质量审计。兄弟BaseIntent／research及全局Codex规则未修改。

## 删除的过时交接

| 位置 | 清理内容 |
| --- | --- |
| AGENTS.md | 删除host意图进度FSM、goal_kind、current-intent与票据意图状态、legacy-v34、忽略sink的读取免审、旧Abort／False-False计分覆盖及缺失的跨分支报告链接；改为当前static-task-v352／sink-free-read-v4契约 |
| DV_STATE.md | 删除跨分支快照说明、过期HEAD、重复阶段交接与旧“本轮”状态；保留当前实现、正式结果、未解决问题和验证边界 |
| RESEARCH_STATUS.md | 删除当前V2两层／三层未实施的旧状态与失效research/paper入口；研究回报跟随technical_route当前链接 |
| experiments/README.md | 删除已移除进程调度的旧顺序执行说明，改为当前按attack并行；同步当前模型／调用授权边界 |
| Workshop索引与L1/L2/L3余项 | 删除v3.1／v3.4当前默认、已实现功能仍标未实施、阈值控制当前免审、过期平台与迁移状态；阶段索引只做历史导航 |
| 7份过期顶层执行计划 | 移除旧预算／执行门槛／技能执行指令和待实施状态，保留原阶段记录入口；完整原方案字节移入显式历史归档 |
| 当前文档与analysis/plan.md | 将“最新”结果统一指向v3.5.3；当前正式结果与历史专项分开；后续任务只保留已有未解决问题 |

当前代码依据：`dscg/prompt_profiles.py`、`dscg/task_view.py`、`dscg/input_isolation.py`、`dscg/audit_router.py`、`dscg/pipelines/defended.py`、共享计分／运行入口及Dashboard配置。当前没有`dscg/intent_flow.py`；静态视图仍可含intent，但没有宿主意图进度FSM。`authorization_intents`阶段名和旧intent/progress侧车字段的兼容读取保留，不能因名字相似删除有效兼容路径。

## Offline Documentation Verification

本次仅修改文档。检查当前文档链接／锚点、代码路径与默认契约、旧状态残留、原方案SHA256及初始tracked文件／index身份；结果见`workshop/artifacts/20261027_handoff_cleanup/validation.json`。具体命令／退出码与初始快照在同目录。未执行Python／Node运行时回归或原生工具任务，不声称全套测试通过。

在线模型请求0；未进行Online Evaluation。纯文档清理不需要9任务在线验证，且不改变已有真实模型成绩、错误、分母或费用结论。

## 原文与边界

- 清理前说明／状态／计划字节与开始Git身份保存在`workshop/artifacts/20261027_handoff_cleanup/originals/`及`initial.json`。
- 7份历史执行计划的可追踪原文和哈希见[归档manifest](../archive/handoff_cleanup_20261027/manifest.json)。归档保留原相对路径语境，不作为当前操作说明。
- 既有历史阶段报告正文、结果／导出、模型／工具配置、凭据、运行源码和测试源码均未由本次修改；不删除历史兼容读取代码，不重写原生标签。
- 未暂存、提交或切换分支。E0 pending、I3 partial、I2 locked及原生重试错误投影等遗留保持。

下一行动：按[当前计划](../../analysis/plan.md)复用v3.5.3正式配对账选择单项改动，不重新执行旧campaign或跨分支任务。
