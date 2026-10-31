# 框架说明、方案归档与平台交接核查（2026-10-10）

本阶段完成用户要求的文档细节整理：README把三层职责、实际执行循环、触发频率与读取例外说明清楚，增加“读取邮件并发送预算摘要”的示意；已实施三层基础方案从workshop顶层移入completed；待实现和撤回的机制逐项标识；核查平台交接是否交付。

## 文档与方案状态

[README](../../README.md)先说明层号与时间顺序，再用“未授权delete_email”和“已授权send_email但收件人偏离”解释L2/L3的不同作用。示例不代表实测，L1不保证模型服从边界，目的地依赖语义审计而不是参数硬授权；已授权无sink读取的有效deny仍可能由Monitor例外放行。

[三层基础方案](./3_layer_opt.md)现在归入completed，L1、L2前置与原L3的工程实施完成；§5总成本目标、§7匹配模型消融与独立终态验证仍未正式验收。新增落实状态表避免“归档=所有目标达成”的误解。

[顶层索引](../README.md)只列两个未实施机制：[L3 Checker CSA](../L3_checker_opt.md)和[授权对照校准](../original_framework_direction_20261008.md)。前者的本地特征/模型、独立标签、分组阈值、off/shadow/selective、路由凭据和内部读取免审均未实现；后者未实施且暂停推进。原有公开读取免审不是CSA的实现证据。

[completed索引](./README.md)区分各历史阶段的保留、未完成和撤回项：V2 Stage1保留，Stage2执行提示撤回；原局部LLM净化、重审/恢复不进入默认；早期E0自检与八例I3结论不能替代当前闸门/partial证据。仅更新现行阅读路径，原始字节和旧证据哈希保留。

## 平台交接结论

只读查询了 **dashboard optimize** 对话（`01a10ff4-740a-78a3-a1e2-74bd3ab90915`），其历史下载、多指标选择与分图/颜色对应三个请求均有completed记录；这些记录作为检索线索，再对照当前源码和离线检查。未向其他对话发送消息或分配任务。

此前交付范围已落实：当前三层架构弹窗、旧L2/L3开关与factory接线、独立/history页面、ASR/TSR下载、分指标图表和身份/颜色映射均在源码中。具体位置与本次核查见 [framework_updates](../../docs/framework_updates.md) 的逐项交接表。

独立L1网页开关、CSA模式、路由/封装统计图和失败片段浏览器没有实现，明确列作扩展。网页有限子集的seed排序与partial注册顺序前缀不同，跨入口比较要核对实际task IDs。当前运行中的旧服务仍需用户重启/刷新才能加载已变更的源码，本次没有重启服务或模型评测。

## 验证与保留

本次开始时已有上一阶段未提交的三层运行时/网页改动；全部保留，**相对于本次开始快照没有修改运行时、tests或dashboard源码**。基线HEAD为`8f608618171d4ffac8c8ec99d1278302282204fe`，不代表当前源码全部已提交。起始状态、最终hash与归档映射见 [evidence.json](../artifacts/20261010_framework_docs_cleanup/evidence.json) 和 [新增修订清单](../archive/framework_docs_cleanup_20261010/revision_manifest.json)。

| 命令 | 退出码 | 范围 / 结果 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -p 'test_dashboard*.py' -v` | 0 | 当前20/20面板配置/历史/导出离线回归，dashboard_tests.log |
| `node --test tests/test_history*.cjs` | 0 | 当前21/21历史选择/图表检查，node.log |
| `conda run -n ipi python workshop/artifacts/20261010_framework_docs_cleanup/validate.py` | 0 | 链接、搬迁、原字节、修订链、65个源码hash、Flask页面与结果目录核查，validation.json |
| `python workshop/verify_migration.py` | 1 | 仍被既有删除的research/paper/framework_optimization_20261007.md兼容路径阻断，migration.log；本次修订链检查在此之前通过 |
| `git diff --check` | 0 | diff_check.log |

新输出均在`workshop/artifacts/20261010_framework_docs_cleanup/`。本阶段0个新运行时测试、0个模型API调用、0个benchmark/training/calibration样本。没有重跑完整模型或防御回归，也未将先前204/204称为本次新全量结果；本次仅验证文档与平台交接，正式E0、I3partial与I2locked状态保持。

全部11份本次修改前文档/检查脚本存为独立原始字节，旧manifest和旧artifact哈希不改写。第五修订清单连接既有三层实施清单，并显式记录base方案旧→新位置；完整历史迁移未通过与本次当前一致性通过分开报告。

下一步：使用当前README与交接清单阅读框架；若需要平台独立消融/路由统计等扩展，另行确定其范围，不由文档归档自动启动实现。
