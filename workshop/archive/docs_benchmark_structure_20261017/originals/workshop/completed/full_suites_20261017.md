# Full benchmark 场景选择

日期：2026-10-17。基准 revision：`e1f0772358cefb5756d30875f8e6f5d2d4ad16d8`，本次改动尚未提交。

两个测量CLI共用 `--suites workspace travel banking slack`；默认四场景不变。full选择场景后仍执行这些场景的全部注册用户和注入目标；partial保持原前三个用户×前三个目标。full的clean、离线清单导出与cohort均尊重场景选择。cohort保留所选场景全部用户及通过目标，原证据/名单不改写；不再因名单另有未选场景而强制扩大执行。显式缩小场景时名单须覆盖所选子集；旧部分场景cohort按默认入口读取的行为保持兼容。

ordinary full仍用 `task_scope=full` 表示所选场景内部完整，另记录 `suite_scope=selected` 和场景列表，并显示“所选场景全任务评测摘要”；实际执行四场景标记all_registered。不能把场景子集标为四场景正式评测。full根suite_manifest.json绑定整个场景集合，同名切到不相交集合也拒绝，force-rerun不覆盖。导入full清单仍不能缩小所选场景内任务ID。

源码兼容映射仅新增基准版本的完整已知身份，并绑定当前修改文件哈希；保持模型、任务/GOAL、筛选规则、原生评分和dscg代码检查。未知版本仍拒绝；新测量用新name。当前实验入口、用户数据/凭证和正式研究闸门不变。

## 验证

所有工程检查产物在 `workshop/artifacts/20261017_full_suites/`，修改前字节、源码身份和工作树见 before.json/originals；命令与文件/日志哈希见 validation.json。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_full_suites.py -v` | 0 | 4/4；实际注册ID完整执行、场景范围绑定/旧报告不变、clean、导出及非法参数 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_partial_cohort.py -k full_cli_suite_subset -v` | 0 | 1/1；四场景冻结名单只执行三场景，保留全部用户/通过目标 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 385/385；包括原full/partial/precheck回归和旧源码兼容 |
| `conda run -n ipi python -B -m experiments.run_benchmark --help` | 0 | 展示--suites，无模型请求 |
| `git diff --check` | 0 | 无空白错误 |

RED日志复现full CLI尚未提供--suites；GREEN模拟pipeline完整执行所选真实注册任务，不将它们缩成partial前缀。cohort模拟每场景4用户/3个保留目标，选3场景、1攻击，产生36条模拟计分结果；原名单字节不变。撤下旧的“full CLI必须拒绝--suites”测试，以新的完整任务执行契约替代。

新增真实模型请求0、真实benchmark样本0；计划数不是有效分母或费用节省结果。E0 pending、I3 partial、I2 locked及closed路线不变。历史cleanup/迁移清单保持原哈希，不用它们来认证本次新源码。

下一步：用户以相同场景集合和攻击选择，用新名称运行匹配baseline与DSCG；需要筛选目标时两组使用同一cohort。命令见 [全量指南](../../docs/full_benchmark.md#1-使用哪个入口)。
