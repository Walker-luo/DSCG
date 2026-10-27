# DSCG Project State

> 更新日期：2026-10-27（Asia/Shanghai）。当前实现为 **DSCG_v3.5.3 / static-task-v352**；本文件只保留现行实现、已验证范围、未解决问题与下一步。历史过程见阶段报告，不从其他分支交接推断当前行为。

## 1. 工作区与当前任务

| 项目 | 状态 |
| --- | --- |
| 工程目录／分支 | `DSCG/`／`workshop`；不修改兄弟BaseIntent或research工作区 |
| 本次开始HEAD | `290b6a156b5a0eaed631171e105c45de7db39de7`；提交时间 `2026-10-27T21:22:16+08:00`；不是本次文档清理产生的提交 |
| 本次任务 | 清除现行交接、状态与导航中的过时机制／默认值，核对当前实现及文档引用 |
| 初始工作区 | Git status为空；本次仅改说明、计划／索引和本状态，不暂存或提交 |
| 当前默认 | `static-task-v352`；baseline默认legacy／原生循环；显式legacy为单次授权对照 |
| 模型与授权 | 在线仅Qwen3.7-Flash；行为验证已有免逐次确认授权，至少9个不同计分任务，大改动按覆盖扩展；纯文档修改无需调用 |

## 2. 已实现的当前机制

- **L1：**从原始历史重建规划视图，有限银行月支出profile保留全部记录与六个结构字段，其余使用来源封装；原始返回继续用于审计／记录。CLI默认off，factory/API保留projected，比较须显式匹配模式。
- **L2：**默认两阶段为静态任务视图提取与全局动作工具布尔权限编译，合并自动读取；主规划与L3共享辅助视图，完整请求仍是依据。全局授权冻结、整批权限／schema／目录复核及授权工具视图保留。视图不证明条件或完成。
- **任务源：**有限明确txt/md委托先经中介准备读取，再编译完整有效请求；普通工具结果不能新增任务权限。保留现有大小／语法边界，不支持递归授权。
- **L3：**严格四字段判决，对当前动作、原请求约束与有限证据审计；外发正文和目的地都检查。`sink-free-read-v4`仅免审已注册／授权／schema有效、read、public/internal、sink=none调用，其余继续审计，deny／abstain阻断。
- **Monitor与诊断：**整批回执、一次性票据、原生顺序及独立诊断／L3原文附件保留。共享读取器支持历史格式；兼容历史intent/progress字段不代表当前启用该机制。
- **执行范围：**full/partial/cohort使用共享工厂、原生评分与分母投影；多attack独立进程并行，内部顺序，clean／single attack／screen顺序。partial仍为注册前3用户×前3目标，cohort不补位。
- **明确未实现：**当前没有host意图进度FSM、自动完成闸门、动态扩权、参数修补、执行后恢复或对象／数据／参数硬授权。最终文本没有独立动作审计。不得导入旧跨分支交接作为默认契约。

代码入口与操作规则见 [AGENTS.md](AGENTS.md)、[README](README.md)、[框架说明](docs/framework_updates.md)、[配置](docs/model_tool_configuration.md)。

## 3. 最新结果与已完成阶段

- **v3.5.3正式复盘已完成：**[analysis/v3-5-3.md](analysis/v3-5-3.md)。共同1119键／1116有效，utility成功727→741，banking−20、Slack−5、travel+39，原生ASR2→0。原始注入、标签、错误和L1模式差异保留；不作单因素因果或一般安全结论。
- **v3.5.3专项优化已完成：**[报告](workshop/completed/v353_optimization_20261027.md)与[实施计划](workshop/completed/v353_implementation_plan_20261027.md)。248计分／消融任务中247有效、1错误；2,968 API尝试／2,966响应，8,252,464已知Tokens，失败usage未知。该阶段范围已结束，不能由剩余额度追加调用；其冻结源码和成绩不替代正式结果。
- **日志定位已交付：**[报告](workshop/completed/benchmark_task_log_ids_20261027.md)记录suite／stage／用户／注入ID与安全错误码，两后端各16项针对性工程检查；该阶段模型调用0。
- **旧版本与逐案例分析：**[v3.5.2](analysis/v3-5-2.md)、[重点案例](analysis/details.md)及[历史阶段目录](workshop/completed/README.md)。按各自版本／配置解读，不重标旧数据，不重复已完成的历史任务。

## 4. 未解决问题与边界

| 问题 | 当前已知情况／处理边界 |
| --- | --- |
| banking任务停办与退款 | u4／u6有权限无候选；u15授权已改善但执行仍差。区分真实缺参、主规划停办与L3误拒，不补日期或扩权 |
| Slack与travel残余误差 | Slack第二频道仍有误拒；travel候选混用、年份与最终交付字段存在问题，原生评分疑点与模型问题单列 |
| 静态视图协议 | 正式28例失败为19引用／9条件关系；不能放宽引用检查、修补返回或将辅助摘要当完整原请求 |
| 原生generation重试与错误投影 | SDK retries0不代表原生generation无重试；已记账失败后成功的调用尚未完整投影为基础设施错误，保留未知成本 |
| 长请求 | static新增提取路径检查原文长度；NoL2／纯读零调用／受限host仍有原协议和截断边界，未修复全部长请求 |
| 历史证据与成本 | 部分旧原回复／导出缺失，cost_comparison_ready可为false；缺失标未知，不补造或据不完整成本宣称节省 |
| 研究门槛与旧I3 | E0 pending；I3 partial（24有效／8范围缺口），旧诊断仍有失败／错误；I2 locked。新机制及已关闭路线须研究侧决定 |

正式研究依据 [technical_route.md](../research/technical_route.md)，回报位置跟随该文件当前链接；本次不修改研究决策。

## 5. 验证状态

- **此前运行验证：**v3.5.3报告保留初始集成202项、AgentDyn相关49项、Node49项及后续定向检查；完整Python套件仍有旧I3失败／错误。报告记录的是其冻结源码，不是本次重跑。
- **本次清理：**仅文档／交接一致性、链接、源码契约和diff检查；真实模型请求0、原生任务执行0、运行时回归未运行。检查结果见 `workshop/artifacts/20261027_handoff_cleanup/validation.json`，清理报告见 [handoff_cleanup_20261027.md](workshop/completed/handoff_cleanup_20261027.md)。
- **证据保护：**原文快照、开始HEAD／index／tracked文件哈希在同一任务目录。未改运行算法、配置、凭据、正式results或download，历史报告原文保留。

## 6. 下一步

先复用正式配对账核对静态协议与banking无候选，再选择单项改动、新名称及匹配clean／攻击验证。Slack误拒、travel候选／最终交付、原生重试错误投影分别处理；不以参数修补、动态扩权或改评分追分。当前清理任务完成后，从 [analysis/plan.md](analysis/plan.md)和实际代码继续，不重开旧campaign。
