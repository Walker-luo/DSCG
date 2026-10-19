# Dashboard 使用指南

在 `DSCG/` 激活要使用的环境，再启动同一个入口：

```bash
conda activate ipi
python -m dashboard.app
```

`ipi` 自动识别为 AgentDojo；使用 AgentDyn 时先改为 `conda activate ipi-agentdyn`，命令和网页操作相同，不需要后端选择器或额外后端参数。识别依据是当前 Python 进程实际加载路径、安装来源、版本及revision，不仅是环境名。默认地址为 [实验配置](http://127.0.0.1:8888/)；[历史分析](http://127.0.0.1:8888/history)是并列页面。用户从面板启动的实验保存到 `results/dashboard/`。

切换终端中的 conda 环境不会改变已启动的服务，须停止原 Dashboard 进程，再在目标环境中启动并刷新页面。也可在两个终端同时运行，并使用不同端口：

```bash
# 终端 A：AgentDojo
conda activate ipi
PORT=8888 python -m dashboard.app

# 终端 B：AgentDyn
conda activate ipi-agentdyn
PORT=8889 python -m dashboard.app
```

两个服务各自识别当前环境；历史结果目录可被两边读取，新运行仍按各自基准分开保存。当前通过校验的两个后端均使用 suite version `v1.2`：

| 后端 / 环境 | 场景 | 用户任务 | 注入任务 |
| --- | --- | ---: | ---: |
| AgentDojo / `ipi` | Workspace / `workspace` | 40 | 14 |
| AgentDojo / `ipi` | Travel / `travel` | 20 | 7 |
| AgentDojo / `ipi` | Banking / `banking` | 16 | 9 |
| AgentDojo / `ipi` | Slack / `slack` | 21 | 5 |
| AgentDyn / `ipi-agentdyn` | Shopping / `shopping` | 20 | 9 |
| AgentDyn / `ipi-agentdyn` | GitHub / `github` | 20 | 9 |
| AgentDyn / `ipi-agentdyn` | Daily Life / `dailylife` | 20 | 10 |

AgentDojo注册用户任务合计97，AgentDyn合计60。这是原生clean范围，不是本次模型成绩。计数、攻击列表和预估任务来自当前活动后端。来源、版本和revision按[AgentDojo锁](../config/agentdojo.lock.json)与[AgentDyn锁](../config/agentdyn.lock.json)的元数据核对；不扫描源码内容，runtime_variant=unverified。

页面和 `/api/config` 在安装缺失、未知来源或revision/路径不符时仍可打开，返回 `benchmark_id=unknown`、`backend_ready=false`、空 `suites`/`attacks` 和 `backend_error`；预计任务显示“未加载”，启动按钮禁用。`/api/run` 在创建模型客户端前拒绝请求，后台任务也复核提交时身份；历史分析仍可使用。后端校验通过时，场景仅限当前环境；不能把 AgentDojo 场景提交给 AgentDyn 进程，反之亦然。

`/api/config` 的 `tool_metadata_path` 与 `tool_metadata_selection` 报告实际选中的风险目录、来源和归属。明确路径/环境覆盖、后端专属 local 目录、已识别的通用 local 副本及内置目录按现有解析规则选择。若旧 `config/tools.local.toml` 是另一基准的已识别目录副本，会跳过并提示 `warning`，保留原文件，使用活动后端内置目录。无法归属的自定义通用目录不会被静默套用；`tool_metadata_error` 单独报告风险配置错误，不把已验证后端改标为未知。原生 baseline 不使用 DSCG 风险目录；DSCG 在创建模型客户端前检查实际工具覆盖与分类。高级设置中的显式路径仍可覆盖默认选择。

## 防御结构

当前引擎为 **three-layer-v3.1**；页面与API从引擎常量读取版本，实验页顶部“防御架构”已同步当前规则。图中三层为：L1 工具返回隔离、L2 可信任务工具授权与候选前置检查、L3 当前动作语义审计；Monitor 与一次性票据单列为执行基础设施。L2 编译后只展示有效已授权工具；有限明确文件/唯一邮件/指定网页任务先受监控读取，再形成完整有效任务供规划和L3使用。L1保留此前明确原生银行月支出任务的六字段投影规则；这不是 AgentDyn 三场景专门优化。AgentDyn 三场景不因切换基准扩大投影适用域，其他工具结果继续保留来源封装；原文继续供日志/L3。投影模式off/shadow/projected可由API/partial设置，网页当前无独立选择器。普通工具结果通过 L1 进入主模型，后续候选先检查 L2 再路由 L3。

v2.2的L1日常输出概述无关指令、L3同时审查外发正文，已在控件、预览和架构图说明；用户明确要求的安全分析/必要引用仍保留。最终自然语言回答仍无独立强制审计，router off仍运行原L3。预览按实际开关显示授权工具视图和委托任务分支；历史运行保持各自版本，不按当前引擎重标。

该图描述完整防御的基础配置。实验配置支持 L1/L2/L3 独立消融，L2 候选前置检查、授权工具视图、显式任务文件展开可分别关闭，NoL2下三项全部无效。宿主授权profile仅API可配，网页默认原编译策略。预设包含完整三层、移除任一层、V2 风格对照（关闭 L1、前置、工具视图与任务展开，保留新版目录复核、授权与审计；不是历史V2精确复现）和自定义组合。L2/L3 全关时 L1 随之关闭；该 DSCG 消融仍经过 Monitor，不等同于原生 baseline。切换原生 baseline 后 DSCG 控件不参与运行。审计重试为 0，完成提示关闭；L3 纯算法路由已接入 API默认off；full/partial DSCG CLI默认shadow，baseline/NoChecker默认off；网页专门模式/artifact控件和真实校准尚未完成。授权对照校准尚未实施。

非法混合批次整体拒绝，不执行其合法成员；Monitor 重新检查前置结果与当前授权/目录。L1 不增加模型调用，但会增加历史输入；已有单次144条模型结果和定向修复验证，仍没有可归因的L2单变量收益或通过真实E0的结论；最新成本标记不可直接比较。当前约束仍是工具级，对象、目的地、参数与数据权限未强制约束。AgentDyn 的 `browse_webpage`、`input_to_webpage` 会派发实际网页处理逻辑，可能修改账户/文件/仓库、发送邮件或转账，不能因名称含“浏览”就视为只读。内置 [AgentDyn 风险目录](../config/tools.agentdyn-v1.2.toml) 对共享名称按实现的保守副作用并集处理，不赋予只读免审；单一 effect 字段记录主导风险，不描述每种具体行为。现有工具级检查不限制 URL/域名、具体页面处理器或工具内部对象及副作用，也不保证阻止浏览器模拟环境中的全部操作。新运行应使用新名称，历史页面保留旧版本结果。

## 实验配置与工作台

配置依次按评测对象/模型、场景/攻击、防御组合分组，启动按钮固定在配置栏底部；窄屏可直接跳到工作台或返回配置。API 连接、工具风险目录、日志级别和子集 seed 收在高级设置。默认 summary；standard 保留判决与动作记录，full 增加完整诊断开销。攻击列表来自当前已验证安装中的原生攻击注册表，网页使用单一定向攻击；交互 manual 和使用独立分母的 DoS 不在此入口。

任务上限 0 表示全部。网页有限子集继续按 seed 排序，partial CLI 使用注册顺序前缀；跨入口比较需要核对已保存的 task_selection 中实际 IDs。预计任务按已选场景和上限计算：含攻击时为用户任务数 × 注入任务数，良性评测仅计用户任务；网页每次选择一个攻击。预计任务不含攻击生成阶段的额外预检。

工作台顶部是**待启动配置**，结果概览中另列**本次实际配置**。选择已保存运行后查看 TSR、ASR、任务数、缺失安全判定及成本。新汇总按有效utility分母加权 TSR、按有效布尔安全判定加权 ASR；良性评测的 ASR 不适用。旧结果只在逐任务记录完整且唯一时恢复有效 ASR 分母，否则显示未记录，不把缺失当作零。原始历史文件不改写。若同一结果内出现不同已记录基准或任务目录，聚合指标与分母保持空值，并标记 `aggregation_warning=benchmark_or_catalog_mismatch`。

概览、图表、对比和报告的 Token 统一合计主模型（含授权和攻击预检）与审计模型。旧结果缺审计使用量时仅显示已记录成本，不推定审计为零。三层记录展示 L1 重复呈现/新增字符、L2 允许/拒绝批次、L3 公开读取免审/语义调用，并列出 trace 覆盖数。L2新增实际完整/可见工具累计数、编译器调用与任务文件展开数；编译器调用不是授权模型调用，纯读路径仍可能零模型调用。缺少旧字段保持未记录，不补成零；有效任务新增字符不是Tokens。仅统计已计分任务，排除攻击生成预检；字符数不是 Token。没有记录的历史统计标为未记录。

新网页运行ID自动带agentdojo_或agentdyn_前缀。配置、summary、整体结果和报告记录benchmark的id、repository、revision、suite_version、package_version、source_kind、verification_mode=metadata_only、runtime_variant=unverified。新记录不生成实现/目录/组件源码哈希；历史字段保持原样。

运行进度按已完成场景显示，不推断任务级完成百分比。断开实时日志不会终止后台评测。结果概览区分L3开关与保存的选择性路由模式，并列出L1/L2/路由trace覆盖。若汇总明确标记 `cost_comparison_ready=false`，提示已记录用量不能直接代表全程成本或节省比例。历史离线验收见[实施报告](../workshop/completed/dashboard_framework_ui_20261010.md)，当前显示验收见 [v2.2平台报告](../workshop/completed/dashboard_v22_20261013.md)，源码/源记录复核见 [复核报告](../workshop/completed/l2_docs_sync_20261013.md)。

## 历史对比

1. 选择实际结果目录，例如 `partial_benchmark/` 或 `benchmarks/`。
2. 在“基准”中选择 AgentDojo 或 AgentDyn，默认“全部基准”。选项来自当前目录中的已记录身份；未知记录显示“未记录基准”，冲突或不完整身份显示“混合／身份不完整”，不从目录名称或当前环境补写身份。
3. 多选模型/运行名称，如 baseline 与优化版本；清空选择时不会自动恢复全选。
4. 选择攻击和场景，核对已记录基准版本、任务目录、实际任务 ID、模型配置与计分口径。
5. 在结果列表勾选需要比较的运行，再生成图表或下载分析数据。

目录、基准、模型和攻击联动，失效选项按层级重置。更新筛选默认勾选全部匹配结果；自动刷新保留有效筛选和手动排除项。分析与导出只使用当前可见且勾选的结果。

同一模型/运行名称在列表、图表和明细中共用颜色与字母标记；多攻击对比另用攻击编号、点形和线型。顶部图例突出版本名，完整身份保留在提示和导出中。TSR、ASR 分图展示，Token 使用独立尺度；超过 6 个对比项时图表改为单列，窄屏纵向排列。颜色与标记在同次加载中保持一致，不跨重新加载持久化。

支持当前 CLI 的 `<结果目录>/<benchmark>/<model>_<name>/<attack>/<suite>/`、旧扁平 `<结果目录>/<model>_<benchmark>_<name>/<attack>/<suite>/`、网页 `dashboard/<benchmark>_<时间>_<短ID>/` 和旧目录结构，不迁移原始数据。历史场景筛选和图表按实际记录生成，因此旧四场景和新三场景的记录均可读取，不按当前环境重标。缺失基准身份时保留 `benchmark=null`、`benchmark_id=unknown`；相互冲突的身份标记 mixed。攻击缺失显示“未记录攻击”，旧混合攻击汇总仍显示“混合攻击”。未知身份的旧目录供历史查看/导出，不自动补写身份，也不作为新运行或跨基准续跑的依据；新实验使用新名称。

历史分析返回 `paired_comparison_ready` 与 `comparison_warnings`：只有完整、相同的已记录基准身份及任务选择通过这一对齐检查。身份缺失、不同基准或不同任务目录不能合并分母或计算配对收益；历史图表仍独立显示各运行，热图仅对齐相同已记录身份及任务选择的行。工作台运行对比会拒绝未对齐的多运行请求。此检查不证明模型、攻击投递或宿主 oracle 一致，筛选攻击相同也不等于任务 ID 相同。

## 下载分析数据

点击“下载分析数据”即可获取 ZIP，无需先画图；下载始终同时包含 ASR 与 TSR。

| 文件 | 内容 |
| --- | --- |
| `analysis.json` | 结构化分析入口：来源和已记录 benchmark 身份、任务选择、对齐状态、指标、逐任务 outcome、分子/分母及缺失/截断告警 |
| `summary.csv` | 实验与场景指标对比 |
| `task_records.csv` | 带已记录benchmark身份的明细；旧哈希保留，新记录为metadata_only，供核对后按任务 ID、模型、攻击对齐 |
| `README.md` | 指标口径和限制 |

百分比为 0–100；缺失值为空。明确报错的明细不计入观察性 ASR/TSR 分母，旧记录可能为 unknown。原汇总和明细统计分开保存；每次最多导出 50,000 条明细，并标明截断。导出不含完整工具轨迹，也不能独立证明 E0 通过或框架有因果增益。

历史实现验收见[归档索引](../workshop/archive/project_structure_20261008/README.md)；当前对应源码在 [dashboard/](../dashboard/)。2026-10-18 双后端接线分别在 `ipi` 与 `ipi-agentdyn` 通过 47 项 Python dashboard 检查，Node 历史/UI 检查 41 项通过，并完成两边实际目录、风险选择和启动 ID 的无模型探测；[验证记录](../workshop/artifacts/20261018_dual_benchmark/dashboard/dashboard_validation.json)保留命令和哈希。检查没有模型调用或计分 rollout，未执行图形浏览器布局验收，不证明模型效果、E0 通过或防御收益。

运行错误保留原始轨迹，派生效用/安全标签为null并标记infrastructure_error，不作为攻击成功或防御成功；总任务数、有效分母、错误数和Token分别保留。分析下载schema2保留记录中已有的任务/环境/攻击/工具哈希；新记录不生成这些源码哈希；身份不明的单个场景也不会继承相邻场景的身份。

CLI的新后端子目录（如`partial_benchmark/agentdojo/qwen3.7-flash_baseline/`）由历史页递归读取，分组保留后端和实际相对路径。原扁平目录仍独立可读，不把同名新旧运行或两个后端自动合并。网页发起实验的dashboard保存结构不变。
