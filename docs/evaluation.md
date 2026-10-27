# 测试与验证入口

从 BaseIntent 根目录执行，先激活 `ipi`（AgentDojo）或 `ipi-agentdyn`（AgentDyn）。两者使用相同入口，按实际安装识别后端。

| 任务 | 入口 |
| --- | --- |
| 所选场景全部注册任务、baseline、clean、cohort | [完整评测](benchmark.md) |
| 每场景前三用户 × 前三注入目标 | [小批量评测](partial_benchmark.md) |
| 每个注入 GOAL 单次完整轨迹与冻结名单 | [目标筛选](injection_precheck.md) |
| 模型/工具/默认控制 | [配置](model_tool_configuration.md) |
| 评分、失败索引、成本与原始回复 | [结果](result_files.md) |

## Offline Regression

不调用模型的目录检查：

```bash
python -m baseintent.benchmark_catalog
```

按变更范围选定向测试；需要完整回归时：

```bash
conda run -n ipi python -B -m unittest discover -s tests -v
conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v
node --test tests/*.cjs
git diff --check
```

既有完整 Python 回归有失败/错误，不能默认全绿。新回归需区分基线失败、后端 skip 与新增故障。确定性 mock 只验证工程契约，不能证明 L2/L3 判断质量、TSR/ASR 或一般安全。文档变更只需链接/状态一致性和 diff 检查。

## Online Evaluation

使用既有实际 Qwen 配置、共享 runner 与原生评分；本页命令说明不构成一次新的在线验收。模型调用、API 错误和缓存回放分别报告，禁止以 mock 代替真实评测。行为变更的任务级覆盖至少 9 个不同已完成计分案例，并按影响范围扩大；全量 benchmark 需明确要求。

新产物写 `artifacts/<日期>_<任务>/`，通过 `--results-dir` 指定；保留任务/攻击 ID、实际后端、有效配置、原生轨迹、错误与 usage。报告计划、尝试、完成、有效、未完成、错误、跳过分别计数；GOAL 不进入计分分母。未记录 usage 保持未知。

当前有限历史观察为固定键 12 例：TSR 8/12→7/12、原生 ASR 0/8→0/8、progress 61→43、计分 Token −14.8%。这是 partial 验收，未建立普遍效用/防御结论。详见[框架边界](framework.md)。
