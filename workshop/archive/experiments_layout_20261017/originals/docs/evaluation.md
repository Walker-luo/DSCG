# 测试文件与入口索引

从这里选择测试方式，具体运行命令由对应指南维护。所有命令从 `DSCG/` 执行，默认已激活 `ipi`。

## 测试指南

| 文件 | 什么时候使用 |
| --- | --- |
| [benchmark.md](./benchmark.md) | 使用run_benchmark，对所选场景运行全部注册任务；包含baseline/DSCG、clean、cohort、结果与续跑 |
| [partial_benchmark.md](./partial_benchmark.md) | 使用run_partial_benchmark优化框架；默认每场景前3用户×前3注入，支持场景与前缀内cohort筛选 |
| [injection_precheck.md](./injection_precheck.md) | 直接请求injection GOAL，复用/复测预检并冻结名单，处理未决与续跑 |
| [model_tool_configuration.md](./model_tool_configuration.md) | 配置主模型/安全模型、工具schema与风险目录，核对配置优先级和可选控制 |

full的cohort保留所选场景全部用户；partial的cohort只过滤原注入前缀，不补位。两种分母不同。公共[攻击表](./benchmark.md#攻击选择)、[参数](./benchmark.md#可选控制与日志)和[指标口径](./benchmark.md#指标与证据)统一在benchmark指南维护。

## 主要测试入口

| 文件 | 作用与输出 |
| --- | --- |
| [run_benchmark.py](../experiments/run_benchmark.py) | 完整任务测量；默认results/benchmarks，普通范围full、冻结目标范围screened |
| [run_partial_benchmark.py](../experiments/run_partial_benchmark.py) | 小批量测量；默认results/partial_benchmark，范围partial或partial_screened |
| [run_injection_precheck.py](../experiments/run_injection_precheck.py) | screen直接目标预检；默认results/injection_precheck，全部判定完成后生成cohort.json |
| [generate_tool_metadata.py](../experiments/generate_tool_metadata.py) | 离线检查/导出注册工具风险目录，不调用模型 |

两测量入口均支持suites、默认四场景；DSCG CLI默认shadow，baseline/NoChecker自动off（显式不兼容组合报错），API/factory默认仍off；baseline选原生无防御控制，clean选无攻击用户效用控制。其他审计/校准工具见 [实验工具索引](../experiments/README.md)，不在此逐一罗列共享实现与单元测试文件。

## 配置文件

| 文件 | 用途 |
| --- | --- |
| [models.example.toml](../config/models.example.toml) | 模型配置模板；复制为本地models.local.toml后配置服务。Key保留在本地/环境变量，不写公开报告 |
| [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml) | 内置工具风险目录；加载顺序与覆盖规则见配置指南 |
| 显式任务清单 | write-task-manifest离线导出，用于核对/冻结任务ID，不等同于能力预检名单 |
| cohort.json | screen生成的不可覆盖名单；包含模型/任务身份、筛选结论和证据哈希，不手工修改 |

## 预检与测量结果文件

| 文件 | 看什么 |
| --- | --- |
| 预检目录的screen_manifest.json、status.json、summary.md | 配置绑定、逐目标尝试、通过/失败/未决及成本记录 |
| 预检目录的attempts/及cohort.json | 直接GOAL轨迹、结果证据和冻结名单；错误不当作能力失败 |
| 测量目录的attack_manifest.json、suite_manifest.json | 攻击、场景及范围绑定；suite_manifest用于普通full/partial及partial筛选，full筛选由screened_run_manifest绑定 |
| 测量目录的summary.md、all_report.txt | 各攻击/场景的完成情况、TSR/ASR分母与模型Tokens |
| 测量目录的failure_cases.jsonl | 用户计分任务中的效用失败、攻击成功、缺失/错误与轨迹位置；片段不是原因证明 |
| 场景内的run_manifest.json、summary.json、detailed_results.csv | 实际用户/注入ID、模型/源码和防御配置、计数与成本范围 |
| 原始任务JSON与full日志侧车 | 模型/工具交互、原生评分；路由与有界审计输入供复核，侧车仅详细日志时写入 |
| 筛选测量的screened_run_manifest.json、screened_cohort.json、preflight_report.json | cohort身份、实际选择/跳过集合、分母和未计分原生预检记录 |

同名文件按所属阶段区分含义。先确认task_scope、suite_scope与实际ID，再比较计分和成本；计划数不等于有效样本数。用户结果留在results，agent临时检查使用新的workshop/artifacts任务目录。布局与字段详解见两份运行指南，不修改历史实验文件。
