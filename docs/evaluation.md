# 测试文件与入口索引

从这里选择测试方式，具体运行命令由对应指南维护。所有命令从 `DSCG/` 执行：激活 `ipi` 使用AgentDojo，激活 `ipi-agentdyn` 使用AgentDyn。两个环境使用相同入口，按实际导入路径、安装来源、版本和revision识别后端，不根据环境名称猜测，也不合并两套场景。

```bash
conda activate ipi              # 或 conda activate ipi-agentdyn
python -m dscg.benchmark_catalog
```

最后一条命令只检查安装来源、版本、revision、实际导入路径并列出场景，不调用模型。首次安装分别使用[environment.yml](../environment.yml)或[environment-agentdyn.yml](../environment-agentdyn.yml)。两者沿用agentdojo导入名及0.1.35版本；当前verification_mode=metadata_only、runtime_variant=unverified，不扫描源码或认证客户端变体。未知来源、错误revision/路径及跨后端场景仍拒绝。旧运行配置一致可续跑，冻结cohort测量只验证名单自身摘要和模型/环境/所选任务；screen续跑仍验证原预检证据。

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
| [agentdyn_zero_rates.py](../experiments/diagnostics/agentdyn_zero_rates.py) | 只读分析已有AgentDyn攻击运行：原生标签、参考工具授权差集、阻断、错误、直接GOAL预检和注入文本在工具返回中的精确重合；输出必须使用新的目录 |
| [generate_tool_metadata.py](../experiments/tools/generate_tool_metadata.py) | 离线检查/导出注册工具风险目录，不调用模型 |

两测量入口默认运行当前后端的全部场景，`--suites`只能选择该后端子集。当前native v1.2目录如下，实际运行仍以目录和任务清单为准：

| 后端/环境 | 场景：用户/注入目标/工具 | Full clean / 每个targeted攻击网格 / typical三攻击 | Partial clean / typical三攻击 |
| --- | --- | --- | --- |
| AgentDojo / ipi | workspace40/14/24、travel20/7/28、banking16/9/11、slack21/5/11；69个不同工具名 | 97 / 949 / 2847 | 12 / 108 |
| AgentDyn / ipi-agentdyn | shopping20/9/39、github20/9/34、dailylife20/10/27；65个不同工具名 | 60 / 560 / 1680 | 9 / 81 |

这些是计划任务组合数，不是有效效用/安全分母或API请求数。Partial仍保留每场景注册顺序前3用户×前3目标。DSCG CLI默认shadow，baseline/NoChecker自动off（显式不兼容组合报错），API/factory默认仍off；baseline选对应后端原生无防御循环，clean选无攻击用户效用控制。其他工具见 [实验工具索引](../experiments/README.md)。

正常命令无需`--tool-metadata`：目录按显式路径、环境变量、后端专用local、可归属的通用local、后端内置顺序选择。当前通用`config/tools.local.toml`完整匹配AgentDojo审核目录，AgentDojo使用它，AgentDyn会提示跳过并自动使用自己的内置目录，原文件不变。无法归属的自定义通用目录会报错，需明确选择；baseline不加载防御风险目录。详见 [配置指南](./model_tool_configuration.md#41-加载位置)。

## 配置文件

| 文件 | 用途 |
| --- | --- |
| [models.example.toml](../config/models.example.toml) | 模型配置模板；复制为本地models.local.toml后配置服务。Key保留在本地/环境变量，不写公开报告 |
| [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml)、[tools.agentdyn-v1.2.toml](../config/tools.agentdyn-v1.2.toml) | 各后端独立审核目录，不合并、不自动推断副作用 |
| [agentdojo.lock.json](../config/agentdojo.lock.json)、[agentdyn.lock.json](../config/agentdyn.lock.json) | 保留发行/安装来源、revision与历史源码哈希；当前只使用安装元数据，不扫描源码 |
| 显式任务清单 | write-task-manifest离线导出，用于核对/冻结任务ID，不等同于能力预检名单 |
| cohort.json | screen生成的不可覆盖名单；包含模型/任务身份、筛选结论和证据哈希，不手工修改 |

## 预检与测量结果文件

| 文件 | 看什么 |
| --- | --- |
| 预检目录的screen_manifest.json、status.json、summary.md | 配置绑定、逐目标尝试、通过/失败/未决及成本记录 |
| 预检目录的attempts/及cohort.json | 直接GOAL轨迹、结果证据和冻结名单；错误不当作能力失败 |
| 测量目录的benchmark_plan.json、attack_manifest.json、suite_manifest.json | 攻击、场景及范围绑定；suite_manifest用于普通full/partial及partial筛选，full筛选由screened_run_manifest绑定 |
| 测量目录的summary.md、l3_router_summary.md/json | 各攻击/场景的完成情况、TSR/ASR分母与模型Tokens，以及L3路由/校准与完整性；[结果指南](./result_files.md) |
| 测量目录的failure_cases.jsonl | 用户计分任务中的效用失败、攻击成功、缺失/错误与轨迹位置；片段不是原因证明 |
| 场景内的run_manifest.json、summary.json、detailed_results.csv | 实际用户/注入ID、模型和防御配置、参考Git版本、计数与成本范围 |
| 原始任务JSON与full日志侧车 | 模型/工具交互、原生评分；路由与有界审计输入供复核，侧车仅详细日志时写入 |
| 筛选测量的screened_run_manifest.json、screened_cohort.json、preflight_report.json | cohort身份、实际选择/跳过集合、分母和未计分原生预检记录 |

CLI测量目录为`results/{partial_benchmark,benchmarks}/<backend>/<model>_<name>/`，screen为`results/injection_precheck/<backend>/<model>_<name>/`。原扁平运行目录保留并支持续跑，历史页不合并新旧路径。

显式reuse的原汇总/不完整轨迹快照和兼容依据在测量目录的reuse子目录；参数规则见两份运行指南。

同名文件按所属阶段区分含义。先确认task_scope、suite_scope与实际ID，再比较计分和成本；计划数不等于有效样本数。用户结果留在results，agent临时检查使用新的workshop/artifacts任务目录。布局与字段详解见两份运行指南，不修改历史实验文件。

AgentDyn动作具有动态副作用：`browse_webpage`/`input_to_webpage`可以派发修改、外发或付款handler，OTP验证可执行排队动作；下载会写文件，未读邮件读取会标记已读。工具级风险目录使这些动作接受相应授权/审计，但不提供参数、对象、收件人或数据来源约束。后端切换与离线通过不等于真实E0通过，也不改变I3 partial或其他研究闸门。
