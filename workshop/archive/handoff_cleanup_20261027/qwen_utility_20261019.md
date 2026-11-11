# Qwen banking / Slack 通用效用修正

2026-10-21后续工程：按用户要求新增独立精简 `task-alignment-v1`，原目录配合步骤/操作/目的地匹配和当前动作审计；不晋升旧候选。诊断authorized-v2已修正合成授权与来源工具，legacy-v1旧响应可复核。候选显式开启，新benchmark命令见[指南](../docs/qwen_utility.md#task-alignment-v1)，真实效果仍待用户测量，无新增付费请求。

2026-10-21更新：用户已明确授权并完成audit96＋authorization48次Qwen诊断，API错误0、Token131,588，工具执行0。L3协议失败1→0，但效用未证明改善，银行48条响应漏带授权sandbox，须新版本修正诊断上下文。L2工具语义候选漏授权1→3、多授权2→3，新增逐对错授权1处，不晋升。见[实际报告](./completed/utility_diagnosis_20261021.md)和[当前指南](../docs/qwen_utility.md)。

状态：保留短版legacy；先修诊断输入，再设计最小候选。预算已耗尽，source阶段、37/97项clean和攻击未启动。本文件留在pending用于后续验收；原始包/响应和此前工程报告不改。不是TSR恢复或研究闸门结论。

候选仍按协议→工具语义→来源语义相邻比较；L1等待独立证据。后续付费调用另行授权，不因本轮protocol机械gate=true自动启动其他阶段。

接口：`prompt_profile=legacy|protocol-v1|tool-semantics-v1|source-context-v1`，候选累积前一阶段改动。默认legacy保留原提示、目录、模型、路由和重试。候选绑定提示内容和目录协议版本；不同候选不能混用缓存或校准文件。

验证：离线协议类型/阻断/日志边界、目录来源及身份、CLI/API/cohort接线，两个环境完整Python回归及Node。未来同轮37项局部clean、97项全量clean和冻结cohort三攻击比较，由用户授权后另跑，不用模拟结果冒充模型效果。

## 执行账本

- 基点：e9b494e6c13fcc0d0fee9885f5eadbdc58147e85，workshop分支，开始时工作树干净。
- Ruling：在用户指定的现有checkout内工作，保留结果和环境；不创建新worktree。
- Ruling：语义提示改进作为显式候选，不替换默认。离线mock无法确认模型判断改善，遵守先验收再替换的停止条件。
- Ruling：所有本轮产物存放workshop/artifacts/20261019_qwen_utility/，覆盖技能默认workspace位置。
- 完成：协议诊断、三个候选、CLI/API/cohort/身份绑定、15项新离线测试、两个环境完整回归（511/515项，各1跳过）、Node45/45、文档。
- 后续状态：有限144次响应已完成，候选不晋升；银行包授权状态缺失及来源工具一致性先修，新的模型/clean/攻击需另行预算。没有证据支持修改L1，因此未改。
- 边界修正：RED暴露错误decision=list被归为MODEL_ERROR、无效工具metadata在新目录中解引用None；分别修正为INVALID_DECISION和unknown/critical，全部仍失败关闭。
