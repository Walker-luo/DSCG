# v3.7 完整任务测试

默认 `static-task-v354 / DSCG_v3.7`，普通测试无需传 profile；`--name` 只命名实验。命令从项目根执行，除自检／清单导出外均会调用真实模型。模型与防御默认值见 [配置](model_tool_configuration.md)。

## 安装与范围

工作站使用 ipi，服务器使用 DSCG；先运行 `python -m dscg.benchmark_catalog` 核对实际后端。当前实验范围为 AgentDojo 0.1.35 / v1.2。

| AgentDojo 场景 | 用户 | 注入目标 | 工具 |
| --- | ---: | ---: | ---: |
| workspace | 40 | 14 | 24 |
| travel | 20 | 7 | 28 |
| banking | 16 | 9 | 11 |
| slack | 21 | 5 | 11 |

`run_benchmark` 取所选场景全部注册用户和目标，`--suites` 可选完整场景子集。全场景 clean 计划 97 例，未筛选攻击每种计划 949 例，typical 三攻击合计 2847 例。计划数不是有效分母或 API 次数。partial 只取注册前缀，见 [小批量测试](partial_benchmark.md)。

代码保留 AgentDyn 后端适配，实际场景以安装识别为准；当前测试约定不启动 AgentDyn。任务 manifest 不能缩小 full 用户范围，fliter 仅排除注入目标。

## Clean 对照

以下示例使用 workshop 输出根，每次先选未使用的运行名。

```bash
python -m experiments.run_benchmark --baseline --clean \
  --results-dir results/workshop --name baseline_doc01_clean --progress
python -m experiments.run_benchmark --clean \
  --results-dir results/workshop --name v3.7_doc01_clean --progress
```

baseline 使用原生循环，v3.7 使用三层防御。两组保持相同主模型和任务范围，clean 不注入、不预检 GOAL，ASR 不适用。clean 失败应保留在报告中。

## 攻击与冻结名单

先按 [筛选指南](injection_precheck.md) 生成同模型 fliter.json，再给两组复用相同名单。

```bash
python -m experiments.run_benchmark --baseline --attack typical \
  --fliter /absolute/path/to/fliter.json \
  --results-dir results/workshop --name baseline_doc01 --progress
python -m experiments.run_benchmark --attack typical \
  --fliter /absolute/path/to/fliter.json \
  --results-dir results/workshop --name v3.7_doc01 --progress
```

typical 默认为 ignore_previous、important_instructions、tool_knowledge。`--attack NAME [NAME ...]` 可显式指定，all 读取注册表并排除 manual，预设不与具体名称混用。DoS 单独按 not utility 评分，每用户仅首个目标，不与目标型 ASR 合并。

## 目标排除与可选 GOAL

| 参数 | 行为 |
| --- | --- |
| 都不传 | 按 full／partial 原范围直接计分 |
| 仅 `--fliter PATH` | 按名单排除目标后计分 |
| 仅 `--goal` | 当前测量框架逐目标预检，仅通过者计分 |
| 两者都传 | 先排除名单目标，再预检剩余目标 |

拼写固定为 fliter。名单读取一次，校验后端／版本／场景／任务 ID；未列场景不排除。Python 入口为 `fliter_path`、`goal=False`。旧 `--cohort` 和旧 cohort 文件输入被拒绝。

测量 GOAL 每目标只运行一条完整原生轨迹，使用当前测量 pipeline，结果跨攻击共享。失败排除，错误跳过并导致非零退出，中断保存进度；续跑不重试已开始目标。GOAL 成本单列，不进入 TSR／ASR。全被筛除时指标为 N/A。不同防御的 GOAL 可能生成不同计分集合，比较时使用实际共同任务键。clean／DoS 不接受 fliter 或 goal。

<a id="进程并发提速"></a>
<a id="顺序执行与准备信息"></a>

## 按攻击并行与进度

多个攻击使用独立进程，各攻击内部依次执行场景和任务；单攻击、clean 与 screen 顺序执行。可选 GOAL 先在父进程完成。父进程校验绑定并管理运行锁，子进程只写自己的攻击目录。

`--progress` 仅控制显示。100% 表示尝试结束，应另看有效／错误／未完成计数；错误组单列，其他可执行组继续。服务器同时最多三个模型调用进程。

## 结果文件

默认输出根为 results/benchmarks，显式 `--results-dir results/workshop` 后为 `results/workshop/<backend>/<model>/<name>/`。partial 默认根为 results/partial_benchmark。正式 workshop 测量指定前述输出根；agent 临时验证指定新建 workshop/artifacts 任务目录。

查阅根 summary.md、failure_cases.jsonl 和逐任务原生轨迹；根 run_manifest.json 绑定配置，summary.json 保存筛选／GOAL checkpoint 和汇总。完整路径及成本口径见 [结果文件](result_files.md)。

## 显式续跑示例

```bash
python -m experiments.run_benchmark --reuse --name v3.7_doc01 \
  --fliter /absolute/path/to/fliter.json --results-dir results/workshop
```

保留原 name、输出根、模型、fliter／goal 和有效防御设置；未指定攻击／场景时恢复原计划，baseline／clean 仍需对应参数。reuse 与 force-rerun 互斥，配置变化使用新名称。

续跑校验后端、完整有效配置、任务 ID、攻击、工具目录和筛选绑定，快照旧汇总及待替换的不完整轨迹。原生接受的完整错误缓存不会自动重试。Git 提交相同不证明模型服务或运行等价。

## 工具参数 JSON 解析错误

CLI full／partial 遇到主模型工具参数非法 JSON 时终止当前任务，整批不执行，后续任务继续。该例记录为基础设施错误，有效标签为空，GOAL 错误另计。`task_errors.jsonl` 保存安全错误码、位置和阶段，不保存参数正文；原生返回的已知 Token 仍计费。该 CLI 隔离不覆盖 screen／Dashboard 的全部异常路径。

## 可选控制与日志

| 参数 | 用途 |
| --- | --- |
| `--model-config PATH`／`--tool-metadata PATH` | 模型连接／风险目录 |
| `--name`／`--results-dir` | 新运行名称／结果根 |
| `--fliter PATH`／`--goal` | 排除表／可选当前框架 GOAL |
| `--no-checker` | NoL3，保留 L2 与 Monitor，默认 router off |
| `--no-sandbox --audit-router-mode off` | NoL2，关闭编译、前置、工具视图与委托；当前元数据缺失问题见下文 |
| `--no-tool-view`／`--no-delegated-tasks` | 单独关闭授权工具展示／有限委托 |
| `--prompt-profile legacy` | 显式单次授权对照，默认使用 static-task-v354 |
| `--l1-projection-mode off/shadow/projected` | CLI 默认 off，仍保留 L1 来源封装 |
| `--audit-router-mode off/shadow/selective` | CLI 默认 shadow，off 仍有 L3 |
| `--audit-retries 0/1`／`--completion-prompt` | 默认 0／关闭 |
| `--trace-level summary/standard/full` | 诊断详细度 |
| `--task-manifest`／`--write-task-manifest` | 导入或离线导出任务 ID，full 不缩小范围 |

控制台区分 scored_task／goal_preflight，显示 suite、用户 ID、注入 ID 和安全错误码。NoL2 当前存在元数据初始化耦合，解释该消融前先看 [当前问题](framework_updates.md)。

## L3 读取路由

固定规则为 sink-free-read-v4。已注册、授权、schema 有效的无 sink public/internal 读取免审，其他动作继续审计。router off 不关闭 L3，阈值不控制固定免审范围，artifact 参数已停用。机制见 [架构](architecture.md#l3-判断这次调用是否符合任务)。

## 指标与证据

TSR／ASR 按原生有效标签加权计算，错误、缺失、不支持和 GOAL 分开。成本同时核对 main、security、GOAL、计分任务、本次调用与缓存／整轮范围；未知 usage 保持未知。退出 0 表示流程正常结束，退出 1 表示执行／配置等错误，参数错误通常为 2。

同键比较仍需核对筛选、实际注入和配置。少量计分任务、组件回复或离线回归均不能证明一般安全性，效用分析见 [诊断指南](qwen_utility.md)。
