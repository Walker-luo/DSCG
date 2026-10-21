# AgentDyn `tool_knowledge × dailylife` 不兼容组处理

状态：工程实现和离线验证完成；没有运行付费模型或真实 benchmark。基于工作树 `0235fbf5b6af22e4fd88c8d02f9d4e25a713c533`，本次修改尚未提交，工作树还包含此前 DeepSeek 请求兼容、进度及报告的未提交改动。

## 原因与处理

AgentDyn dailylife 的 10 个注入目标，其原生 `ground_truth` 都有至少一个工具调用缺少 `placeholder_args`。`ToolKnowledgeAttack.get_tools_sequence` 在计分任务的攻击构造阶段抛出 `ValueError`，先于缓存读取及计分轨迹生成。shopping、github 的所选目标通过同一只读检查。原 `results/partial_benchmark/agentdyn/deepseek-flash_test` 共 133 个文件，修改前后逐文件 SHA256 相同；原生任务、攻击模板和评分均未修改。

共享兼容检查只检查实际选中的目标，使用每个目标的原生默认环境和 `ground_truth`。发现缺失占位参数时，整个攻击×场景组为 `unsupported (missing_placeholder_args)`；其他参考调用异常记录为真实执行错误。CLI 在准备阶段、模型客户端与 GOAL 预检之前完成检查；`--progress` 与普通路径一致。执行记录包含理由、受影响目标 ID 和计划组合数；摘要显示 `0/计划数`、TSR/ASR `N/A`，不产生伪造计分样本。至少一个组完成且无真实错误时返回 0，全部不兼容返回 1。Dashboard 按网页实际选择检查，混合运行只聚合完成场景，全部不兼容时发出非成功终态并不展示成功率。

原计划数保持不变：AgentDyn 默认 partial typical 81，其中 9 不兼容、72 可执行；full typical 1,680，其中 200 不兼容、1,480 可执行。它们只是计划组合数；原生返回结果决定有效评分分母。cohort 按实际保留目标单独计算。

## 验证与证据

- `conda run -n ipi python -B -m unittest discover -s tests -v`：退出 0，共 575 项，其中 9 项跳过；`workshop/artifacts/20261020_agentdyn_tool_knowledge/python_ipi_final.log`。
- `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v`：退出 0，共 579 项，其中 1 项跳过；`workshop/artifacts/20261020_agentdyn_tool_knowledge/python_ipi_agentdyn_final.log`。真实 AgentDyn 套件离线复现原生 `ValueError`，测试了普通/进度、full/partial/cohort、Dashboard 全部不兼容与混合运行、续跑缓存、意外参考调用异常。
- `node --test tests/*.cjs`：退出 0，47 项通过；`workshop/artifacts/20261020_agentdyn_tool_knowledge/node_final.log`。
- 两个 AgentDyn CLI 的 `--help`：退出 0，见同目录 `full_help.txt`、`partial_help.txt`。两份测试指南的本地链接及锚点：19 项通过，见 `docs_guide_links.json`。仓库更广的链接扫描发现 README/AGENTS 历史引用的 `plan.md` 与 `report/report.md` 缺失，与本次新增链接无关，见 `docs_links.json`。
- `git diff --check` 与 `git diff --cached --check`：退出 0。原结果文件清单和哈希在 `original_results_hashes.json`；native 兼容性及计划数在 `native_compatibility.json`。

上述证据与本报告的逐文件 SHA256/字节数见 `workshop/artifacts/20261020_agentdyn_tool_knowledge/artifact_hashes.json`。

限制：离线模型 fixture 证明流程和计数行为，不证明 DeepSeek 在线请求、最终 TSR/ASR 或服务限流情况。下一步在相同配置绑定满足时，用原名称加 `--reuse` 补跑兼容组，并复核新的执行清单、摘要和原生轨迹；不要手工改写旧结果。
