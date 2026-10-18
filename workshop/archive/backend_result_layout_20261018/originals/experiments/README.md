# 实验工具索引

从DSCG目录执行，激活`ipi`使用AgentDojo，激活`ipi-agentdyn`使用AgentDyn。主目录只保留三个日常运行入口；相同命令按实际导入路径、安装来源/版本/revision选择后端，不根据环境名称猜测或混合两套场景。模型运行由用户显式启动。

环境配置分别为[environment.yml](../environment.yml)与[environment-agentdyn.yml](../environment-agentdyn.yml)。AgentDojo使用0.1.35发行版本，AgentDyn固定commit 5353cf7615b135cace8d07c8f12dac53a16b6db3。历史源码锁保留，当前运行只核对元数据，不扫描后端与工程源码哈希。可离线列出实际目录：

```bash
conda activate ipi              # 或 conda activate ipi-agentdyn
python -m dscg.benchmark_catalog
```

两个后端沿用agentdojo导入名及0.1.35发行版本，不能只凭版本号确认后端。metadata_only识别拒绝未知来源、错误revision或包路径；不认证源码内容和客户端变体。

## 日常测量

| 入口 | 用途 | 说明 |
| --- | --- | --- |
| `python -m experiments.run_injection_precheck screen` | 直接GOAL能力预检、恢复历史尝试、冻结injection名单 | [预检指南](../docs/injection_precheck.md) |
| `python -m experiments.run_partial_benchmark` | 默认每场景前三个用户×前三个注入 | [小批量指南](../docs/partial_benchmark.md) |
| `python -m experiments.run_benchmark` | 当前后端所选场景全部任务，或cohort冻结目标；默认该后端全部场景 | [完整任务指南](../docs/benchmark.md) |

两个测量入口默认当前后端全部场景：AgentDojo为workspace、travel、banking、slack，用户/目标/工具依次40/14/24、20/7/28、16/9/11、21/5/11（69个不同工具名）；AgentDyn为shopping、github、dailylife，依次20/9/39、20/9/34、20/10/27（65个不同工具名）。`--suites`只选择当前后端子集，如AgentDojo的workspace travel或AgentDyn的shopping github。目录来自运行时校验后的native v1.2注册表。

Full clean计划分别97/60，targeted网格每攻击949/560，typical三攻击2847/1680；partial clean12/9、typical108/81，仍按每场景注册前3用户×前3目标选择。这些是计划组合数，不是有效评分分母或API请求数。partial的cohort仅过滤原目标前缀、不补位，标记partial_screened；full保留全部用户，标记screened。DSCG CLI默认shadow，baseline/NoChecker默认off，API/factory仍off；typical为ignore_previous、important_instructions、tool_knowledge，injecagent保留显式/all选择。

正常命令无需工具目录flag。选择顺序为显式路径→DSCG_TOOL_METADATA→config/tools.<backend>.local.toml→语义完整匹配审核目录且归属当前后端的tools.local.toml→后端内置目录。当前通用local是AgentDojo副本，在AgentDyn下会提示跳过并自动选新内置目录，原文件不变；未知自定义通用local会报错，需明确选择。所选目录缺项在创建模型前拒绝，不合并分类或覆写文件。baseline使用对应后端原生循环，不加载防御风险目录；模型、路由和重试默认值不变。

## 目录分工

```text
experiments/
├── run_benchmark.py
├── run_partial_benchmark.py
├── run_injection_precheck.py
├── common/         # 任务选择、清单、报告、cohort与版本兼容
├── diagnostics/    # E0、I3与轨迹诊断；日常测量无需单独运行
├── calibration/    # L3独立标签数据与阈值校准
└── tools/          # 工具风险元数据检查与导出
```

| 模块 | 用途 |
| --- | --- |
| [common/partial_controls.py](./common/partial_controls.py) | full/partial任务选择、冻结清单、参考来源及缓存绑定 |
| [common/partial_reporting.py](./common/partial_reporting.py) | 测量报告、失败索引和成本统计 |
| [common/injection_cohort.py](./common/injection_cohort.py) | 冻结名单/轨迹证据校验、恢复/复用与筛选测量；历史兼容映射不参与运行 |
| [diagnostics/harness_audit.py](./diagnostics/harness_audit.py) | E0合成记录审计；也向runner/Dashboard提供原有评分辅助函数 |
| [diagnostics/i3_p0_stress.py](./diagnostics/i3_p0_stress.py) | I3状态/边界fixture；当前partial证据见 [研究交接](../../research/Experiments/implementation_status.md) |
| [diagnostics/trace_diagnostics.py](./diagnostics/trace_diagnostics.py) | 只读启发式轨迹标注，不改native评分，不作为独立安全oracle |
| [calibration/l3_router_dataset.py](./calibration/l3_router_dataset.py) | 从显式独立标注准备L3数据集 |
| [calibration/calibrate_l3_router.py](./calibration/calibrate_l3_router.py) | 使用独立分组数据生成冻结校准artifact |
| [tools/generate_tool_metadata.py](./tools/generate_tool_metadata.py) | 离线核对当前后端元数据和全工具覆盖；默认复制到config/tools.<backend>.local.toml，保护通用local和两份审核内置目录 |

## 专项工具用法

新模块路径示例：

```bash
python -m experiments.diagnostics.harness_audit --help
python -m experiments.diagnostics.i3_p0_stress --help
python -m experiments.calibration.l3_router_dataset --help
python -m experiments.calibration.calibrate_l3_router --help
python -m experiments.tools.generate_tool_metadata --help
```

专项工具按需使用；I3仍为partial，E0合成自检不等于真实E0通过。L3准备与校准方法见 [L3方案](../workshop/L3_checker_opt.md)，元数据用法见 [配置指南](../docs/model_tool_configuration.md)。

旧顶层专项模块不保留转发壳；历史报告中的旧命令保留当时上下文，复跑使用上述新路径。原始字节及路径/哈希映射见 [本次归档](../workshop/archive/experiments_layout_20261017/README.md)。先前移除的专用诊断/绘图代码仍在 [早期归档](../workshop/archive/experiments_docs_cleanup_20261017/README.md)，不恢复到当前目录。

full/partial/cohort按攻击、场景顺序执行，已删除workers和进程调度；准备静默核对配置，不创建pipeline。目录包含实际后端。旧运行配置一致可续跑，原manifest、attempt与cohort不改写；后端、模型、任务或有效防御配置变化仍拒绝。

用户实验仍默认写入results。Agent临时检查显式写入新的workshop/artifacts任务目录，不改写历史实验。

显式续跑：两入口支持`--reuse --name <原名称>`，省略attack/suites恢复原计划；与force-rerun互斥并覆盖环境强制设置。共享[续跑校验](./common/benchmark_reuse.py)按配置比较，不读取历史源码兼容映射。Git/Python版本仅供追溯；cohort/轨迹完整性仍校验哈希。见[公共续跑说明](../docs/benchmark.md#显式续跑示例)。

AgentDyn动态页面handler可修改、外发或付款，OTP验证可执行排队动作；下载写文件，未读邮件读取会标记已读。风险目录按真实实现分类，没有增加对象/参数/收件人约束或新的免审规则。没有新增L1 profile，AgentDyn三个场景使用完整来源隔离。离线接入检查不证明模型效用、安全提升或真实E0通过，I3仍partial。
