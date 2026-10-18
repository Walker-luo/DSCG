# 完整任务测试：AgentDojo 与 AgentDyn

同一份代码在两个conda环境中自动选择基准，正常测试不需要`--benchmark`或额外工具目录参数。模型/风险配置见 [配置指南](./model_tool_configuration.md)，小规模排错见 [partial](./partial_benchmark.md)。

## 安装与依赖自检

在DSCG目录首次创建所需环境；已有环境不覆盖：

```bash
conda env create -f environment.yml
conda env create -f environment-agentdyn.yml
```

任选一个环境，后续测试命令完全相同：

```bash
conda activate ipi                      # AgentDojo
# 或：conda activate ipi-agentdyn         # AgentDyn
python -m dscg.benchmark_catalog
```

| 环境 | 实际后端身份 | 默认场景 |
| --- | --- | --- |
| ipi | 官方AgentDojo0.1.35发行包，suitev1.2 | workspace/travel/banking/slack |
| ipi-agentdyn | AgentDyn提交5353cf7615b135cace8d07c8f12dac53a16b6db3，suitev1.2 | shopping/github/dailylife |

两个包都声明agentdojo0.1.35，不能只看版本或环境名。当前按实际加载路径、安装来源、版本和固定revision自动识别；未知来源、错误revision、包路径冲突或不支持的场景在模型创建前拒绝。运行时不遍历后端源码、不计算源码哈希。两份lock保留历史哈希及发行元数据，当前只读取元数据；不是完整依赖锁。

当前记录`verification_mode=metadata_only`、`runtime_variant=unverified`。不再验证官方源码与本地system角色适配的逐字节差异；同轮baseline/DSCG仍应使用相同安装环境。远端模型真实修订和服务表现需实际测试。

模型配置及Key继续使用本地文件/环境变量，不覆盖已有配置。工具目录按当前后端自动选择，显式参数/环境覆盖、基准专用local目录仍可使用；当前通用tools.local是AgentDojo内置目录的相同副本，在AgentDyn自动选用对应内置目录并给出提示。未知自定义通用目录报错，不悄悄忽略。细则见配置指南；baseline不使用防御风险目录。

<a id="进程并发提速"></a>

## 顺序执行与准备信息

主模型、授权编译和审计默认使用 Qwen3.7-Flash，显式关闭思考；本地配置、环境变量和显式参数仍可覆盖。配置方法见[模型指南](./model_tool_configuration.md#24-最小可运行配置与角色复用)。

full、partial和cohort均按攻击、场景顺序执行，已删除workers参数及进程并发。旧命令需去掉该参数。准备阶段静默核对完整任务范围与已有配置绑定，不创建pipeline或发起模型请求；启动一次打印模型、后端、攻击、场景、结果目录和缓存策略，每组再打印任务数与开始/完成状态。原生任务对话、错误和必要警告继续输出。

```bash
python -m experiments.run_benchmark --baseline --force-rerun \
  --model-config config/models.local.toml --name qwen37_full_baseline_01

python -m experiments.run_benchmark --force-rerun \
  --model-config config/models.local.toml --name qwen37_full_dscg_01
```

每个目标型攻击/场景分组仍先执行原生GOAL预检，再执行用户×注入目标组合；一次任务通常包含多次模型/工具交互，DSCG还包括授权和审计。减小本地准备开销不保证Qwen服务响应加快，也不享受官方Batch折扣。

同目录运行锁防止重复写入。`attack_manifest.json.execution`与`execution/<本次ID>/execution.json`记录serial、组状态及wall_seconds；历史并发记录保持原样。失败组单列，其他组继续；中断保留原生结果，使用原参数加reuse恢复。API不再提供workers参数。

## 1. 使用哪个入口

| 入口 | 用户任务与目标 | 用途 |
| --- | --- | --- |
| `experiments.run_benchmark` | 所选场景全部注册用户任务与注入目标 | 正式完整任务对照 |
| `experiments.run_partial_benchmark` | 每场景注册顺序前3个用户、前3个注入目标 | 排错、成本较低的初步回归 |
| `experiments.run_injection_precheck screen` | 全部所选注入目标的直接GOAL | 可完成性预检与冻结cohort |

实际注册表如下，启动自检和manifest是执行范围的来源：

| 基准 / 场景 | 用户任务 | 注入目标 | 工具 | 每目标型攻击组合 |
| --- | ---: | ---: | ---: | ---: |
| AgentDojo workspace | 40 | 14 | 24 | 560 |
| AgentDojo travel | 20 | 7 | 28 | 140 |
| AgentDojo banking | 16 | 9 | 11 | 144 |
| AgentDojo slack | 21 | 5 | 11 | 105 |
| AgentDyn shopping | 20 | 9 | 39 | 180 |
| AgentDyn github | 20 | 9 | 34 | 180 |
| AgentDyn dailylife | 20 | 10 | 27 | 200 |

| 范围 | AgentDojo | AgentDyn |
| --- | ---: | ---: |
| full clean用户任务 | 97 | 60 |
| full目标总数 | 35 | 28 |
| full每目标型攻击组合 | 949 | 560 |
| full typical三攻击组合 | 2847 | 1680 |
| partial clean | 12 | 9 |
| partial typical三攻击组合 | 108 | 81 |

计划组合不是模型请求次数或有效分母；原生攻击GOAL预检另计。可用`--suites travel banking slack`选择AgentDojo子集，或`--suites shopping github`选择AgentDyn子集。跨后端场景名拒绝；full保留所选场景全部注册ID，不能用manifest缩小范围。

## 2. Clean 对照：先确认智能体能力

建议先做同轮无攻击对照，再做攻击测试。以下会真实调用模型，请自行在服务器启动；本轮工程验收没有执行它们。

```bash
python -m experiments.run_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name baseline_clean_01

python -m experiments.run_benchmark --clean --force-rerun \
  --model-config config/models.local.toml \
  --name dscg_clean_01
```

两组使用同一主模型、源码、环境、全部用户任务和执行限制；DSCG另用当前安全模型。按 `(suite_name, user_task_id)` 配对比较成功/失败、总Token与调用数，并分别报告错误、缺失任务。clean不构造攻击、不执行攻击GOAL预检，ASR/Defense Rate为null。不能把clean失败的任务从后续完整攻击分母中悄悄删掉。若另报可完成任务子集，应先冻结名单并同时保留完整分母结果。

原生预检warning主要针对 injection GOAL，不是全部用户任务的clean能力验证。模型拒绝、动态验证码操作失败和原生评分疑点需结合真实轨迹/终态分析；一次clean失败不证明任务永远不可完成。

## 攻击选择

```bash
python -m experiments.run_benchmark --baseline --attack typical --force-rerun \
  --model-config config/models.local.toml --name baseline_typical_01

python -m experiments.run_benchmark --attack typical --force-rerun \
  --model-config config/models.local.toml \
  --name dscg_typical_01
```

默认 `typical` 为 `ignore_previous`、`important_instructions`、`tool_knowledge`；`injecagent` 可显式选择，已经不在typical。具体攻击和 `all` 来自当前已验证后端的注册表，排除交互式 `manual`。预设不能与具体名字混用，typical缺项直接报错。例如：

```bash
python -m experiments.run_benchmark --baseline --attack important_instructions injecagent \
  --name baseline_explicit_01
```

两套后端按各自原生任务/工具循环评分。AgentDyn提供动态环境与新目标，攻击生成器仍有AgentDojo基线来源；安装成功不代表比旧攻击更强。`tool_knowledge` 使用上游参考调用，当前部分 shopping/github 注入目标的参考调用仍有占位或与GOAL不一致的内容，可能降低攻击质量或造成原生预检失败。本项目不补写标准答案或修改原生评分来追分，正式实验需保留并检查这些轨迹。

DoS按 `not utility` 单独计分，每用户仅使用首个注册目标一次；不可与目标型ASR合并。cohort测量拒绝DoS及包含DoS的all。全部自动攻击的实际名单和组合数以运行manifest为准，不固定论文数字。

## 预检与冻结 cohort

独立screen检查当前主模型直接完成注入GOAL的能力，与通过工具返回注入的攻击实验不同：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_01
```

在输出的实际目录找到 `cohort.json`，之后两组使用同一文件：

```bash
python -m experiments.run_benchmark --baseline --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name baseline_screened_01

python -m experiments.run_benchmark --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name dscg_screened_01
```

示例使用AgentDyn路径；AgentDojo输出路径中为agentdojo。使用当前环境实际生成的模型/运行目录，名单不能跨后端读取。screened保留全部所选用户任务，仅筛选目标；名单核对后端元数据、模型、任务ID、GOAL、筛选规则及证据哈希，源码变化本身不再阻止读取。细则见[预检指南](./injection_precheck.md)。

## 结果文件

CLI测量和screen在分类根目录下新增后端子目录，模型/运行名称中不再自动重复后端：

```text
results/partial_benchmark/agentdojo/qwen3.7-flash_baseline/
results/partial_benchmark/agentdyn/qwen3.7-flash_baseline/
results/benchmarks/agentdojo/qwen3.7-flash_baseline/
results/injection_precheck/agentdojo/qwen3.7-flash_injection_screen_01/
```

`--results-dir DIR`仍表示分类根，实际保存为`DIR/<backend>/<model>_<name>/`，不会自动判断DIR末尾是否已有后端名。未传name时保留原pipeline默认名称，去掉原先额外追加的后端后缀。Dashboard发起实验仍保存在原dashboard目录；历史页支持两种CLI布局，按实际路径分别展示。

默认根目录保持 `results/benchmarks/`，partial为 `results/partial_benchmark/`；新运行自动使用 `<benchmark_id>/<model_id>_<name>/`。内部布局：

```text
<run>/
  benchmark_plan.json 或 screened_run_manifest.json
  attack_manifest.json
  summary.json / summary.md / failure_cases.jsonl
  <attack>/<suite>/
    run_manifest.json / summary.json / summary.md
    <user_task>/<attack>/<injection_task>.json
```

clean使用 `none/<suite>/<user_task>/none/none.json`。原生JSON与full trace压缩侧车保留；`summary.md`便于阅读，JSONL按原路径定位失败，片段只是排查线索。缺失/非布尔安全标签、API/运行错误单列，不能当成攻击失败或防御成功；中断任务不能补造标签。计分分母和错误数必须一起报告。

manifest、cohort、summary和导出记录`benchmark`的id、repository、revision、suite_version、package_version、source_kind及`verification_mode=metadata_only`。新结果不生成后端实现/目录/组件源码哈希，也不认证runtime_variant。模型公开请求配置、完整任务集合、攻击、工具元数据内容及有效防御设置仍绑定；不同后端或任务集合不能合并分母。旧记录中的哈希保留，缺少必要身份的历史目录不能推断补齐。

成本核对主模型、安全模型、合计Token和调用次数；攻击目标预检与独立screen成本分别注明，不能重复累加。缓存复用后不等于一次完整新鲜测量；检查 `cost_scope`、`invocation_cost`、`cost_comparison_ready`，缺少usage保留未知。

## 显式续跑示例

使用相同name、根目录、模型与全部防御控制，去掉force-rerun、加reuse：

```bash
python -m experiments.run_benchmark --reuse --baseline \
  --model-config config/models.local.toml --name baseline_typical_01

python -m experiments.run_benchmark --reuse \
  --model-config config/models.local.toml \
  --name dscg_typical_01
```

未指定attack/suites时恢复原运行的完整计划；显式提供必须一致。clean仍需clean，screened仍需同一cohort。reuse与force-rerun或离线manifest导出互斥，并覆盖DSCG_FORCE_RERUN。新旧运行均按后端来源/版本、模型公开请求配置、完整任务ID、攻击/场景、cohort、工具元数据内容及有效防御配置核对；源码哈希、Git commit、Python补丁版本和旧并发设置不作为续跑门槛。缺少必要绑定或原范围不能核验时拒绝，不补造身份。

原生接受的成功、失败及错误缓存不会自动重试；reuse只补跑缺失或原生不完整任务，不恢复单个工具动作。更新汇总前保存快照，需要替换的不完整轨迹先保留原字节。旧run/cohort/attempt绑定不改写；规则变化另存configuration_only记录，明确source_equivalence_verified=false。配置一致续跑并不证明源码等价，正式比较仍需自行保持代码与环境一致。

退出0表示流程正常结束，不表示任务全成功或安全验收通过；退出1表示配置/执行/攻击异常，错误保留并继续可执行的后续攻击；退出2常为CLI参数错误。

新旧目录续跑：`--reuse`先定位新`<backend>/<model>_<name>/`；仅在新路径不存在时查找原`<model>_<backend>_<name>/`，并在旧目录原地续跑。新路径存在但绑定不完整/配置不符时直接拒绝，不回退；两者同时存在时优先新目录。不传reuse的测量只定位新结构并使用其中的原生缓存。原结果不移动，旧cohort/轨迹引用不改写。

## cohort 或续跑校验失败

来源/revision、模型、任务、GOAL或防御配置冲突不等于模型配置文件缺失。先核对实际Python与包路径、安装来源、模型公开配置、工具目录和原防御参数；cohort文件/轨迹哈希不符仍拒绝。当前已取消源码兼容映射检查，不需要为单纯源码变化修改映射或manifest。CLI路由解析器保留default=None，按profile解析shadow/off。

## 可选控制与日志

| 参数 | 说明 |
| --- | --- |
| `--baseline` | 原生AgentDyn工具循环，无DSCG与安全模型 |
| `--clean` | 无攻击用户任务效用对照 |
| `--suites NAME [NAME ...]` | 默认当前基准全部场景；full全部注册ID，partial前3×3 |
| `--attack NAME [NAME ...]` | 默认typical，可重复指定；all查询固定注册表 |
| `--cohort PATH` | 冻结筛选名单，不能与clean/task manifest混用 |
| `--name NAME` / `--results-dir DIR` | 独立运行名和结果根目录 |
| `--force-rerun` / `--reuse` | 重跑/续跑，均保留身份检查 |
| `--model-config PATH` / `--tool-metadata PATH` | 模型配置/已审查工具目录 |
| `--no-checker` | 关闭L3的消融，保留授权/Monitor/ticket，不是baseline |
| `--no-tool-view` / `--no-delegated-tasks` | L2展示/有限委托消融 |
| `--l1-projection-mode off/shadow/projected` | 默认projected；AgentDojo保留银行有限profile，AgentDyn沿用完整来源封装 |
| `--audit-router-mode off/shadow/selective` | DSCG CLI默认shadow；baseline/NoChecker默认off；shadow不新增免审 |
| `--audit-router-artifact PATH` | 单独校准的冻结artifact；旧基准/输入绑定不兼容时不可复用 |
| `--audit-retries 0/1` / `--completion-prompt` | 当前默认0/关闭，常规对照不叠加恢复 |
| `--trace-level summary/standard/full` | 默认summary；full增加序列化/压缩/写盘成本 |
| `--task-manifest PATH` / `--write-task-manifest PATH` | 导入/离线导出任务ID；full不能缩小范围 |

Python factory/API原有router默认off保持；网页以有效配置为准。不要把router off当作关闭L3。具体默认及字段见 [配置指南](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

不调用模型的目录导出：

```bash
python -m experiments.run_benchmark --write-task-manifest \
  workshop/artifacts/20261018_dual_local_check/full_tasks.json
```

Agent临时检查必须使用新 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/benchmarks`，不写用户正式results。新环境的 `browse_webpage` 可执行带副作用的handler，OTP验证也可恢复待执行写入，因此不进入读取免审。工具级框架仍不能单独授权内部handler或硬约束参数/对象；没有新增免审或安全保证。

## 指标与证据

TSR使用原生utility，ASR使用原生injection predicate，保留原始标签与轨迹；错误/缺失单列。汇报完整任务分母、有效标签分母及配对得失，不只平均各场景百分比。独立终态核查、重复对照和攻击强度仍需真实实验。本轮 [双基准报告](../workshop/completed/dual_benchmark_20261018.md) 只证明工程接线及离线模拟；没有付费模型评测，也不宣布E0通过或TSR/ASR收益。
