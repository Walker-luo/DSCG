# DSCG 与 research 的交互入口

DSCG 维护工程实现、测试、使用说明和 workshop 材料；正式论文问题、创新判断、实验协议与投稿计划留在兄弟仓库 [research](../research/)。

研究任务从 [technical_route.md](../research/technical_route.md)读取，并跟随该文件的当前实现状态链接回报。本地实现及遗留问题见 [DV_STATE.md](DV_STATE.md)和[当前框架](docs/framework_updates.md)，不从旧交接推断当前机制或研究门槛。

| 范围 | 当前状态 |
| --- | --- |
| 工程框架 | DSCG_v3.5.3：L1规划视图、L2静态任务视图与工具授权、L3当前动作审计；Monitor／票据为执行基础设施 |
| E0 | 真实harness审计待完成，合成自检不代表过闸 |
| I3 | partial：24个有效探针、8个范围缺口，待研究侧复核 |
| I2 | 仍锁定；对象／数据／参数授权与已关闭provenance/source-to-sink路线不因工程更新解锁 |

研究驱动任务完成后，按研究侧当前状态文档记录revision、工作树、命令／退出码、产物哈希、样本分母、限制和下一步；不在DSCG复制论文计划或自行宣布新颖性。

工程计划与报告见 [workshop](workshop/README.md)。新agent产物放 `workshop/artifacts/<YYYYMMDD>_<task>/`，用户正式结果与导出保留在 `results/`、`download/`。规则见 [AGENTS.md](AGENTS.md)。
