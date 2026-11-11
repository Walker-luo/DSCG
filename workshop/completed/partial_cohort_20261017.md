# Partial 冻结 injection 名单

日期：2026-10-17。基准 revision：`9f385a3433f6d09bb7c9b278258ecc43f34e62c8`；工作树已包含前一步未提交的partial场景选择，本次保留并继续扩展。

partial CLI/Python API新增 `--cohort`/`cohort_path`，复用共享cohort证据校验、模型工厂、原生执行与报告。普通partial默认仍四场景，各取注册顺序前三个user与前三个injection，最多9组合/场景/目标型攻击。筛选模式保留前三个user，仅取原前三个injection与冻结通过名单的交集，不补位。三场景名义上仍有9个user；某场景无保留前缀目标时跳过，全部为空拒绝执行。

结果仍默认 `results/partial_benchmark/`，标为 `partial_screened`，区别于全量名单测量的全部用户 `screened`。名单附件保存实际ID、原始/通过/前缀/实际目标数、每攻击计划组合数，以及requested/omitted/skipped场景；预检报告仅覆盖实际执行目标。名单须覆盖所选场景，保留原始证据哈希检查、DoS拒绝和clean/其他清单冲突。新旧范围、名单或场景集合不能用同名测量覆盖；shadow/full等控制沿用原流程。

已知原17文件版本、统一入口20文件版本及前一步partial场景版本按明确字节映射兼容。只扩展名单/runner入口，筛选规则、默认执行评分及dscg防御源码不变；未知版本仍拒绝。旧manifest、attempt和cohort不改写。

## 验证

工程产物：`workshop/artifacts/20261017_partial_cohort/`。修改前源码与工作树状态见 `initial_state.json` 和 originals；精确文件/日志哈希见 `validation.json`。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 49/49 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_injection_precheck.py -v` | 0 | 28/28 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_full_benchmark.py -v` | 0 | 15/15 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 381/381 |
| `conda run -n ipi python -B -m experiments.run_partial_benchmark --help` | 0 | 显示partial名单语义 |
| `git diff --check` | 0 | 无空白错误 |

6个新增离线集成用例通过真实冻结证据与模拟模型/执行，覆盖原前缀交集、不补位、不扩大用户、默认partial输出、范围绑定、空场景、缺失场景、冲突/DoS/证据损坏拒绝、旧源码兼容及shadow/full控制转发。RED日志复现缺少CLI和Python参数；GREEN模拟中每场景5个注入目标有3个通过，但原前三个中仅1个通过，因此三场景×3用户×1目标×4攻击=36条计分结果、12次计划原生预检，而非扩大到后续目标。普通partial仍有每场景9个组合。

新增真实模型请求0、真实benchmark样本0；离线结果不是实际省费率、模型能力或安全收益证据。直接目标失败不能证明间接攻击不可能。E0 pending、I3 partial、I2 locked及closed路线保持原状。

下一步：用户在服务器以同一cohort/场景启动新名称的partial baseline与DSCG，核对附件中的实际分母。命令见 [小批量测试指南](../../docs/partial_benchmark.md#对照与输出)。
