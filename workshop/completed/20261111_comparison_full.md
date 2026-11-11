# 全量对比实验报告（2026-11-11）

模型：**qwen3.7-flash only**；后端：AgentDojo 0.1.35 / suite v1.2；全量网格：97 个注册 user tasks × fliter（DSCG digest 前缀 72091a30）过滤后的全部 injections × 3 typical attacks = **1947 攻击键**（649/attack），clean = **97**。

## 结果

| Method | TSR (full) | ASR (full) | errors | clean TSR | common-key TSR | common-key ASR | chat calls | tokens |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: |
| Baseline (native，复用) | 1426/1944 (73.4%) | 438/1944 (22.5%) | 0 | 82/96 | 1233/1704 (72.4%) | 434/1704 (25.5%) | 9,409 | 41.37M |
| GrantBind v3.6.3 (复用) | 1542/1947 (79.2%) | 0/1947 (0.0%) | 0 | 83/97 | 1323/1707 (77.5%) | 0/1707 (0.0%) | 14,988 | 51.25M |
| Spotlighting | 1454/1946 (74.7%) | 345/1946 (17.7%) | 0 | 82/97 | 1253/1706 (73.4%) | 344/1706 (20.2%) | 9,070 | 40.42M |
| MELON | 1305/1938 (67.3%) | 27/1938 (1.4%) | 9 | 73/96 | 1104/1701 (64.9%) | 27/1701 (1.6%) | 11,812 | 60.96M |
| IPIGuard | 873/1667 (52.4%) | 23/1667 (1.4%) | 40 | 57/94 | 873/1667 (52.4%) | 23/1667 (1.4%) | 10,733 | 106.04M |

分场景 ASR（命中/有效键）：

| Method | workspace | travel | banking | slack |
| --- | --- | --- | --- | --- |
| Baseline | 31/839 | 99/360 | 124/431 | 184/314 |
| GrantBind v3.6.3 | 0/840 | 0/360 | 0/432 | 0/315 |
| Spotlighting | 17/840 | 98/360 | 93/432 | 137/314 |
| MELON | 1/836 | 6/358 | 5/430 | 15/314 |
| IPIGuard | 0/590 | 0/350 | 0/417 | 23/310 |

## 运行记录

| 运行 | 环境 | 起止（Asia/Shanghai） | exit | 备注 |
| --- | --- | --- | --- | --- |
| Spotlighting attack | DSCG | 12:25 → 13:53 | 1 | 1947 键，1 个任务错误（不阻断其他键） |
| Spotlighting clean | DSCG | 13:53 → 14:03 | 0 | 97 键 |
| MELON attack+clean | cmp-melon | 14:06 → 18:06 | 0 | 12 条 lane（4 suites × 3 attacks）+ 4 clean lane |
| IPIGuard attack | cmp-ipiguard | 15:41 → 次日 05:13 | 0 | 30 个分片，3 攻击池 × 3 worker，分片原子锁 |
| IPIGuard clean | cmp-ipiguard | 05:13 → 09:27 | 0 | 4 个 clean 分片 |

合并校验：MELON `missing=0 extra=0`（1947）、IPIGuard `missing=0 extra=0`（1707，expected 由 v1.2∩v1.1.2 生成）；clean 均 97 键。

## 口径与限制

1. Baseline 与 GrantBind 复用已有 full-scope 真跑（GrantBind 为 **v3.6.3 / DSCG_v3.6.3**，非 v3.7；无 v3.7 full 运行），未重跑。
2. IPIGuard 用官方仓库自带 AgentDojo 0.1.23 fork（suite v1.1.2）；workspace injection_task_10/11 不存在，裁剪 240 键（2 injections × 40 users × 3 attacks），在 1707 键上报告；common-key 列以该 1707 键为交集。
3. MELON 为官方检测器移植到 AgentDojo 0.1.35，唯一实质偏差为 embedding 换 DashScope text-embedding-v4（1024 维）；无任务裁剪。
4. 全部 error 为模型输出非法 JSON 的 JSONDecodeError（MELON 9/1947、IPIGuard 40/1707、clean 1/97 与 3/97），按基础设施错误记 null 标签、不计入有效分母。
5. token 为调用方记账（DSCG api_accounting / B 臂 client 包装）；原生重试 usage 可能未完全覆盖。MELON 另有 4,342 次 embedding（0.145M tokens）单列，未计入表内 tokens。
6. Tool Filter 在 qwen 端点不可用（108 键报告已判定），全量不重跑。

## 产物

- 汇总表：`workshop/artifacts/20261111_comparison_full/tables/comparison_full.md`；本地写作素材：`results/workshop/agentdojo/qwen3.7-flash/_comparison_full/`（README/PRUNING/MANIFEST/paper_table.tex/code）。
- 原始数据：`results/workshop/agentdojo/qwen3.7-flash/{spotlighting_full,melon_full,ipiguard_full}(_clean)`（服务器对应 DSCG results / MELON runs / IPIGuard runs）。
- 启动与合并脚本：`workshop/artifacts/20261111_comparison_full/scripts/`；日志：同目录 `logs/`。

## 下一步

- 论文表采用 `_comparison_full/paper_table_full.tex`（需压 6 页版面），正文注明：GrantBind=v3.6.3 full-scope 复用、IPIGuard v1.1.2 裁剪、MELON embedding 替换、Tool Filter 不可用。
- 如后续需要 v3.7 full 参考臂，可单跑 `experiments/run_benchmark.py` 全量（约 1.5–2h，qwen3.7-flash）。
