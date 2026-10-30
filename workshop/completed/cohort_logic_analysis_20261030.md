# 当前基线的cohort与GOAL逻辑

2026-10-30。当前HEAD a7bc699205fe28e01e0043c6624c8d75bd63bd30，detached HEAD；策略仍static-task-v354，沿用用户当前代码作为后续基础。本次仅分析，未切换／修改运行代码、未发API请求。保留已有未跟踪v354_timeout_analysis_20261030.md，不改历史结果。

## 三个环节

| 环节 | 目的／执行方式 | 影响 |
| --- | --- | --- |
| screen生成cohort | 无防御pipeline将injection GOAL作为正常用户请求，跑一条原生轨迹并评分 | 有效成功目标保留；失败／错误分别处理，冻结选择 |
| --cohort消费名单 | 校验名单摘要、主模型／provider、后端、场景及任务ID，取保留目标 | 本身不发模型请求，也不重新读取原screen证据判断GOAL |
| 当前测量中的原生预检 | 每个attack×suite使用该测量的pipeline，将保留GOAL再作为正常用户任务执行 | 只记录／警告，不重新过滤cohort；不是间接攻击，也不进入TSR／ASR分母，但增加调用和错误机会 |

筛选阶段与测量阶段使用的pipeline可能不同：前者无防御，后者随当前baseline／防御设置。因此并非字节相同请求，但对于“筛一次能力、冻结共同任务集合再比较防御”的目的，后者属于重复的能力检查。它不是必须的名单消费校验。

## 直接代码证据

- experiments/common/injection_cohort.py:307的run_screened读取／校验cohort、确定selected，然后调用shared.main；没有把“已筛选，关闭GOAL”的开关传下去。附件cost_scope也明确写native per-attack preflight retained。
- experiments/run_partial_benchmark.py:682在screened路径仍设置goal_total=len(selected_injections)，再调用共享原生执行器。
- experiments/common/benchmark_tasks.py:186只判断not attack.is_dos_attack，未判断是否cohort。先遍历目标执行run_task_without_injection_tasks，再对用户任务运行run_task_with_injection_tasks。
- 预检为False仅warnings.warn；后续targets不变，故不是二次筛选，不会因预检失败自动删计分任务。

例如保留20个GOAL、选择3种攻击，新的完整测量每种pipeline可再安排60条GOAL轨迹；一条轨迹可能多次API调用。缓存可减少实际调用，不能直接把计划轨迹数当请求数；不同实验名称／攻击／防御通常分别记录结果。

## 为什么与前一轮观察不同

本次当前HEAD是a7bc699，而上一轮超时分析对应7dd3db0。git diff确认，7dd3db0在不改dscg防御文件的情况下引入goal_preflight开关及frozen-screen-only-v1身份：screened／partial_screened关闭原生GOAL，普通未筛选测量保持预检，同时改进度、报告和测试。当前切换退回了这项入口修复；不能把GOAL又出现归因于框架模型能力退步。

## 建议边界

推荐：screen只做一次直接GOAL；cohort消费保留摘要／模型／后端／任务范围校验，随后直接做正常计分任务，不自动再跑GOAL。普通不带cohort的benchmark可保留原生预检。如需研究“防御是否损害直接能力”，另做显式诊断，独立分母和成本，不改变冻结名单。

后续可在用户当前代码上只迁入这部分测试入口改动，保留当前L1/L2/L3。必须同时覆盖full／partial／API入口、进度、费用报告及策略身份；用新run-name，不将旧结果伪装成无预检模式。本次没有实施或重测，也不自动切回7dd3db0。

核对命令：git status --short／git rev-parse HEAD／git branch --show-current；读取上述函数及screen._native_attempt；git diff a7bc699 7dd3db0 -- experiments/common/benchmark_tasks.py experiments/run_partial_benchmark.py experiments/common/injection_cohort.py。代码保护hash与检查在workshop/artifacts/20261030_cohort_logic_analysis/。
