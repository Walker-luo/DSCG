# 默认攻击与显式续跑实施计划

执行用户已批准的同名计划；不调用真实模型、不改变native缓存/评分或默认任务范围。

- [x] 新typical为ignore_previous、important_instructions、tool_knowledge；injecagent仍可显式/all选择。先更新契约断言并观察RED。
- [x] 为full/partial/API增加reuse=False，支持clean/cohort；需name及已有可核验目录，与force冲突，显式reuse覆盖强制重跑环境变量。不传时保持原缓存行为。
- [x] 在common集中续跑范围恢复及全部绑定预检；未显式选择攻击/场景时采用旧运行计划，缺少根记录时要求显式原攻击及场景；新实验提前记录计划，旧四攻击保持原名单。
- [x] 仅读取明确已审阅源码集合；源码等价变化单独记录，其他配置必须匹配；任务执行前全部检查，失败不写结果。保留旧绑定/raw，新根清单校验后补写，汇总更新前快照。
- [x] 覆盖native缓存的成功/失败/错误/缺失、来源兼容/拒绝、晚场景冲突、缺根记录、CLI/API互斥、clean/cohort/full/partial和成本回归。
- [x] 当前文档/帮助同步108/81/2847及旧四攻击续跑规则；历史成绩与归档不改。全套离线、帮助、链接、哈希、diff检查，一次独立审阅，归档与研究交接。

工程证据：workshop/artifacts/20261017_benchmark_reuse/。原文：workshop/archive/benchmark_reuse_20261017/。本次继续当前workshop工作区，不提交或合并。
