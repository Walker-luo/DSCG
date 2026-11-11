# 对比实验执行报告（2026-11-10）

模型：**qwen3.7-flash only**（DSCG Apache 端点，temperature 0）；后端：AgentDojo 0.1.35 / suite v1.2；
网格：`workshop/artifacts/20261105_qwen38_flash_attack/manifest/attack_grid_108.json`（4 suites × users 0-2 × 3 injections × 3 attacks = 108 攻击键；clean = 12 用户任务）；fliter：`results/workshop/agentdojo/qwen3.7-flash/v3.6.3/fliter.json`。

结果表（主产物：`workshop/artifacts/20261109_comparison_run/tables/comparison.md`）：

| 方法 | TSR | ASR | 错误 | clean TSR | chat calls | tokens | 备注 |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| baseline (native) | 82/108 (75.9%) | 41/108 (38.0%) | 0 | 11/12 | 440 | 1.49M | DSCG 原生循环 |
| GrantBind v3.7 | 94/108 (87.0%) | 0/108 (0.0%) | 0 | 11/12 | 769 | 1.98M | 同网格参考臂 |
| Spotlighting | 78/108 (72.2%) | 27/108 (25.0%) | 0 | 10/12 | 401 | 1.41M | AgentDojo 内置，未调参 |
| Tool Filter (invalid) | 0/108 (0.0%) | 0/108 (0.0%) | 0 | 0/12 | 219 | 8.58M | 实现不兼容，qwen 只回纯文本、不产生 tool call；仅作失败证据 |
| MELON | 70/108 (64.8%) | 1/108 (0.9%) | 0 | 9/12 | 514 | 2.01M | 官方代码移植 0.1.35；embedding 换 DashScope text-embedding-v4 |
| IPIGuard | 59/98 (60.2%) | 8/98 (8.2%) | 1 | 6/11 | 553 | 5.40M | 官方 0.1.23 fork / suite v1.1.2；workspace/injection_task_10 缺失 9 键 |

## 运行明细

| 运行 | env | commit | 起止（Asia/Shanghai） | exit | 结果目录 |
| --- | --- | --- | --- | --- | --- |
| spotlighting | DSCG | 52864fc | 11-09 20:24→20:27 | 0 | `results/workshop/agentdojo/qwen3.7-flash/spotlighting` |
| spotlighting_clean | DSCG | 52864fc | 11-09 20:27→20:28 | 0 | `.../spotlighting_clean` |
| tool_filter_ws_bk(+clean) | DSCG | 52864fc | 11-09 20:48→11-10 00:03 | 0 | `.../tool_filter_ws_bk[_clean]` |
| tool_filter_tr_sl(+clean) | DSCG | 52864fc | 11-09 20:48→11-10 00:04 | 0 | `.../tool_filter_tr_sl[_clean]` |
| baseline_108(+clean) | DSCG | 52864fc | 11-10 11:02→11:05 | 0 | `.../baseline_108[_clean]` |
| v37_108(+clean) | DSCG | 52864fc | 11-10 11:05→11:13 | 0 | `.../v37_108[_clean]` |
| melon(+clean) | cmp-melon | 52864fc | 11-09 20:37→21:28 | 0 | `/home/yuxin_luo/MELON/runs/melon[_clean]` |
| ipiguard(+clean) | cmp-ipiguard | 52864fc | 11-09 20:48→11-10 04:06 | 0 | `/home/yuxin_luo/IPIGuard/runs/ipiguard[_clean]` |

启动脚本与日志：`workshop/artifacts/20261109_comparison_run/{scripts,logs}/`；聚合脚本：`scripts/aggregate_comparison.py`。

## 有效性与偏差

1. **Tool Filter 无效**：`OpenAILLMToolFilter` 的工具选择提示在本 DashScope qwen 端点返回纯文本（如 `get_event_details, get_contact_info`），后续生成不再产生 tool call，108/108 效用为 False、clean 0/12。这是实现不兼容，不是防御效果；正文不得把它写成“Tool Filter 防御失败”。修复路径：改用 JSON/原生 function-calling 解析工具选择，或退回支持该元素的模型（需用户授权）。
2. **MELON 移植差异**：官方 `pi_detector.MELON` 依赖 OpenAI `text-embedding-3-large` 与旧版消息格式；本轮按官方算法（masked re-execution + tool-call 相似度 0.8）移植到 AgentDojo 0.1.35 typed messages，embedding 改为 DashScope `text-embedding-v4`（1024 维），并去掉未使用的 torch/transformers import。除 embedding 后端外阈值与流程未改。
3. **IPIGuard 版本差异**：官方仓库自带 AgentDojo 0.1.23 fork，只注册到 suite v1.1.2；本轮在共同键上运行（workspace/injection_task_10 在 0.1.23 不存在 → 跳过 9 键；99 尝试、98 有效、1 错误）。其 harness 打分与 DSCG 原生打分不同源，仅作同网格近似比较。
4. **同网格参考臂补齐**：baseline_108 与 v37_108 为 2026-11-10 新跑，保证与四个外部臂完全同键同攻击；GrantBind v3.7 在该网格 ASR 0/108、TSR 94/108。
5. **成本**：DSCG 侧 token 来自 `summary.json.api_accounting`（仅记录到调用方统计）；B 臂来自驱动内 OpenAI client 计数（不含 embedding 之外的重试）。IPIGuard completion tokens 偏高（3.17M）源于其 DAG 规划/遍历提示。

## 下一步

- 决定 Tool Filter 是否值得修复后重跑；若不修复，正文仅保留 Spotlighting/MELON/IPIGuard 三条外部对照并注明 Tool Filter 不可用。
- 用同一聚合脚本生成论文表（TSR/ASR 两列 + clean 脚注），并压缩 6 页版面。
- 若扩到 qwen3.8-flash 或其他网格，直接复用 `experiments/run_external_defense.py` 与两个 B 臂驱动。
