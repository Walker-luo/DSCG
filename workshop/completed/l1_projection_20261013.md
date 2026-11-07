# L1有限结构化投影实施记录

日期：2026-10-13。用户授权依据：[L1_opt.md](../L1_opt.md)。当前版本 `three-layer-l1-v3`；一个有限原生profile已完成工程接入，真实安全/效用/总成本验收及更广profile仍待完成。正式research路线未变，本报告不宣布算法新颖性。

## 实际变化与范围

原L1完整呈现正文并添加Spotlighting风格来源标记。新L1对完整有限月支出请求，先验证原生banking `get_most_recent_transactions` callable/code/输入schema、Transaction输出格式和read/sink-none元数据，才生成固定结构视图。全部记录/原顺序和 `id/sender/recipient/amount/date/recurring` 保留，`subject`省略。规划器不再接触该字段，来源标记仍在。这不是更换分隔符，也没有净化模型、关键词删句或行筛选。

例如原生交易备注夹带要求转账的指令，月总支出任务只需金额/日期/交易双方等字段，投影保留其计算信息，省略备注。要求分析备注、引用原文、附加其他任务、执行order.txt及未匹配句式时仍呈现完整封装。所有字段保持不可信；合法错误金额、IBAN替换或源端漏行无法认证。

严格解析JSON/YAML，最多32,768 UTF-8字节/500行，字段集合必须为原生七字段；拒绝重复/merge键、YAML anchor/alias/tag、非有限金额、布尔数值ID、错误类型/日期/标识、未知/缺失字段。非空错误、显式截断、非文本/混合块、call-ID绑定歧义/不一致、不更短或不适用工具均回退。宿主没有从返回正文选择profile，工具权限与执行基础设施不改变。

原始history、tool_call和error不修改；每轮从原历史生成独立view，L3最近四条/每条2048字符的原窗口继续接收原文。没有新增对象/参数/数据权限、来源传播或恢复机制。Monitor的READ_ONLY_SOURCE_ALLOW例外、L3默认routeroff、retries0/completionfalse保持。

## 控制、身份与平台

- `l1_projection_mode=projected`为executor/factory/partial默认；off保留旧来源封装，shadow计算候选但不替换正文；关闭input_isolation时有效off。旧factory/executor位置参数保持含义，新增factory参数为keyword-only。
- 模式、profile/适配器源码/原生代码/schema/解析边界进入版本、pipeline名、partial manifest和L3兼容hash。相同run名切换模式即使force-rerun也拒绝，需新名字；旧L3部署artifact需重新校准。原生baseline仍使用原循环/无审计连接，manifest将投影记为off/无profile。
- `dscg_l1_projection`记录实际/候选投影、回退原因及字符变化；同一历史返回每次呈现重复计数，不是独立样本。旧added_characters_total仅记封装增量，投影减少量另列。summary/standard不重复projection SHA，runtime/config/full保留身份。
- Dashboard保存/传递有效模式，默认projected，模板/预览/架构和动态版本同步；TXT报告记录模式，旧记录显示未记录。没有单独模式选择器或投影累计面板，API/partial支持对照。没有重启用户服务，重启/刷新才加载源码。

实现：[l1_projection.py](../../dscg/l1_projection.py)、[input_isolation.py](../../dscg/input_isolation.py)、[defended.py](../../dscg/pipelines/defended.py)。计划：[实施计划](./L1_projection_implementation_plan_20261013.md)。平台交接：[framework_updates.md](../../docs/framework_updates.md)。

## 验证与精确命令

以下从DSCG执行；全部新持久化输出位于 `workshop/artifacts/20261013_l1_projection/`，不写用户results/download。详细RED/GREEN过程见 [ledger](../artifacts/20261013_l1_projection/progress.md)。无真实模型或外部工具调用、无新benchmark rollout；模型接口使用Mock/Recorder。回归/I3会执行内存测试工具桩，表示检查仅注册native工具并调用输出formatter。

| 命令（均将控制台重定向到任务根目录对应log） | exit | 分母/结果 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -v`（baseline.log） | 0 | 实施前284/284；当时源码相对HEAD无运行改动 |
| `conda run -n ipi python -m unittest discover -s tests -p test_l1_projection.py -v`（t1_red.log → t1_green.log） | 1 → 0 | 9用例/24缺API子例错误 → 9/9；初GREEN发现测试修改共享工具目录，隔离夹具后修正 |
| `conda run -n ipi python -m unittest discover -s tests -p test_l1_projection_controls.py -v`（t2_red.log → t2_green.log） | 1 → 0 | 5个缺控制用例 → 5/5 |
| 同一controls命令（t2_binding_red.log） | 1 | 7例中1个错误：list模式应返回明确ValueError，而非未处理TypeError；后续全量通过 |
| 同一controls命令（t2_compatibility_red.log） | 1 | 8例中1个错误：新增参数移位；随后保持旧位置参数并全量复验 |
| `conda run -n ipi python -m unittest discover -s tests -v`（offline.log → offline_green.log → offline_final.log → offline_review_green.log） | 1 → 0 → 0 → 0 | 首次300例有2个紧凑trace子例失败，去除冗余hash后300/300；接口兼容补例后301/301，审查回合边界补例后303/303 |
| `node --test tests/test_dashboard_ui.cjs tests/test_history_selection.cjs tests/test_history_ui_selection.cjs tests/test_history_charts.cjs`（node.log及node_final.log） | 0 | 31/31，未增加新图表/模式控件 |
| `conda run -n ipi python -m experiments.i3_p0_stress --output workshop/artifacts/20261013_l1_projection/i3`（i3.log） | 1 | expected partial：24valid/8scope/0tool-boundary，0错误；不是no_go |
| `conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output workshop/artifacts/20261013_l1_projection/e0`（e0.log） | 0 | 合成6例：valid1/tool_error1/infrastructure_error4；真实E0未通过 |
| `conda run -n ipi python workshop/artifacts/20261013_l1_projection/characterize.py characterization_final.json`（characterization_final.log） | 0 | native formatter fixture1例/3行×6字段与独立预期1050；历史144末视图/334返回，12任务/12返回投影 |

最终fresh-context审查发现一个P2：旧query可能覆盖新实际user的备注引用要求。新增回归先失败（review_red.log 1/9；review_boundary_red.log 4个失败子例/10用例），修正为最新实际文本user选择，仅已建立且原user匹配的委托context采用T_eff；缺失/空白/混合user回退。全量303/303通过，无第二审查循环。原表示检查保留，最终检查重新绑定更新后的profile身份，输出characterization_final.json。

新测试验证全行/六字段/顺序、原文与审计保留、正常引用/不适用任务回退、错误/混合/绑定、重复键/别名/超界/格式攻击、有效但错误事实仍不可信，以及模式依赖、factory/router/cache/CLI/API和旧接口兼容。它们不是benchmark防御率。

## 表示检查的证据边界

只读来源：`results/partial_benchmark/deepseek-flash_3layer_L2opt/` 的144条v2.2历史；每个任务只重建一次完整历史的最后view，未模拟真实规划请求次数。12/144任务、12/334返回适用；312返回NO_PROFILE，10返回ERROR_OR_INCOMPLETE。适用返回14,787→7,380字符，减少7,407字符，含字段省略与确定性格式变化，**不等于整段上下文或总Tokens节省**。

144次本地view构建中位数约0.038ms、最大2.291ms，包括copy/metadata/parse/wrapper；仅一次本机描述性测量，不是端到端延迟保证。历史payload相关，不能用12条当独立安全校准；源标签不重算。原v2.2的TSR130/144、nativeASR0/144不属于v3结果。

本机快照的code revision为 `2dcc3d18af59de0136286d1c7090dba7624f6f8f`、branch `workshop`；变更保持未提交。初始运行源码无改动；before.json是在归档原文后采集，已包含本阶段archive未跟踪目录，不能误写成该快照完全clean。最终工作树、原文/源码/产物hash与用户输出保护检查见 [验证清单](../artifacts/20261013_l1_projection/validation_final.json) 和 [修订映射](../archive/l1_projection_20261013/revision_manifest_final.json)。这些是本次范围检查，未改历史migration validator或旧hash。

## 文档与保护验证

`conda run -n ipi python workshop/artifacts/20261013_l1_projection/validate.py validation_final.json revision_manifest_final.json > workshop/artifacts/20261013_l1_projection/validation_final.log 2>&1`；另执行 `git diff --check`。检查14份原字节、79个未改源码hash、29份受保护文档、177个原归档文件、1341份用户结果/导出size/mtime与144条本次读取历史的字节hash，并核对当前链接/版本/目录状态。全部是本次范围验证，不称完整历史迁移或防御效果验证。

首份validation/revision_manifest记录了尚未写完的自身stdout日志，因此该日志SHA为空文件hash；原文件保留供追溯，最终清单明确排除进行中的自身日志，结束后单独验证最终日志hash。该记录缺陷不修改用户结果或旧历史证据。任务review/ledger及最终所有文件hash见最终清单；正式研究路线和implementation_status原前缀保持。

## 整理与后续

完成的有限实施计划/报告归入completed；L1_opt仍在顶层，标明更广适配和真实四臂评估未完成。README、配置/评测说明和平台交接已同步，旧文档原字节保存在 `workshop/archive/l1_projection_20261013/originals/`。旧完成报告、L2/L3候选、来源目录、report/report.md、原始结果/导出与research route保持。

下一项：使用新run名固定模型/任务ID/载荷/L2/L3，做projection off/projected匹配对照，并单列合法引用、字段内事实污染、结构破坏及总模型成本；在独立保真/终态通过前不扩展profile或宣称收益。I2仍锁定，正式研究侧选择不由本报告代替。
