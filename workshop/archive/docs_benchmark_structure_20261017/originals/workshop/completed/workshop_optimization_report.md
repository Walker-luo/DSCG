# DSCG Workshop 优化结果

> 2026-10-06 复核：下文八例 I3 的 `no_go` 是历史记录。旧脚本没有把错误反馈送入恢复回路，且注册工具时缺少参数 docstring，不能支撑对象级恢复约束。补齐后的 fixture 发现并修复了并发票据状态 bug，当前仍观察到全新调用的范围缺口，回报 `partial`。新证据见 [I3 报告](../../docs/i3_p0_stress_report.md)。

本轮改动集中在评测记录可靠性和离线恢复压力测试，未改变 P0 的授权、Reference Monitor、一次性执行票据或模型调用路径。

## 已完成

- E0 harness 审计：固定 seed 的任务排序、每次运行一个 manifest hash、每个样例一个 payload hash，并独立重放宿主 final-state predicate。
- 紧凑记录：默认摘要只保留任务标识、状态、错误类型、delivery 标志、结果、动作计数和受限 final-state 摘要；原生 AgentDojo cache 继续保留 `messages`，完整 trace 仍是显式 opt-in。
- 评测 runner/dashboard：缺少 `security_results[task_key]` 不再默认当作安全成功，而是写入 `infrastructure_error` 状态并从 ASR 有效分母排除；partial/dashboard 的有限任务选择改为固定 seed 排序。
- JSON 哈希投影：默认 `summary` 每个授权记录移除 4 个重复输入/目录哈希；`standard` 每个动作记录移除参数哈希，只保留契约或批次关联标识。P0 内存校验和 `full` 压缩 sidecar 保留原始哈希。
- I3 P0 压力测试：覆盖合法重试、未授权工具、扩大对象范围、关闭检查、伪造管理员、旧票据重放、修改目的地/参数、并发重复提交八条路径。

## 证据

```text
conda run -n ipi python -m unittest discover -s tests -q
Ran 86 tests ... OK

E0: valid=1, tool_error=1, infrastructure_error=4
I3: status=no_go, executed=1, blocked=7
```

报告文件：

- `/tmp/dscg-e0-harness-audit.json`，SHA-256 `7dbb694af20ef2b48c1121c0440b50340ce89a26af91ded589e1a75136fe9120`
- `/tmp/dscg-i3-p0-stress.json`，SHA-256 `3dde73adb12b5229eefe794cfb9e2677558552f1bc840e8ff6014f23358908aa`

## 效果边界

记录文件不再为 harness bookkeeping 添加参数级、事件级或环境字段级哈希，减少了冗余记录和泄露面。缺失安全结果会被显式计数，避免虚假的防御成功样本。离线 I3 没有发现可复现的 P0 越权恢复缺口，因此按路线记录 `no_go`，没有增加新的安全机制。

本轮没有运行真实模型 benchmark，不能据此宣称防御成功率或可用性提升；已有回归测试保持通过。研究侧状态文件未在本轮修改，待后续按路线入口回写。
