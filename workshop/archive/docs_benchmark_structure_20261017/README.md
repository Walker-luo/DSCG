# 测试指南结构整理原文

本目录保存2026-10-17整理前的文档、相关CLI/测试/兼容映射字节，以及 [路径/哈希清单](./relocation_manifest.json)。原文位于originals下，保留当时的相对链接与命令上下文，不作为当前运行指南。

当前入口为 [测试文件索引](../../../docs/evaluation.md)、[完整任务测试](../../../docs/benchmark.md)和[小批量测试](../../../docs/partial_benchmark.md)。旧full_benchmark名称退出当前docs，不留兼容页；本次只更新当前可读文档及报告链接，不改写此前归档文件或原始实验结果。

工作区原已删除的V2兼容别名与I3报告不恢复。当前需要I3证据的链接指向已有研究交接；不重建被删除文件，不改变原研究状态。

执行期间用户另行确认CLI默认shadow：仅对full/partial DSCG CLI生效，baseline/NoChecker隐式off，显式不兼容模式报错。API/factory默认仍off。原始off版本按任务开始revision核对后归档；并行编辑的中间版本另在本次工程产物中记录。兼容映射只允许明确已知来源用于直接GOAL预检，不允许用新默认值覆盖旧攻击测量身份。

历史归档与原始结果未移动，旧hash清单不因本次调整更新。当前验证与限制见 [整理报告](../../completed/docs_benchmark_structure_20261017.md)；不将历史迁移快照工具描述为已认证当前版本。
