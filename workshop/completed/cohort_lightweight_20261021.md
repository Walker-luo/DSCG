# 冻结 cohort 的轻量测量读取（2026-10-21）

full、partial及旧benchmark转发入口共用轻量名单读取：主模型仅比较model_id/provider；核对实际后端身份、具体包版本、suite版本、AgentDyn固定revision，以及所选场景的任务ID和注册顺序。cohort自身摘要仍校验一次，之后各攻击/场景复用内存名单。原预检目录可移动或缺失，不再读取attempt、轨迹或引用manifest，也不比较GOAL、重算筛选判定或检查序列化。旧adapter no-op分支及其专属测试已删除，原报告保留。

full保留所选场景全部用户；partial仍取原前三用户及原前三注入前缀交集，不补位。所选场景必须存在于名单和当前后端，空目标场景跳过，全部为空拒绝。full默认当前后端全部场景，子集名单需显式指定suites。reuse先恢复原场景，再校验相应子集。

新screened_cohort附件和本次execution记录写入cohort_validation，mode为model_backend_suites_v1、cohort_digest_verified=true、screening_evidence_verified=false。原绑定/名单/证据不改写。名单是可信输入，此读取不重新认证原预检结论；screen创建、续跑和历史证据复用仍采用原证据流程。实际测量缓存继续比较完整请求与防御配置，因此更换endpoint可使用原名单启动新实验，却不能复用不同endpoint的攻击缓存。

## 离线验证

证据根：[20261021_cohort_lightweight](../artifacts/20261021_cohort_lightweight/)。修改前原文在originals/，哈希见delivery_validation.json；初始代码revision和工作区状态见revision.txt，交付改动为未提交工作区差异。

| 命令 | 退出码 / 结果 |
| --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0；600 tests，9 skipped |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 0；604 tests，1 skipped |
| `conda run -n ipi python -B workshop/artifacts/20261021_cohort_lightweight/compare_validation.py` | 0；合成35目标、每模式5次 |
| `python workshop/artifacts/20261021_cohort_lightweight/validate_delivery.py` | 0；383份原预检文件哈希不变；无新增链接错误 |
| `git diff --check` | 0 |

完整测试日志为ipi_verified.log、agentdyn_verified.log。新增测试覆盖模型/provider与环境不匹配、请求设置变化、任务类型/重复/顺序、名单摘要损坏、只验证所选场景、空名单、full/partial范围、恢复原场景、一次文件读取和缓存配置隔离。原证据损坏不再阻止测量，但仍阻止screen续跑。

timing.json记录同一合成样本的中位校验耗时：旧流程约3.91ms，新流程约0.85ms；5次启动各读取cohort一次，旧流程额外打开证据350次（每目标哈希和JSON各一次），新流程为零。该结果仅描述离线本地校验，不预测服务器或模型耗时；未设置时间断言。

文档检查217处本地链接，README及已完成索引原有三处report/report.md目标缺失；修改前同样存在，本次未改写历史报告引用。当前指南、配置说明及AGENTS已同步新策略。

没有真实模型调用、原生评分变更或防御效果结论。下一步：服务器更新代码后，用原cohort及实际所选suites启动新名测量；若复用旧测量，仍须满足实际请求/防御配置绑定。
