# BaseIntent 研究状态

BaseIntent 是单独维护的研究方向；当前技术说明在 [docs/framework.md](docs/framework.md)，工程状态在 [DV_STATE.md](DV_STATE.md)，配置／验证在 [docs/README.md](docs/README.md)。当前代码与运行不依赖兄弟仓库或历史工程报告。

实现研究对象是：可信任务的意图分解、冻结工具能力、执行事件与语义完成判断的分工，以及有状态执行中介。当前仍只提供工具级控制；未实现一般参数／对象授权、事实认证、完整任务覆盖oracle或自动恢复。本次整理不增加算法或论文创新声明。

前一阶段小样本仍存在效用损失，不能把模型调用减少当成研究质量通过。后续研究设计、独立对照与有效性检查需在本项目明确记录，保留所有失败和实际分母。

用户选择保留原Git linked-worktree／历史／remote；代码和研究方向独立不等于Git仓库已拆分。重命名验证的实际范围与限制见 [维护记录](docs/maintenance.md)。
