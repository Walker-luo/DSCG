# 结果、诊断与评分

## 从哪里开始看

| 文件 | 内容 |
| --- | --- |
| `summary.md` | 实际配置、范围、每攻击/场景 TSR/ASR、有效分母、错误与 Token |
| `failure_cases.jsonl` | 完整失败/缺失索引；摘要中有限链接不减少这里的案例 |
| `l3_router_summary.md/.json` | 路由原因、实际模式、完整性及已知成本 |
| 场景 `summary.json` / `detailed_results.csv` | 原聚合和全部任务结果 |
| `attack_manifest.json` / `run_manifest.json` | 实际后端、任务/攻击与有效配置绑定 |
| `execution/<invocation>/execution.json` | 当前调用、攻击进程、状态和实际 wall time |
| 原生任务 JSON 与诊断附件 | 交互、原生评分、框架事件和原始有限回复 |

新 CLI 结果路径为 `<results-dir>/<backend>/<model>_<name>/`，Dashboard 使用 `results/dashboard/`。clean 的原生攻击组件仍为 `none`。保留原生路径以支持缓存/取证，不移动旧目录。新检查产物显式使用 `artifacts/<日期>_<任务>/`。

## 精简任务轨迹与独立诊断

新执行写 BaseIntent 侧车：

```text
<task>.json
<task>.baseintent.jsonl
<task>.baseintent.responses.jsonl
```

原生 JSON 保留交互、评分、错误、耗时及诊断引用；v2 诊断保存紧凑授权、意图、层路由、成本、最终审计和动作事件。不可变公开配置按攻击/场景去重，当前公开字段使用 `baseintent_*`。

L3/progress 的完整 content 或 refusal 在解析前保存到响应附件，包括畸形/不完整回复；立即绑定相对路径、attempt/response ID 和字节偏移。只保存允许的 finish/usage/latency/call/intent 字段，L2 只存解析授权。不保存隐藏推理、HTTP 头、SDK 对象、凭证或重复完整提示/工具正文。

宿主派生的 intent_id/status/completion_kind/next_intent_id/reason_code/host_facts 不是模型原始控制字段。`progress_source=host` 没有新 response_id，不能拿上一条模型回复当作本次原文；跳步列表保持为空。模型语义结果与 host 的事实/效果/回答标志分别记录。

程序读取使用 `baseintent.task_diagnostics.load_task_trace(path)`，在内存中合并，不改文件。兼容旧 inline、v1、gzip、`.dscg.jsonl/.dscg.responses.jsonl` 和 `DSCG_BLOCKED`，缺失/损坏/未结束或无效引用明确标记。旧字节和版本身份保持原样，缺失回复不补造、缺失成本不补零。详见[迁移](migration.md)。

cache 命中不生成模型回复、不重写旧文件；真实重跑追加新 attempt，当前引用绑定当前执行。策略/schema/模型/有效防御配置变化须新名称，无跨策略缓存或 cohort 自动迁移。

## 评分与错误

有效 TSR = utility=true / 有效 utility 布尔数；有效 ASR = security=true / 有效原生 security 布尔数。clean ASR 不适用。计划、尝试、完成、有效、错误、未完成和不支持分别报告，不把错误当成功防御。

已收到的已知 L2/progress 输出缺陷及有界无进展使用原生 `AbortAgentError` 停止，保留已执行效果和已有最终回答，再由原生谓词评分。未完成且攻击未成功可以是 False/False；框架终止也可能 utility=true。L3 deny/协议缺陷保留既有受限重规划。

API/超时、输入/目录/内部/I/O 错误及主模型畸形工具参数 JSON 属基础设施错误，效用/安全标签为空。参数不修补，畸形批次不执行。当前阻断层分别为 L2、L3、Monitor。安全错误诊断只记录允许的类型/代码/字段子码和有限栈位置，不保存请求、响应、局部变量或凭证。

## 成本与比较

generation、`authorization_intents`、`authorization_tools`、`intent_progress` 和 audit 按实际 usage 计数。GOAL 与计分分别统计，当前 invocation 与缓存/完整运行分别统计。已知 Token 是小计；缺失 usage、连接失败服务成本和不完整附件保持未知。

固定 public/internal 读取在所有模式免审，不能用旧 shadow 候选数量推定当前实际节省；阈值扫描不改变当前规则。工具级免审不证明目的地或对象安全，见[框架边界](framework.md)。

比较前对齐已记录的后端、实际任务 ID、攻击、模型/请求配置及评分口径。`paired_comparison_ready` 只报告已记录范围的对齐，不证明模型服务、攻击投递和 oracle 同轮一致；`cost_comparison_ready=false` 时不计算完整成本收益。历史身份未知时保持 unknown，不按目录或当前环境补写。

## 只读汇总

已有目录可用 `python -m experiments.diagnostics.summarize_results --help` 查看路由报告生成选项。默认保护已有报告，显式刷新仅限该工具拥有的派生产物；不改原生评分、轨迹或历史模型回复。Dashboard 和 CLI 共用读取、分母与成本契约，完整失败索引优先于短摘要。
