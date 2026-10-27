# Dashboard

从 BaseIntent 根目录启动目标环境：

```bash
conda activate ipi
# AgentDyn 改为 conda activate ipi-agentdyn
python -m dashboard.app
```

默认 [实验配置](http://127.0.0.1:8888/) 与[历史分析](http://127.0.0.1:8888/history)。需要另一端口可用 `PORT=8889 python -m dashboard.app`。切换终端环境不会改变运行中的服务，需重新启动目标服务并刷新页面。用户启动的实验保存在 `results/dashboard/`。

## 配置与执行

后端由实际导入路径、来源、版本和 revision 识别。AgentDojo 提供 workspace/travel/banking/slack，AgentDyn 提供 shopping/github/dailylife。校验仅为安装元数据，不认证运行时源码或远端服务。后端不可用时配置页/历史页仍可打开，显示原因并禁用启动，调用模型前再次校验。

页面使用共享生产 factory，当前框架为 BaseIntent。L2 两次调用、冻结全局工具与固定 ID 进度关联、宿主事件进度、L3 和 Monitor 说明见[框架](framework.md)。页面默认 API 路由 off；CLI 默认 shadow。注册/授权/schema 有效的 public/internal 读取在所有模式固定免审，阈值无法收紧，不按 sink、URL 或对象隐私筛选。off 不关闭 L3。专用路由模式/校准控件不等于已经提供的功能。

选择原生 baseline 时运行对应后端原生循环，防御控件不参与；BaseIntent 消融仍可能经过 Monitor，不能当作原生 baseline。NoL2 关闭自动意图流，NoChecker 保留 L2/进度。审计重试默认 0，完成提示默认关闭；以保存的实际配置为准。L1 投影只有现有银行有限 profile，AgentDyn 没有新增 profile。

网页任务上限 0 表示全部，子集由 seed 排序；partial CLI 使用注册前缀，二者需要核对实际 task_selection IDs。预计任务不含额外 GOAL 请求，也不是有效分母或 Token 估算。断开日志不会停止后台任务。

## 结果与历史比较

工作台区分待启动配置与本次实际配置。TSR 按有效 utility 加权，ASR 按有效原生 security 加权，clean 不适用；API/工程错误、缺失判定和不支持分别显示。缺失历史字段保留未记录，不能补成零或按当前版本重标。

历史页读取当前按后端分层和旧扁平布局，不移动或重写数据。先选结果目录，再选实际记录的后端、运行、攻击和场景；仅当前可见且勾选项参与图表/导出。未知或冲突身份保持 unknown/mixed，不能从目录名或当前服务补写。

配对比较检查已记录后端与实际任务选择，未对齐不得合并分母；这不额外证明模型服务、投递与评分 oracle 一致。成本合计实际主模型（含授权/progress）和审计 usage，GOAL 与计分分开；缺失成本保持未知。若 `cost_comparison_ready=false`，已记录 Token 不能代表完整节省。

新执行使用 `.baseintent.jsonl` 与 `.baseintent.responses.jsonl`，历史 DSCG 附件只读兼容。报告、失败索引和原文引用与 CLI 使用共享读取契约。详见[结果说明](result_files.md)与[迁移](migration.md)。
