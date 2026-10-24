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

AgentDojo默认覆盖workspace14/travel7/banking9/slack5共35目标；AgentDyn为shopping9/github9/dailylife10共28目标。可用对应场景的suites选择子集。**每目标只执行一次完整GOAL轨迹：成功保留，失败跳过，不再复测。** 一条轨迹仍可包含多次模型请求和工具调用。

API/上下文错误、中断或损坏记录单列为`error`，不计有效失败，也不纳入cohort或自动重试。处理完其他目标后仍生成只含成功目标的cohort；有错误时退出码为1，提示本次筛选不完整，不阻止你读取已生成名单。原生失败但没有运行错误时退出码为0。上游部分参考调用是占位内容，按原生轨迹与真实终态审查，不修改目标或标准答案。

实时输出总量、逐目标状态、耗时和已知Token；执行中每15秒等待提示不额外调用模型。默认输出：

```text
results/injection_precheck/<benchmark_id>/<model_id>_injection_screen_01/
  screen_manifest.json
  status.json    # 仅总量、成功/失败/错误数、已知Token及未知成本数
  summary.md     # 每场景一行，不逐任务重复展开
  cohort.json    # 完整判定、任务名单及证据引用
  attempts/      # 单次记录、绑定和原始轨迹
```

results-dir表示预检分类根，程序追加`<backend>/<model>_<name>/`。相同screen命令优先使用新目录，新路径不存在时才查找旧`<model>_<backend>_<name>/`并原地续跑；新路径存在但绑定缺失/损坏/不符时拒绝，不回退旧目录。旧cohort与attempt不移动、不改写。screen续跑仍依赖原证据路径；测量读取已冻结cohort不依赖这些路径。

具体尝试保留独立原生轨迹、原始错误与哈希，冻结名单引用证据。status不再重复decisions/逐次轨迹和复用拒绝路径，只保留统计；完整详情查看cohort及attempts。已有旧文件不删除或搬移，旧冻结名单不重写。成本未知保持未知，screen成本与后续攻击原生预检分别记录。

可选只读复用同一后端、模型和任务配置的baseline预检（--reuse-from是证据来源，区别于测量入口的--reuse）：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml \
  --reuse-from results/benchmarks/agentdyn/qwen3.7-flash_baseline_typical_01 \
  --name injection_screen_02
```

将目录换成实际模型/运行名。核对后端元数据、模型公开配置、版本、任务ID、GOAL和完整原生结果；按路径排序取首条兼容记录作为唯一尝试，失败/错误也不再补测，不继续寻找后续成功。源码哈希、预检脚本及任务实现源码变化不再成为兼容门槛，历史兼容映射不参与运行。原始轨迹、引用manifest及cohort哈希仍检查；跨基准或缺少必要身份时拒绝。

## 2. 中断和错误后续跑

保持模型/后端/任务/GOAL配置、name和输出根，重新执行同一screen命令。只执行尚未开始的目标；已有失败、错误和中断尝试不重跑，原字节保留。已完成但未写attempt记录的原生轨迹会恢复记账。冻结cohort已生成则核验后直接返回，不发模型请求；含error的名单继续返回1。

旧“两次失败”规则的**已冻结cohort**保留原语义和原字节；旧的未完成screen允许在其他身份相同时改用单次规则，按每目标首条尝试判定，不再补测。原manifest/attempt不改写，规则转换记入compatibility，新cohort声明单次规则。该变更不要求重筛已经冻结的历史名单。源码差异另记configuration-only记录，不认证源码等价。

screen没有force-rerun；需要全新预检使用新name。配置冲突不覆盖原结果。仅记录Git/Python/包版本供追溯，不做工程源码扫描；缺少后端、模型或任务身份不能通过手改manifest补造。

冻结 cohort 在测量时视为可信名单：只比较主模型的 `model_id + provider`，核对实际后端身份、具体包版本、suite版本（AgentDyn还核对固定revision），并检查本次所选场景及任务ID的有效性和注册顺序。只读取一次cohort并验证自身摘要，随后复用内存名单；adapter、endpoint、凭证变量、思考设置和审计模型不作为名单兼容条件。

测量不再读取attempt、原始轨迹或引用manifest，不核对GOAL、重算筛选结论或检查消息序列化。因此原预检目录移动、缺失或轨迹变化不会阻止冻结名单读取，也不再使用adapter no-op特殊兼容分支。原文件不改写；新附件及执行记录的 `cohort_validation` 标明 `mode=model_backend_suites_v1`、`screening_evidence_verified=false`，表示未重新验证预检证据，而非重新认证筛选结论。

这仅适用于测量读取冻结名单。screen创建、未完成续跑及历史证据复用仍走原证据校验；已有攻击结果的缓存复用仍严格比较实际模型请求与防御配置，不能因名单可读就混用不同请求配置的旧缓存。

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
