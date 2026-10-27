# 完整任务测试：AgentDojo与AgentDyn

当前默认 **DSCG_v3.5.3／static-task-v352**。单次授权对照用 `--prompt-profile legacy`；`--name`只命名实验。框架见[README](../README.md)，模型／工具／profile见[配置指南](model_tool_configuration.md)。本页命令除自检／清单导出外均会调用真实模型。

<a id="默认-v32-策略与复测"></a>
<a id="默认-v33-策略与复测"></a>
<a id="默认-v34-策略与复测"></a>

## 默认v3.5.3与显式对照

默认L2先提取静态任务视图，再编译全局工具权限并冻结。v3.5.3改进请求字段、独立推荐、费用口径及真实执行状态提示，static共享编号／读取对照；L1、免审、Monitor和原生评分保留。普通动作任务通常比legacy多1次main调用，无条件验证、完成保证或自动扩权。

```bash
# 所选AgentDojo场景全部注册任务；使用新名称
python -m experiments.run_benchmark --suites banking slack \
  --prompt-profile legacy --name v353_legacy_01 --progress
python -m experiments.run_benchmark --suites banking slack \
  --prompt-profile static-task-v352 --name v353_static_01 --progress
```

两命令只相差profile，仍需同模型、攻击／cohort及有效配置配对。static支持NoL2／NoChecker消融（非off路由仍需L2／L3）；baseline仅legacy，其他历史候选仍要求L2／L3；历史候选见[诊断指南](qwen_utility.md)。

## 安装与依赖自检

首次安装见[README](../README.md#安装与配置)，已有环境不覆盖。在项目根执行：

```bash
conda activate ipi              # 或 ipi-agentdyn
python -m dscg.benchmark_catalog
```

AgentDojo为0.1.35／v1.2；AgentDyn同样导入agentdojo，固定revision `5353cf7615b135cace8d07c8f12dac53a16b6db3`。识别实际安装来源、路径、版本和revision，不按环境名猜测、不扫描源码。当前metadata-only，不认证服务／源码等价性。工具目录自动匹配，无需后端flag。

## 1. 使用哪个入口

| 入口 | 范围 |
| --- | --- |
| `experiments.run_benchmark` | 所选场景全部注册用户×全部注入目标 |
| `experiments.run_partial_benchmark` | 每场景注册前3用户×前3目标，见[partial](partial_benchmark.md) |
| `experiments.run_injection_precheck screen` | 每注入目标一次直接GOAL，见[预检](injection_precheck.md) |

| 后端／场景 | 用户 | 注入目标 | 工具 |
| --- | ---: | ---: | ---: |
| AgentDojo workspace | 40 | 14 | 24 |
| AgentDojo travel | 20 | 7 | 28 |
| AgentDojo banking | 16 | 9 | 11 |
| AgentDojo slack | 21 | 5 | 11 |
| AgentDyn shopping | 20 | 9 | 39 |
| AgentDyn github | 20 | 9 | 34 |
| AgentDyn dailylife | 20 | 10 | 27 |

| 计划范围 | AgentDojo | AgentDyn |
| --- | ---: | ---: |
| full clean | 97 | 60 |
| full每种目标型攻击／typical三攻击 | 949／2847 | 560／1680 |
| partial clean／typical | 12／108 | 9／81 |

计划数不是有效分母或API调用数，原生GOAL预检另计。AgentDyn `tool_knowledge × dailylife`参考调用缺placeholder_args，当前不支持：full跳过200、typical可执行1480；partial跳过9、可执行72，不进入效用／安全分母。实际范围以manifest为准。

`--suites`仅选当前后端场景子集。full保留全部注册ID，task manifest不能缩小范围；cohort只过滤注入目标。

## 2. Clean 对照：先确认智能体能力

```bash
python -m experiments.run_benchmark --baseline --clean --name baseline_clean_01 --progress
python -m experiments.run_benchmark --clean --name v353_clean_01 --progress
```

两组同环境、主模型、任务和限制。baseline使用原生无防御循环；clean不注入、不做攻击GOAL预检，ASR不适用。保留失败和错误，不因clean失败悄悄删减攻击分母。

## 攻击选择

```bash
python -m experiments.run_benchmark --baseline --attack typical --name baseline_typical_01 --progress
python -m experiments.run_benchmark --attack typical --name v353_typical_01 --progress
```

默认typical为ignore_previous、important_instructions、tool_knowledge。可用 `--attack NAME [NAME ...]`，injecagent需显式选择；all读取当前后端自动攻击注册表并排除manual。预设不能与具体攻击混用。DoS按not utility单独评分，每用户仅首个目标，不与目标型ASR合并。

## 预检与冻结cohort

按[预检指南](injection_precheck.md)生成名单，两臂使用同一份：

```bash
python -m experiments.run_benchmark --baseline --suites banking slack --attack typical \
  --cohort /absolute/path/to/cohort.json --name baseline_screened_01
python -m experiments.run_benchmark --suites banking slack --attack typical \
  --cohort /absolute/path/to/cohort.json --name v353_screened_01
```

full保留全部所选用户，只筛目标，结果标screened。名单仅覆盖子集时须明确suites；不能与clean／task manifest混用，拒绝DoS及含DoS的all。测量读取cohort不重验原screen轨迹，但实际测量缓存仍严格绑定有效配置。

<a id="进程并发提速"></a>
<a id="顺序执行与准备信息"></a>

## 按攻击并行与准备信息

多个攻击各用独立spawn进程，攻击内依次执行场景、原生GOAL预检和计分任务；单攻击／clean顺序执行。screen保持顺序。不新增并发flag或自动限流；不是官方Batch折扣。

准备阶段先核对配置／范围，主进程统一显示状态；`--progress`只控制显示，不影响身份或缓存。GOAL与计分进度分开，100%表示尝试结束，不等于全部有效或成功。错误组单列，其余可执行组继续；运行锁与execution记录保留。

## 结果文件

默认 `results/benchmarks/<backend>/<model>_<name>/`；partial根为results/partial_benchmark。`--results-dir DIR`仍会追加后端／运行层级。根 `summary.md`、`failure_cases.jsonl`、`l3_router_summary.md/json`是查阅入口，原生JSON／CSV／manifest保留。详见[结果文件](result_files.md)。

agent临时测量显式使用新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/benchmarks`，不写用户正式结果目录。

<a id="cohort-或续跑校验失败"></a>

## 显式续跑示例

```bash
python -m experiments.run_benchmark --reuse --name v353_typical_01
```

保留原name、输出根、模型、攻击／场景、cohort和全部有效防御配置。未指定攻击／场景时恢复原计划；clean仍加clean，baseline仍加baseline，cohort仍需同一名单。reuse与force-rerun互斥；策略更新用新名称，force-rerun不绕过绑定。

续跑核对后端、完整模型请求配置、任务ID、攻击、工具目录内容和有效防御设置；Git commit／源码哈希／Python补丁版本不作为兼容门槛，也不证明源码等价。先快照旧汇总和需替换的不完整轨迹；原生接受的完整错误缓存不会自动重试。

新路径优先，只有其不存在时才查原扁平路径并原地续跑；配置不符不回退、不覆盖旧绑定。退出0表示流程正常结束，退出1表示配置／执行错误或全部不支持，退出2通常是参数错误。

## 工具参数 JSON 解析错误

CLI full／partial／cohort中，主模型工具参数JSON语法错误终止当前任务，整批不执行，后续任务继续。不修补、不自动重发、不补造原生标签；该例按基础设施错误排除TSR／ASR有效分母。GOAL预检错误另计，有错误仍退出1。

`task_errors.jsonl`保存安全错误码、位置、长度及结束原因，不存参数正文。其他JSON异常沿用原路径。screen／Dashboard不在该CLI隔离范围。API已返回的Token仍计费；详见[错误记录](result_files.md#工具参数错误记录)。

## 可选控制与日志

L2授权编译失败的控制台消息包含 `suite`、`stage`、`user_task_id`、`injection_task_id` 和安全错误码。正式计分阶段为 `scored_task`，可直接定位用户／注入任务对。GOAL预检将注入目标单独当作用户请求执行，此时显示 `stage=goal_preflight user_task_id=none injection_task_id=...`；预检失败／错误警告逐个列出目标，不对应某个普通用户任务。clean显示 `injection_task_id=none`。直接pipeline调用若缺少任务上下文，明确显示 `unknown`。

| 参数 | 用途 |
| --- | --- |
| `--model-config PATH`／`--tool-metadata PATH` | 模型连接／审核风险目录 |
| `--prompt-profile legacy/static-task-v352` | 选择单次授权对照／当前两阶段默认，其他profile见诊断指南 |
| `--name`／`--results-dir` | 运行名称／分类输出根 |
| `--no-checker` | 关闭整个L3，仍保留L2／Monitor，不是baseline |
| `--no-tool-view`／`--no-delegated-tasks` | 关闭授权工具展示／有限委托 |
| `--l1-projection-mode off/shadow/projected` | CLI默认off；factory/API默认projected，off仍保留来源封装 |
| `--audit-router-mode off/shadow/selective` | CLI默认shadow，baseline／NoChecker默认off；均有固定读取免审 |
| `--audit-router-threshold`／`--audit-router-artifact` | 前者仅诊断，后者已停用，非空拒绝 |
| `--audit-retries 0/1`／`--completion-prompt` | 默认0／关闭，普通比较不叠加 |
| `--trace-level summary/standard/full` | 默认summary，控制诊断详细度 |
| `--task-manifest`／`--write-task-manifest` | 导入／离线导出任务ID，full不可缩小范围 |

离线导出示例：

```bash
python -m experiments.run_benchmark --write-task-manifest \
  "workshop/artifacts/<YYYYMMDD>_<task>/full_tasks.json"
```

<a id="l3直接阈值策略2026-10-21"></a>

## L3读取路由

当前为sink-free-read-v4，三模式均固定免审授权、schema有效的无sink public/internal读取，其他调用仍审计。**router off不是关闭L3，shadow也不代表所有读取均会审计。** 阈值不决定免审，旧artifact不再输入。完整规则及工具级隐私限制见[配置](model_tool_configuration.md#l3读取路由)。

## 指标与证据

TSR／ASR使用原生utility／security，按有效标签加权，错误、缺失、unsupported和GOAL分开。报告实际ID、有效分母、配对得失与成本范围；不平均场景百分比或把缺失补成零。独立screen与原生GOAL成本不能重复累计；检查invocation、缓存和整轮成本，缺usage保持未知。

同键结果也不自动证明模型服务、注入投递与oracle等价；当前遗留问题见[交接](framework_updates.md)。离线／小样本不等于一般安全或E0通过。
