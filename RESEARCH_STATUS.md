# DSCG 与 research 的交互入口

DSCG 维护实现、测试、使用说明和 workshop 优化材料；正式论文问题、创新判断、实验协议与投稿计划留在兄弟仓库 [research/](../research/)。

工程任务唯一入口是 [technical_route.md](../research/technical_route.md)，当前 route-2026-09-30。完成后向 [implementation_status.md](../research/paper/implementation_status.md) 追加 commit、工作树、完整命令/退出码、产物哈希、样本分母、限制和下一步。

| 范围 | 当前状态 |
| --- | --- |
| P0 | 工具级底座已实现；当前 V2 保留两层防御 |
| E0 | 真实 harness 审计待完成，合成自检不代表过闸 |
| I3 | partial：24 条有效样例中 8 条范围缺口，待研究侧复核 |
| I2 / 三层候选 | 尚未解锁或实现；旧 provenance/source-to-sink 路线保持关闭 |

所有优化计划与报告在 [workshop/](./workshop/README.md)，新 agent 测试产物固定在 `workshop/artifacts/<YYYYMMDD>_<task>/`；用户正式原始实验仍在 `results/`。详见 [AGENTS.md](./AGENTS.md)。

根目录冗余 Paper_TODO 指针已归档；正式计划入口是 [research/paper/Paper_TODO.md](../research/paper/Paper_TODO.md)。本仓库不复制论文计划或自行修改 Go/No-Go 判断。
