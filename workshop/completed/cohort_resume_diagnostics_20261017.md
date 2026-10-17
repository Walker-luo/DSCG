# 服务器 cohort 续跑排错（2026-10-17）

本次修复错误诊断和已知源码续跑兼容，不修改原生模型循环、评分、任务范围或防御行为。依据用户服务器反馈，Python 和两个入口导入路径正确；唯一源码不匹配来自 `run_partial_benchmark.py` 解析器的 `default=None` 被手改为 `default="shadow"`。

## 根因与处理

- 服务器预期哈希 `f5e81729b76eb4e9350a66cadcbb3b911ea746a65076b93fa6587dfe48159de4`，实际 `605d476bc586e74128eec619690a3f304b4f7ce32e88377a644718e174bd593c`。在归档原代码中只替换用户指出的一处默认值，逐字节重现实际哈希。未把这处改变 baseline 语义的手改加入兼容名单。
- `None` 用于后续按 profile 自动选择 DSCG shadow、baseline/NoChecker off。恢复 None 即可保留所需默认行为；服务器同步 runner 和两份兼容映射。未知源码仍拒绝复用。
- cohort/screen 绑定拒绝现在显示运行环境、变更字段名或具体源码路径与哈希前缀，不输出配置值、GOAL 或工具正文。full/partial CLI 分别报告模型、工具元数据和测量证据错误。
- 修复独立问题：测量兼容映射的生成机器 Python 3.10.21 不再额外约束服务器；原运行与当前运行的 Python/AgentDojo 仍必须一致，旧源码仍须在独立审核名单中。
- 新增本次变更前完整源码身份并刷新明确目标哈希。两份兼容清单的元数据演进不改变 direct-GOAL 执行；测量入口独立验证其清单。旧身份、manifest/cohort、轨迹不改写。

本地现有 `No_workspace_v3.2` 身份副本中，模型公开配置和任务目录与当前一致；以服务器同为 Python 3.10.19 作纯内存模拟时，预检与测量源码兼容均通过。该运行原路由为 **off**，攻击为原四攻击；续跑须显式保持 off，省略 attack 以读取原名单。完整命令见[运行指南](../../docs/benchmark.md#cohort-或续跑校验失败)。本地没有原服务器预检绝对路径下的轨迹，不能声称完成了服务器全部证据核验或实际续跑。

## 离线验证

基准 revision `31b932e2cccb6265f24345be8a103562a2ae51be`；任务开始工作树干净，交付时为本次代码、测试、文档和兼容映射修改，未提交。验证环境 Python 3.10.21 / AgentDojo 0.1.35；服务器报告 Python 3.10.19。产物位于 [本次目录](../artifacts/20261017_cohort_resume_diagnostics/)，修改前原字节位于 [归档](../archive/cohort_resume_diagnostics_20261017/originals/)。

| 命令 | 退出码与证据 |
| --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_resume_diagnostics.py -v` | 修复前 1：5项测试6个断言失败；修复后 0；最终6项含默认值保护均通过全套回归 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 首次 1：413项中1个旧绑定回归失败，补全已审阅兼容清单元数据过渡后最终0：413/413；日志 regression_final.log |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_partial_cohort.py -v` | 0：9/9，日志 cohort_regression.log |
| `conda run -n ipi python -B -c "import runpy; runpy.run_path('workshop/artifacts/20261017_cohort_resume_diagnostics/verify_saved_run.py',run_name='__main__')"` | 0：只读身份与服务器哈希重现；saved_run_validation.json |
| `python -B workshop/artifacts/20261017_cohort_resume_diagnostics/verify_delivery.py` | 0：归档、映射、用户结果、指南链接与帮助；validation.json |
| `git diff --check` | 0 |

本次生成真实模型请求0、真实benchmark样本0；413项为工程测试分母，不是效用/安全评测。未放宽未知源码、模型、任务、有效防御设置或原生证据校验。真实服务器仍须同步代码、恢复已审核默认值并保留原路由参数后执行原命令。E0 pending、I3 partial、I2 locked及关闭路线均不变。下一步：服务器使用原目录和 `--audit-router-mode off --reuse`，核对新的具体校验结果。
