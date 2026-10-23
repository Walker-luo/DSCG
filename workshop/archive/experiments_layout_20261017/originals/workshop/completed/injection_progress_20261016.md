# 预检实时进度与 benchmark 入口统一

日期：2026-10-16。基准 revision：`05b48b0df2fb5e86cbf82d300772299fd2ec91f1`。状态：工程和离线验证完成，真实服务器执行待用户启动。

## 交付

- [预检入口](../../experiments/run_injection_precheck.py) 从476行整理为约296行，保留 screen 和兼容转发；[共享 cohort 模块](../../experiments/injection_cohort.py) 集中处理证据/绑定、兼容校验、预检结果索引及筛选测量，不复制模型工具循环。新增等待提示和显式旧版本兼容需要少量代码，总行数不作为正确性或性能证据。
- 启动即输出配置/任务目录阶段，随后显示模型、目标数、复用来源、输出目录和首次/续跑。逐目标输出恢复/复用/新尝试/失败复测、结果、耗时、Tokens或未知以及累计保留/排除/未决。所有进度逐行 flush，目标执行中每15秒提示等待，不新增模型请求或重试；结束/异常/中断停止等待线程，中断返回130并说明续跑。
- 统一使用 [run_benchmark](../../experiments/run_benchmark.py)：默认仍完整 full；显式 `--cohort PATH` 或 Python `cohort_path` 使用完整用户集合与冻结 injection targets。共享 runner、任务选择和报告新增明确 `screened` 范围、cohort哈希、筛选摘要标题及分母。full清单仍不能缩小任务集，partial默认前缀保持不变。
- 全部既有 CLI 控制复用统一解析；cohort与clean/其他任务清单/清单导出互斥，拒绝DoS，空场景跳过/全空拒绝。旧 benchmark 子命令只提示转发并要求非空cohort；Python API 的显式 suites 不得漏掉冻结名单的非空场景。
- [兼容映射](../../experiments/injection_cohort_compatibility.json) 固定已知旧17文件集合、旧脚本哈希以及本次6个改动文件目标哈希；防御代码须逐字节不变，未知新增运行源码也拒绝。本次兼容只新增 provenance 文件，旧screen manifest、attempt、cohort不改写；新版本攻击测量使用新name。

命令、输出和兼容细节见 [用户指南](../../docs/injection_precheck.md)。已有运行中的进程需要更新后重新执行预检命令才能看到新进度。

## 验证与审查

新产物根：`workshop/artifacts/20261016_injection_progress/`；精确命令、退出码、revision、dirty工作树及文件/日志哈希见 `validation.json`，小型可分发清单另存于本阶段的 manifest JSON。原始日志和模拟产物默认忽略，未分发时应重新核查。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_injection_precheck.py -v` | 0 | 27/27：模型工作前进度、flush/等待线程停止、中断保存、已知旧冻结/未完成状态、未知旧代码/新增运行源码拒绝、统一入口与控制、范围和证据保护 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 369/369 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_full_benchmark.py -v` | 0 | 15/15 |
| `conda run -n ipi python -B -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 38/38 |
| `python -B -m experiments.run_benchmark --help`、`python -B -m experiments.run_injection_precheck screen --help`、旧 `benchmark --help` | 0 | 无模型客户端构造；帮助保留统一选项与兼容提示 |

TDD日志：`red.log` 复现无实时进度/缺统一入口；`red_02.log` 复现未知新增运行源码未被旧版本兼容拒绝；审查后的 `review_red.log` 复现旧alias漏cohort意外走full及Python suites被忽略。均已修复，最终 `precheck_final.log` 27/27，`full_regression_final.log` 369/369。独立代码审查仅两项有效问题，均在一轮修复中添加回归并验证；无延期项。

`sample_progress.log` 和 demo目录仅使用 FakeSuite 和模拟pipeline，展示输出，不是模型/benchmark新结果。`historical_compatibility.json` 只读复核35个注册目标，14个已有workspace预检仍可复用；没有复测或重新宣布剔除。旧baseline目录280文件及原有dscg运行源码的最终哈希复核写入validation。修改前13个源码/文档原始字节在 `workshop/archive/injection_progress_20261016/originals/`，映射见 `before.json`。

## 限制与下一步

新增真实模型请求0、真实benchmark样本0。源目录/模型服务修订限制、直接GOAL失败不证明间接攻击不可能、历史及原生预检独立usage未知等限制继续保留。实时等待只说明本次目标尚在执行，不是服务端进度百分比或超时根因诊断；screened结果不等于完整full。

下一步：同步服务器代码后用原name继续预检，检查未决/失败轨迹；冻结名单后使用新的测量name运行统一 `run_benchmark --cohort` 的匹配baseline与DSCG/shadow。E0 pending、I3 partial、I2 locked及closed路线不变。
