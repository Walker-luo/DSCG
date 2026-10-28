# Injection目标预检与冻结名单

`experiments.run_injection_precheck screen`把注入任务GOAL直接交给当前后端的原生无防御循环。它测试目标可完成性，**不是间接注入攻击或正常用户clean测试**。失败不证明间接攻击无效；筛选结果须标screened。

## 1. 独立预检

在项目根，激活ipi／ipi-agentdyn后执行；screen会调用真实模型：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_01
```

默认覆盖当前后端全部注入目标（AgentDojo35，AgentDyn28），可用suites选子集。**每GOAL仅一次完整轨迹**：成功保留，失败排除，错误／中断另列且不重试。一条轨迹可含多次模型请求。

全部目标处理后冻结success-only cohort；有错误仍生成名单并退出1，原生失败但无错误退出0。不能按DSCG防御成绩反向筛选目标。

```text
results/injection_precheck/<backend>/<model>_injection_screen_01/
  screen_manifest.json    # 绑定
  status.json            # 数量／已知成本
  summary.md             # 每场景一行
  cohort.json            # 冻结名单与完整判定
  attempts/              # 每目标尝试、原始轨迹与引用
```

可显式只读复用已有baseline GOAL证据：

```bash
python -m experiments.run_injection_precheck screen \
  --reuse-from /absolute/path/to/baseline_run --name injection_screen_02
```

按路径取首条兼容证据作为唯一尝试，失败／错误也不再寻找后续成功；核对模型、后端、任务／GOAL及原始证据。该reuse-from不同于测量续跑reuse。

## 2. 中断和错误后续跑

同配置／name／输出根重新执行screen，仅运行尚未开始的目标；已有失败、错误、中断不重跑。冻结名单存在则核验后直接返回，含错误仍退出1。没有force-rerun；全新筛选用新名称。

历史已冻结的“两次失败”名单保留原字节／规则；未完成旧screen按兼容流程采用首条尝试，不补测、不改旧manifest和attempt。screen创建、续跑及历史证据复用仍检查原证据。

### 测量如何读取冻结名单

只检查主模型model_id＋provider、实际后端／包与suite版本（AgentDyn固定revision）、所选场景与任务ID／顺序，并读一次名单验证自身摘要。**不再读取原attempt／轨迹，不重算GOAL或筛选结论**；原screen目录移动不妨碍名单消费。

adapter／endpoint／凭据变量／思考设置／审计模型不作为名单兼容条件。附件标 `mode=model_backend_suites_v1`、`screening_evidence_verified=false`。这不等于重新认证筛选结论，也不放松实际测量缓存的完整配置绑定。

## 3. 使用冻结名单测baseline和DSCG

```bash
python -m experiments.run_benchmark --baseline --suites banking slack --attack typical \
  --cohort /absolute/path/to/cohort.json --name baseline_screened_01
python -m experiments.run_benchmark --suites banking slack --attack typical \
  --cohort /absolute/path/to/cohort.json --name v354_screened_01
```

示例为AgentDojo，路径换为实际名单；AgentDyn用自己的场景。默认DSCG已启用static两阶段L2；单次授权对照另加`--prompt-profile legacy`。策略更新使用新名称，原cohort按既有消费规则读取。

full保留全部所选用户，仅筛目标；partial保留前3用户×（原前3目标∩cohort），不补位。空场景跳过，全空拒绝；与clean／task manifest互斥，拒绝DoS及含DoS的all。原生攻击GOAL预检仍可能发生，成本与独立screen分开记录。

输出、续跑和评分见[完整指南](benchmark.md)及[partial](partial_benchmark.md)。旧benchmark子命令仍为cohort转发入口。`--results-dir`是分类根，追加后端／模型运行层；新路径不存在时才查旧布局，原数据不移动。agent临时screen须使用新的workshop/artifacts任务目录。
