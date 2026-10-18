# 小批量测试：run_partial_benchmark

在 `DSCG/`、已激活 `ipi`（AgentDojo）或 `ipi-agentdyn`（AgentDyn）环境下执行。安装与依赖自检见 [全量指南](./benchmark.md#安装与依赖自检)，模型/工具配置见 [配置指南](./model_tool_configuration.md)。

## 默认任务范围

当前基准的全部场景，每场景取**注册顺序前3个用户任务×前3个注入目标**。AgentDojo四场景typical三攻击共计划108组合、clean12任务；AgentDyn三场景typical81组合、clean9任务。seed:7保留为元数据，不改变当前前缀顺序。计划组合不等于API调用次数或有效标签分母，攻击目标原生预检另计。

AgentDojo可用 `--suites travel banking slack` 选子集，此时clean9、typical81；AgentDyn可用 `--suites shopping github`，此时clean6、typical54。全量正式结果使用 `experiments.run_benchmark`，不是本入口。实际ID查看summary.task_selection或离线导出：

```bash
python -m experiments.run_partial_benchmark --write-task-manifest \
  workshop/artifacts/20261018_dual_local_check/partial_tasks.json
```

## 对照与输出

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun \
  --model-config config/models.local.toml --name partial_baseline_typical_01

python -m experiments.run_partial_benchmark --force-rerun \
  --model-config config/models.local.toml \
  --name partial_dscg_typical_01
```

baseline使用当前基准原生工具循环，不创建DSCG或安全模型。DSCG默认自动匹配已审查工具目录，切换环境不需要额外参数；自定义目录按配置指南覆盖。默认输出：

```text
results/partial_benchmark/<model_id>_<benchmark_id>_<name>/<attack>/<suite>/
```

根目录含攻击/执行计划、summary.md和failure_cases.jsonl；逐场景保留原生JSON、CSV及summary。错误、缺失与有效分母分别报告，不能把异常当成攻击失败或防御成功。格式、成本与续跑细节共用 [全量指南](./benchmark.md#结果文件)。

<a id="并发运行"></a>

## 顺序运行

主模型和审计模型默认Qwen3.7-Flash、关闭思考。按攻击、场景顺序执行，已删除workers参数。启动打印一次模型与范围；准备阶段静默核对绑定，每组执行时打印用户/目标数量及开始/完成状态。

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun \
  --model-config config/models.local.toml --name qwen37_baseline_01

python -m experiments.run_partial_benchmark --force-rerun \
  --model-config config/models.local.toml --name qwen37_dscg_01
```

默认每场景3×3任务范围不变；每个目标型攻击/场景组仍有额外原生GOAL预检。详见[顺序执行与准备信息](./benchmark.md#顺序执行与准备信息)。这不是官方Batch；减小本地开销不代表真实模型速度已经验证。

## 干净任务对照

```bash
python -m experiments.run_partial_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name partial_baseline_clean_01

python -m experiments.run_partial_benchmark --clean --force-rerun \
  --model-config config/models.local.toml \
  --name partial_dscg_clean_01
```

AgentDojo默认每组12、AgentDyn每组9用户任务，无攻击与GOAL预检，ASR/Defense Rate为null。按相同用户任务配对得失，不能把prefix结果作为97/60个完整用户任务的正式clean结果。上述命令真实调用模型，本次接入验收未执行。

## 筛选injection目标

按 [预检指南](./injection_precheck.md)生成新的AgentDyn cohort，然后两组使用同一份文件：

```bash
python -m experiments.run_partial_benchmark --baseline --attack typical \
  --cohort results/injection_precheck/qwen3.7-flash_agentdyn_injection_screen_01/cohort.json \
  --name partial_baseline_screened_01

python -m experiments.run_partial_benchmark --attack typical \
  --cohort results/injection_precheck/qwen3.7-flash_agentdyn_injection_screen_01/cohort.json \
  --name partial_dscg_screened_01
```

示例路径为AgentDyn；AgentDojo目录标识为agentdojo。换成当前环境实际生成的模型/运行目录。用户仍是原前三个，目标为“原前三个ID ∩ cohort保留目标”，不从后续补位；全筛空场景跳过，全部为空拒绝。scope为partial_screened，不能与full screened混用分母。不能同时使用clean/task manifest，拒绝DoS/all。本次交付前的名单/缓存不迁移，两套后端之间也不可复用。

## 攻击选择与shadow记录

默认typical为ignore_previous、important_instructions、tool_knowledge；具体攻击可重复指定，all查询当前已验证后端注册表并排除manual。injecagent仅显式/all。DoS按首个注册目标、not utility单独计分。上游部分参考调用与GOAL不一致，接入不证明攻击强度。

DSCG CLI默认router shadow，保留L3审计并记录算法观测；baseline/NoChecker默认off，Python factory/API原默认off不变。显式off不关闭L3，no-checker才关闭语义审计。重试0、completion_prompt=false、trace summary保持；selective需独立分组校准与新输入/后端绑定，不能直接沿用旧artifact。

AgentDojo保留现有银行L1有限profile；AgentDyn没有新增profile，完整来源封装保留。动态网页/OTP操作按副作用审计；Monitor/票据仍是工具级边界。框架参数见 [配置指南](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

## 中断续跑

```bash
python -m experiments.run_partial_benchmark --baseline --reuse \
  --model-config config/models.local.toml --name partial_baseline_typical_01

python -m experiments.run_partial_benchmark --reuse \
  --model-config config/models.local.toml \
  --name partial_dscg_typical_01
```

保持原name、根目录、攻击/场景、模型和有效防御设置；旧运行配置一致也可续跑。未指定attack/suites恢复原计划；clean仍需clean，cohort仍需同一文件。源码哈希、Git commit、Python补丁版本不作为兼容门槛；旧绑定保留，规则变化另存记录。reuse与force-rerun互斥，不自动重试原生接受的错误缓存。配置冲突拒绝且不覆盖历史报告；缓存成本不能当作完整新鲜测量。见[显式续跑](./benchmark.md#显式续跑示例)。

Agent临时测试必须用 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。用户正式默认仍为results，不迁移旧数据。离线回归与原生模拟不能代替真实E0、重复模型对照或防御收益验证。
