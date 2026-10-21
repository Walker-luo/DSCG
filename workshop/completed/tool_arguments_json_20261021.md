# 工具参数 JSON 异常的单任务隔离（2026-10-21）

CLI full、partial、cohort 和旧 benchmark 转发入口现在统一按原注册顺序调用原生单任务函数。主模型工具参数解析失败只结束当前任务，后续任务继续；有任务错误仍退出 1。没有修补参数、重试请求或改变原生评分，screen、Dashboard、模型配置和 L2/L3 未调整。

## 原因与边界

用户的 `results/benchmarks/agentdojo/qwen3.7-flash_DSCG_v3` 在 `important_instructions/banking/user_task_3/injection_task_8` 中断，异常来自原生 `_openai_to_tool_call` 对模型 `function.arguments` 的解析。已保存 JSON 没有损坏；非法回复未保存，不能判定具体是空参数、截断还是其他语法错误。Slack 的 `restaurant …` 来自原生评分调试输出，与该异常无关。

AgentDyn 原生解析器还会吞掉非法调用并保留同回复中的合法调用。因此共享适配层临时观察主模型实例的已返回回复，使用原生转换函数识别 JSON 语法错误，在原生请求重试边界外中止该任务，确保混合调用也不会部分执行。实例方法、客户端结束后恢复；不修改已安装后端、响应对象、请求参数或审计模型。完整缓存仍由原生 loader 决定复用，不追溯重判其历史回复。

缓存损坏、攻击构造及其他 JSON 异常沿用原错误处理。诊断只记录固定错误码、阶段、任务 ID、参数长度、解析位置和最多八帧位置，不保存参数/响应/异常原文。

## 结果与续跑

- `task_errors.jsonl` 逐攻击/场景追加历史记录；当前 summary、失败索引只使用本次事件，成功续跑不会被旧错误污染。
- 计分及 clean 错误的内存标签为空，派生状态为基础设施错误；保留计划数，排除有效 TSR/ASR 分母。原生轨迹不补写布尔标签。
- GOAL 错误单列，既不作为能力失败，也不改变目标名单；计分任务仍按原计划执行。
- 进度推进已结束的尝试，100% 不表示全部成功。成功 API 返回的 Token 照常统计，不冒充 API 失败。
- 显式续跑只补原生判定缺失/不完整的任务，替换前保存原字节；完整缓存（包括原生接受的错误缓存）不自动重试。

原运行 708 个文件已逐字节保护，未执行或重写。服务器配置绑定匹配时，可由用户运行：

```bash
python -m experiments.run_benchmark \
  --model-config config/models.local.toml \
  --cohort results/injection_precheck/agentdojo/qwen3.7-flash_Qwen_screen/cohort.json \
  --suites banking slack --audit-router-mode selective \
  --audit-router-threshold 0.70 --progress --name DSCG_v3 --reuse
```

保持原模型请求、工具、防御和 cohort 配置；绑定冲突仍拒绝，不通过改写旧绑定绕过。

## 离线验收

起点 commit `54fa09ce6e127a816ae7f9fe9d9d6e025c98738d`，工作区干净；本阶段修改未提交。原文、RED/GREEN 日志、最终检查及哈希位于 [证据目录](../artifacts/20261021_tool_arguments_json/)，[交付清单](./tool_arguments_json_20261021_manifest.json)记录最终文件身份。

真实后端套件配合本地 MockTransport 覆盖空参数、截断、混合调用、正常 JSON、缓存损坏和攻击构造错误。baseline/DSCG、progress 开关、顺序/真实 spawn、full/partial/cohort、clean/DoS 和 GOAL 错误均覆盖。每个 partial 攻击样本 9 次计分尝试中 8 个有效、1 个错误；GOAL 错误样本仍有 9 个有效计分及 1 个独立未决预检；clean/DoS 为 3 次尝试、2 个有效、1 个错误。这些是合成响应的工程分母，不是模型效用或防御效果。

最终命令与退出码：

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| AgentDojo 全套 | `conda run -n ipi python -B -m unittest discover -s tests -v` | 退出 0；652 项，跳过 10 项；`ipi_verified.log` |
| AgentDyn 全套 | `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 退出 0；656 项，跳过 1 项；`agentdyn_verified.log` |
| Node | bundled Node `--test tests/*.cjs` | 退出 0；47 项通过；`node.log` |
| CLI | 两环境 full/partial `--help` | 均退出 0 |
| 文档、归档和原结果 | `python workshop/artifacts/20261021_tool_arguments_json/validate_delivery.py` | 见 `delivery_validation.json` |
| 补丁格式 | `git diff --check` | 退出 0，日志为空 |

本次检查 233 个当前文档链接，没有新增失效链接；README/Workshop 索引中已有的 4 处 `report/report.md` 缺失引用保持原样。归档哈希一致，原运行 708 个文件无变化。

原并行中断测试曾随机终止在原生 JSON 写入期间，造成按设计拒绝复用的损坏缓存；离线 fixture 改为在任务/场景边界等待后触发中断，仍验证子进程回收、完整缓存不变及续跑。损坏缓存拒绝、真实不完整轨迹补测与快照另有专项测试，未放宽生产缓存规则。

独立只读复核未发现需要修改的问题。本次付费调用 0、真实 benchmark 0；没有验证线上 Qwen 恢复或防御效果。下一步由用户按原配置显式续跑，再查看任务错误数量和有效分母。
