# 框架优化实施报告

按 research/paper/framework_optimization_20261007.md 实现 P0 工程优化；不增加论文机制。各阶段验证日志与 evidence 位于 `examples/results/framework_optimization/20261007_implementation/`，研究回报写入 sibling implementation_status.md。

## P0-A — 任务隔离

顶层调用新建 context，清除旧授权缓存和历史、撤销票据；任务内循环沿用。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-A_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## P0-B — 成本与诊断

记录主模型/授权/审计 API、Token、耗时；历史分析显示两模型合计。官方攻击分数保留，E0 独立送达/环境复核仍待完成。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-B_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## P0-C — 外部请求

网页请求按外部接收方路由至现有审计；离线成对样例覆盖合法访问和注入网址。未实现 URL 对象约束。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-C_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## P1-A — 有界重审

可选一次语义 abstain 重审；保留当前任务历史，parser/超时不重试，持续不确定阻断。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P1-A_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## P1-B — 任务完成提示

可选通用提示继续已授权任务并覆盖用户要求字段；每次工具动作仍受现有 monitor/ticket 检查。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P1-B_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## P2 — 消融入口

partial CLI 支持 no-checker、重审和完成提示开关及匹配任务 manifest；实际安全/效用收益仍需有效在线对照。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P2_tests.log`）。新模型样本 0；不推断效用或防御率改善。

## 验证与使用

| 阶段 | Python 离线回归 | 提交 |
|---|---:|---|
| P0-A | 136/136 | d247d64 |
| P0-B | 139/139 | b029877 |
| P0-C | 141/141 | ee65851 |
| P1-A | 147/147 | 35023c9 |
| P1-B | 148/148 | 1553a1c |
| P2（含审查修复） | 158/158 | 见 research evidence |

Node 图表/选择器测试 21/21；新消融接线的暂存版本单独测试 8/8。用户此前攻击参数、目录布局和 Dashboard 的修改保留在工作树；阶段提交只纳入本轮增量，commit 单独不能代表整个当前工作树。HEAD 原有 baseline 回归预期（seed 20260927、2×2）与 HEAD runtime 已有选择（seed 7、前 3 项）不一致；本次整套测试使用用户工作树已有修订。新 manifest 显式保留当前注册顺序前 3 个 user/injection ID，seed=7 只为历史元数据，不控制模型随机性。

最终 I3：24/24 valid，8 scope violations，0 工具边界违规，命令退出 1，仍为 **partial**。E0 合成 self-check 共 6：valid=1、tool_error=1、infrastructure_error=4，命令退出 0；真实样例仍未独立通过载荷送达与最终状态复核。原始导出与轨迹的 324 个输入哈希保持不变。诊断命令只读取 workshop_new 的 144 条轨迹，保留官方 security 值并标记警告文本 / 外部 URL 候选；不把模型自述或候选动作当作环境 oracle。

审查补修：公开读取免审计分支计数为 0；trace 落盘失败也先撤销票据且保留原任务异常；全缓存保留已记录成本并另存零新增调用，混合缓存只报告当前 invocation；clean 不计入安全分母。没有因这些修复新增参数、对象或数据权限机制。

建议先冻结任务，再分别使用新名称运行 B0 / B1 / B3 / B4；每个配置另加 `--clean` 测相同 12 个用户任务。默认四种典型目标型攻击计划 144 条，保留官方 ASR；第一次在线运行前独立审查 E0 有效分母。完整 P0 默认包含隔离与外部请求风险修正；可用旧审阅 catalog 的副本配合 `--tool-metadata` 做风险分类单因素对照。

```bash
conda run -n ipi python -m experiments.run_partial_benchmark --write-task-manifest examples/results/optimization_tasks.json
conda run -n ipi python -m experiments.run_partial_benchmark --baseline --task-manifest examples/results/optimization_tasks.json --force-rerun --name b0_optimization
conda run -n ipi python -m experiments.run_partial_benchmark --no-checker --task-manifest examples/results/optimization_tasks.json --force-rerun --name b1_optimization
conda run -n ipi python -m experiments.run_partial_benchmark --task-manifest examples/results/optimization_tasks.json --force-rerun --trace-level full --name b3_optimization
conda run -n ipi python -m experiments.run_partial_benchmark --audit-retries 1 --task-manifest examples/results/optimization_tasks.json --force-rerun --name b4_reaudit
conda run -n ipi python -m experiments.run_partial_benchmark --completion-prompt --task-manifest examples/results/optimization_tasks.json --force-rerun --name b4_completion
```

以上仅为待运行命令，本轮新模型样本 **0**。TSR 损失 ≤2pp 和 Token 增幅 ≤20% 仍是待验证目标；尚无证据支持继续缩减审计范围。下一步：独立核验 E0 后运行冻结 manifest 的单因素配对，至少 3 次，并按 suite/user 任务簇分析。
