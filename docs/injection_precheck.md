# Injection 目标预检与冻结名单

`experiments.run_injection_precheck screen` 把注入任务的GOAL直接交给当前基准的原生无防御循环，检查当前主模型的可完成性。它不向工具返回注入内容，也不测试全部正常用户任务的clean能力；后者见 [clean对照](./benchmark.md#2-clean-对照先确认智能体能力)。

直接失败不证明间接注入不能成功，可能是主动拒绝、动态操作失败或原生评分疑点。筛选后的结果须标记screened，不能标成完整AgentDyn，也不能按DSCG效果反向筛选名单。

## 1. 独立预检

在DSCG目录、已激活 `ipi` 或 `ipi-agentdyn` 后：

```bash
python -m dscg.benchmark_catalog
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_01
```

AgentDojo默认覆盖workspace14/travel7/banking9/slack5共35目标；AgentDyn为shopping9/github9/dailylife10共28目标。可用对应场景的suites选择子集。每目标首次一次有效成功即保留，两次有效失败才排除；API/上下文错误、缺失或损坏结果不计有效失败，有未决目标则不生成cohort。上游部分参考调用是占位内容，按原生轨迹与真实终态审查，不修改目标或标准答案。

实时输出总量、逐目标状态、耗时和已知Token；执行中每15秒等待提示不额外调用模型。默认输出：

```text
results/injection_precheck/<benchmark_id>/<model_id>_injection_screen_01/
  screen_manifest.json
  status.json
  summary.md
  cohort.json  # 全部目标完成判定后生成
```

results-dir表示预检分类根，程序追加`<backend>/<model>_<name>/`。相同screen命令优先使用新目录，新路径不存在时才查找旧`<model>_<backend>_<name>/`并原地续跑；新路径存在但绑定缺失/损坏/不符时拒绝，不回退旧目录。旧cohort与attempt不移动、不改写，证据中的绝对路径保持有效。

具体尝试保留独立原生轨迹、原始错误与哈希，冻结名单引用证据。成本未知保持未知，screen成本与后续攻击原生预检分别记录。

可选只读复用同一后端、模型和任务配置的baseline预检（--reuse-from是证据来源，区别于测量入口的--reuse）：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml \
  --reuse-from results/benchmarks/agentdyn/qwen3.7-flash_baseline_typical_01 \
  --name injection_screen_02
```

将目录换成实际模型/运行名。核对后端元数据、模型公开配置、版本、任务ID、GOAL和完整原生结果；相同轨迹不重复计数。源码哈希、预检脚本及任务实现源码变化不再成为兼容门槛，历史兼容映射不参与运行。原始轨迹、引用manifest及cohort哈希仍检查；跨基准或缺少必要身份时拒绝。

## 2. 中断和错误后续跑

保持模型/后端/任务/GOAL/规则配置、name和输出根，重新执行同一screen命令。已判定目标不重跑，不足两次有效失败的目标补测；错误/中断尝试原字节保留，新尝试用新目录。冻结cohort已生成则核验后直接返回；旧manifest、attempt、cohort均不改写。源码差异另记configuration-only记录，不认证源码等价。

screen没有force-rerun；需要全新预检使用新name。配置冲突不覆盖原结果。仅记录Git/Python/包版本供追溯，不做工程源码扫描；缺少后端、模型或任务身份不能通过手改manifest补造。

## 3. 使用冻结名单测 baseline 和 DSCG

```bash
python -m experiments.run_benchmark --baseline --attack typical --force-rerun \
  --model-config config/models.local.toml \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name baseline_screened_01

python -m experiments.run_benchmark --attack typical --force-rerun \
  --model-config config/models.local.toml \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name dscg_screened_01
```

示例是AgentDyn路径，AgentDojo使用agentdojo目录。使用当前环境自己生成的实际cohort路径；两组同一模型/名单/场景/攻击。full保留所选场景全部用户，仅筛选注入目标；partial仍为原前3用户×（原前3目标与cohort的交集），不补位。显式suites须符合冻结名单；空场景跳过，全部为空拒绝。

结果保存cohort及筛选后的ID/hash，不能和完整分母混报。cohort与clean/task manifest互斥，拒绝DoS及含DoS的all。三种typical攻击仍各自执行原生GOAL预检，不能把独立screen当成这些调用已经发生，或重复累计Token。

统一测量入口支持防御控制、自定义results-dir、显式reuse和错误报告；细则见 [完整测试](./benchmark.md) 与 [partial](./partial_benchmark.md)。旧 `run_injection_precheck benchmark` 仍是转发入口，要求cohort。测量reuse与screen的reuse-from含义不同。

上述命令会调用模型；本轮工程验收只做离线模拟。TSR、ASR、攻击强度、服务模型修订可复现性和真实E0仍待验证。Agent生成的临时预检须显式把results-dir设到新的workshop/artifacts日期目录，保留用户results/download。
