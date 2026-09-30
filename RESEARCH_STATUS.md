# DSCG 与 research 的交互入口

DSCG 只维护代码、测试、配置和工程实现状态。论文问题、文献矩阵、创新点、实验协议和投稿判断统一维护在项目根目录的 [`research/`](../research/)。

## 当前研究路线

工程实现按 [`research/technical_route.md`](../research/technical_route.md) 接收任务；当前版本是 `route-2026-09-30`。实现完成后按 [`research/paper/implementation_status.md`](../research/paper/implementation_status.md) 的 YAML 模板回报，至少包含任务编号、代码 commit、完整命令、测试结果、样本分母和阻塞原因。

## 当前状态

- P0 工具级底座已实现并有离线回归。
- E0 harness 审计已由研究侧解锁，I2 仍需等审计通过和独立 oracle 设计。
- I3 P0 压力测试已由研究侧解锁；I1、I4 和旧 provenance/source-to-sink 路线不在当前实现范围。
- `Paper_TODO.md`、论文证据报告和文献分析已经迁移到 `research/paper/` 与 `research/related_papers.md`；本文件不复制论文计划。

## 工程侧更新要求

每次完成研究路线任务后：

1. 在本仓库记录代码和测试变更。
2. 运行任务要求的命令并保存输出或结果哈希。
3. 更新 `research/paper/implementation_status.md` 中的一条回报记录，或者在提交说明中明确指出回报文件路径。
4. 不修改研究侧的 Go/No-Go 结论；若实现结果否定假设，回报 `no_go` 或 `partial`，由研究侧决定是否收缩主张。
