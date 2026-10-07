# 框架优化实施报告

按 research/paper/framework_optimization_20261007.md 实现 P0 工程优化；不增加论文机制。各阶段验证日志与 evidence 位于 `examples/results/framework_optimization/20261007_implementation/`，研究回报写入 sibling implementation_status.md。

## P0-A — 任务隔离

顶层调用新建 context，清除旧授权缓存和历史、撤销票据；任务内循环沿用。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-A_tests.log`）。新模型样本 0；不推断效用或防御率改善。
## P0-B — 成本与诊断

记录主模型/授权/审计 API、Token、耗时；历史分析显示两模型合计。官方攻击分数保留，E0 独立送达/环境复核仍待完成。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-B_tests.log`）。新模型样本 0；不推断效用或防御率改善。
## P0-C — 外部请求

网页请求按外部接收方路由至现有审计；离线成对样例覆盖合法访问和注入网址。未实现 URL 对象约束。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P0-C_tests.log`）。新模型样本 0；不推断效用或防御率改善。
## P1-A — 有界重审

可选一次语义 abstain 重审；保留当前任务历史，parser/超时不重试，持续不确定阻断。

离线回归：`conda run -n ipi python -m unittest discover -s tests -v`，退出码 0（完整日志 `P1-A_tests.log`）。新模型样本 0；不推断效用或防御率改善。
