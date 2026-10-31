# benchmark日志任务ID定位（2026-10-27）

已补全用户报告的两类控制台信息。范围仅为日志展示，保留当前DSCG_v3.5.3的授权、API请求、评分、缓存、原生任务顺序与诊断证据。

## 行为

- L2授权编译失败打印suite、stage、user_task_id、injection_task_id、异常类型及已有安全reason_code；不打印异常原文、提示或凭证。
- 正式攻击计分使用`stage=scored_task`及真实用户／注入任务对。clean使用`stage=clean_task`和`injection_task_id=none`。
- GOAL预检是注入目标自身的直接执行，没有普通用户任务；显示`stage=goal_preflight user_task_id=none injection_task_id=<目标ID>`。失败与tool-JSON错误警告逐目标输出，成功目标不混入警告。
- 共享runner在每次原生调用周围绑定只供控制台使用的ContextVar，并在正常／异常退出后恢复。直接pipeline调用使用已有原生日志上下文；未知字段明确显示unknown。并发attack仍使用原有独立进程机制。

示例（任务ID来自日志单元测试，不是远端历史错误的反推）：

```text
[L2 Authorization suite=banking stage=scored_task user_task_id=user_task_17 injection_task_id=injection_task_3] 意图解析失败，沙箱进入安全失败状态: AuthorizationCompilationError; reason_code=AUTH_INVALID_JSON
[suite=banking stage=goal_preflight user_task_id=none injection_task_id=injection_task_3] Injection GOAL was not solved as a user task.
```

共享修改位于`dscg/task_diagnostics.py`、`dscg/pipelines/defended.py`和`experiments/common/benchmark_tasks.py`，full／partial／cohort均覆盖。用户贴出的旧汇总警告本身不足以还原具体目标；更新服务器代码后，新启动的benchmark进程会输出这些字段，现有Python进程不会自动加载本地改动。

## Offline Regression

新增5项测试覆盖：GOAL与计分授权失败标签、逐目标失败／错误警告、clean及无上下文调用、异常清理、原生日志回退及异常原文不外泄。修改前5项中4失败／1通过，均为缺失日志字段；随后连同既有进度／沙箱测试，在两个环境各16项通过。

命令均在DSCG根目录执行，输出位于本次新产物目录：

```bash
PYTHONPATH=.:tests /opt/miniconda3/envs/ipi/bin/python -B -m unittest test_benchmark_log_context -v
# RED：5项，4失败；保存red.log（当时shell随后执行tail，shell出口为0，测试本身未通过）。
PYTHONPATH=.:tests /opt/miniconda3/envs/ipi/bin/python -B -m unittest test_benchmark_log_context test_benchmark_progress.ProgressAdapterTests test_benchmark_progress.ProgressDisplayTests test_permission_sandbox -v
# GREEN：16项通过，exit 0；green_ipi.log。
PYTHONPATH=.:tests /opt/miniconda3/envs/ipi-agentdyn/bin/python -B -m unittest test_benchmark_log_context test_benchmark_progress.ProgressAdapterTests test_benchmark_progress.ProgressDisplayTests test_permission_sandbox -v
# GREEN：16项通过，exit 0；green_agentdyn.log。
```

未运行全套回归或原生完整benchmark；没有模型判断质量、TSR／ASR或防御效果结论。针对性测试使用本地函数／错误夹具，只验证工程日志和既有控制流程，不替代模型评测。

## Online Evaluation

本次为日志展示修复，没有模型行为变更，不执行在线任务：真实API尝试／成功0／0，新增模型用量0。没有重开任何历史campaign，也未使用旧余额。

## 状态与证据

基线分支`workshop`，HEAD `04c479a45867b086c074101ebb1d10ec7bb01ff7`。开始时DV_STATE.md与analysis/v3-5-2.md已有用户修改，保留；本次补充日志进展与指南，未触碰正式results／download、配置或研究机制，未暂存／提交。语法、文档链接、源码差异及index核对见产物verification.json。

证据：[workshop/artifacts/20261027_benchmark_task_log_ids](../artifacts/20261027_benchmark_task_log_ids/)。含基线、修改前源码快照、RED／GREEN日志和最终源码哈希。

下一行动：将这次运行时改动同步至实际运行服务器，在新进程的日志中按stage和两个任务ID定位；本次未访问或重启远端benchmark。
