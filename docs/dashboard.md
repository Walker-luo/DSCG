# GrantBind Dashboard

## 启动与后端

```bash
conda activate ipi              # 测试服务器使用 DSCG
python -m dashboard.app
```

打开[实验配置](http://127.0.0.1:8888/)或[历史分析](http://127.0.0.1:8888/history)。按当前进程实际安装识别后端，当前实验使用 AgentDojo；切换终端环境后须重启服务。另一服务可用 `PORT=8889 python -m dashboard.app`，各自保持后端身份。

未知安装时页面／历史仍可用，`/api/config`返回backend_ready=false、空场景／攻击和backend_error，新实验在模型创建前拒绝。风险目录错误通过tool_metadata_error单列；baseline不加载防御风险目录。配置优先级见[模型与工具](model_tool_configuration.md)。

## 防御结构

页面展示 **GrantBind v3.7**，运行配置和导出记录沿用版本标识 `DSCG_v3.7`。普通网页默认static：L1规划视图、L2静态任务视图与全局授权、L3当前动作审计与Monitor／票据。

页面默认使用 `static-task-v354`，尚无 prompt profile 选择控件。API 可显式传 `prompt_profile=legacy` 做单次授权对照，NoL2／NoChecker 要求 router off。运行名称不选择策略。默认配置见 [配置指南](model_tool_configuration.md#消融与默认值)。

支持三层开关及工具视图／有限委托控制。NoL2 关闭相关前置、视图和委托，L2／L3 全关时 L1 关闭；baseline 走独立原生循环。当前 NoL2 有工具元数据初始化缺失，结果解释见 [当前问题](framework_updates.md)。

API router默认off，但仍运行非免审L3；无sink public/internal读取固定免审，personal/secret及外部接收方读取仍审计。路由／静态视图没有新增页面选择器。最终文本无独立动作审计；工具级控制不保证对象隐私或参数安全。详细机制与层间共享数据见 [架构说明](architecture.md)。

## 实验配置与工作台

按模型、场景／攻击、防御组合设置；连接、风险目录、日志和seed在高级配置。任务上限0为全部；网页子集按seed选取，**不同于partial CLI注册前缀**，跨入口比较须核对保存的task_selection。

工作台区分待启动配置与保存的实际配置；显示TSR／ASR、有效分母、错误、成本和层级trace覆盖。缺失历史字段显示未记录，不补零。main与security总Token按保存范围展示，GOAL与计分范围分别核对；cost_comparison_ready=false时不推断节省。

新实验保存在results/dashboard，ID带实际后端前缀。进度按已完成场景显示，断开日志不终止后台任务。后端元数据验证不认证源码或模型服务等价性；采样等实际请求配置从诊断核对。

## 历史对比

1. 选择结果目录、已记录基准、**模型**、模型／运行名称及攻击／场景。普通运行按记录里的`model_id`归组，`<model>/<name>`与旧的`<model>_<name>`布局都能把同一模型的多次运行归到一起。消融归档（`<backend>/ablation/<arm>/`）占用模型字段：模型下拉里直接选 `ablation`，臂名作为运行名，标题显示为「消融 · <arm> · <attack>」；消融的专项读取后续单独实现。
2. 勾选要比较的运行，核对后端身份、任务ID、模型／策略、筛选范围及实际任务键。
3. 查看独立TSR／ASR／Token图，或下载分析数据。

生成分析后，“整体测试数据”按攻击分组，每张卡片展示一个运行在所选场景的TSR、ASR成功数／有效数、百分比和已记录Token；合计按有效分母加权。ASR成功数若由已记录比率唯一还原会标注`*`；缺失计数或用量保持未知或标记部分已记录，身份不完整的多场景不合并。

新CLI后端分层、旧扁平目录和Dashboard历史均可读，不移动或合并同名运行。未知身份保持unknown，冲突标mixed，不从目录名、当前安装或相邻场景补写。不同后端／任务集合不能合并分母。

`paired_comparison_ready`与comparison_warnings标记身份／任务选择对齐情况；通过也不认证模型修订、投递或oracle一致。工作台拒绝未对齐的多运行对比；历史图独立显示，分析仅使用当前勾选结果。

## 下载分析数据

无需先画图，ZIP同时包含TSR与ASR：

| 文件 | 内容 |
| --- | --- |
| analysis.json | 实验、配置身份、任务选择、指标、逐任务标签与告警 |
| summary.csv | 实验／场景汇总 |
| task_records.csv | 可用于同键核对的逐任务记录 |
| README.md | 指标口径和限制 |

百分比0–100，缺失为空；明确错误行排除有效分母，旧未知记录仍标未知。每次最多50,000条明细并标截断；导出不含完整工具轨迹，原因分析仍需原始JSON／诊断。当前结果的解释边界与未解决问题见 [v3.7 当前问题](framework_updates.md)。
