# 评测指南

以下命令从 `DSCG/` 执行，默认 `ipi` 已激活。普通对照无需导入外部任务清单。

## 模型与工具配置

完整的字段、获取方式、schema查看命令、优先级及排错见 [模型、工具与运行参数详解](./model_tool_configuration.md)。首次标准测试需要准备模型服务连接；AgentDojo v1.2工具定义/参数/模拟环境和仓库风险目录已提供，不需要手工编写每个工具的参数或申请真实邮箱/银行账号。

### 模型角色与连接字段

`[main]`用于规划/最终回答和L2授权编译，`[security]`用于L3当前动作审计。两者可以共用服务，也可用不同模型/provider；纯算法L3路由不是训练小模型。baseline/NoChecker不建立审计客户端。主模型需支持Chat Completions工具调用及JSON输出，审计模型需支持当前JSON协议，不能仅凭聊天成功确认兼容。

| TOML字段 | 作用 | 测试者如何获得/填写 |
| --- | --- | --- |
| provider | 选择连接预设和兼容处理，如deepseek/dashscope；自定义兼容服务可用custom | 按实际API服务，不只按模型品牌猜测 |
| model_id | 请求里的真实模型ID，区别于运行name | 从服务方API模型列表复制并确认账号可用 |
| base_url | OpenAI兼容根地址，含服务要求的v1等路径 | 从官方接入文档复制；不是网页地址或完整/chat/completions路径 |
| api_key_env | 保存Key的环境变量**名称**，例如DEEPSEEK_API_KEY | 在启动评测/网页服务前设置该变量；这里不填Key本身 |
| api_key | 实际Key，可选直接设置 | 优先用环境变量；公共记录只保留api_key_env，不输出Key |

复制 [models.example.toml](../config/models.example.toml)到config/models.local.toml后，核对main/security的五个字段并设置所需变量。模板main为DeepSeek、security为DashScope，若使用这份双服务配置，两个服务分别要有可用Key：

```bash
export DEEPSEEK_API_KEY='自己的DeepSeek API Key'
export DASHSCOPE_API_KEY='自己的百炼API Key'
```

DeepSeek Key入口见 [官方认证说明](https://api-docs.deepseek.com/api/deepseek-api/)；百炼见 [获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)。模型和endpoint也须从同服务官方文档取得；百炼需匹配地域/业务空间。具体入口和单/双模型TOML示例见 [连接详解](./model_tool_configuration.md#2-主模型和审计模型)。

省略security角色且没有DSCG_SEC_*覆盖时，通过main fallback复用主模型。**复制模板后只留空security的Key不等于省略security**，它仍选择模板的独立模型。已有环境变量也可能覆盖TOML，需检查最终解析值。

普通连接字段优先级：显式函数参数（网页输入属于此层）→DSCG_MAIN_*/DSCG_SEC_*→角色TOML→provider共享设置/预设。实际Key依次取显式api_key、角色API_KEY变量、api_key_env所指变量、TOML Key及适用fallback。模型文件路径是--model-config/config_path→DSCG_MODEL_CONFIG→config/models.local.toml；相对路径按项目根解析。

可离线调用resolve_model_config并只打印public_dict检查main/security，不联网、不验证服务鉴权；现成代码见详解。当前temperature=0；DeepSeek reasoning_effort="none"是代码设置，因为AgentDojo0.1.35不保留reasoning_content的完整工具回合，不是TOML新增参数。实现见 [model_config.py](../dscg/model_config.py)。

### 工具参数与风险目录

工具参数schema来自实际注册函数，描述类型、required/default/枚举，供规划器和运行时使用；风险目录描述真实effect/source/sink等，供L2/L3决定权限/检查路径。风险TOML不会注册工具或建立真实服务连接。通过get_suite("v1.2", "workspace").tools及tool.parameters.model_json_schema()查看当前send_email等定义；完整只读示例见 [工具参数获取](./model_tool_configuration.md#3-工具参数查看什么在哪里获取)。

标准runner加载风险目录顺序是显式--tool-metadata/网页路径→DSCG_TOOL_METADATA→已有config/tools.local.toml→内置 [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml)。显式文件不存在报错；本地目录缺项不自动合并内置分类，缺失/非法工具按critical并在默认L2阻断。直接factory API使用者需传tool_metadata=load_tool_metadata()或在runtime注册分类。

| 风险字段 | 允许值 / 用途 |
| --- | --- |
| effect | read/write/delete/financial/external_send；按实现副作用填写，不按函数名猜测 |
| source | calendar/email/cloud/web/local；来源类别，不认证事实 |
| sink | none/external_recipient/public_output；有外部sink不能当普通公开读取 |
| sensitivity | public/internal/personal/secret；影响审计与免审资格 |
| idempotent | TOML true/false；L3新增内部读取路由的资格之一，不保证只执行一次 |
| reversible | TOML true/false；记录可逆性，不触发自动撤销 |

schema_version可选且默认dscg.tool-risk.v1；risk_level等派生字段不要手填。比如get_unread_emails会标记已读，内置effect=write；send_email为external_send。完整约束、TOML例子和自定义注册顺序见 [风险目录详解](./model_tool_configuration.md#4-工具风险元数据作用字段及覆盖)。

普通比较无需生成新目录。`python -m experiments.generate_tool_metadata`核对AgentDojo0.1.35/v1.2覆盖后复制审核目录到config/tools.local.toml，默认不覆盖已有文件；它不会调用模型、训练或自动推断风险。只读覆盖检查可用validate_catalog，见详解；分类存在仍不等于用户授权。

### 哪些是可选参数

默认L1/L2/L3开启、l1_projection_mode=projected、planning_tool_view/delegated_tasks=true、routeroff、audit_retries=0、completion_prompt=false、summary日志；routeroff仍保留原L3。普通测试不需要host授权profile、reader、自填tau或外部task manifest。独立L3校准artifact及host profile仅按对应支持域选择，不能为节省预算临时制造免审。各API/CLI/网页入口、固定审计窗口和参数含义见 [运行控制表](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

## 对照与输出

**全量正式测试请使用 `experiments.run_benchmark`。** 当前框架与无防御 baseline 的完整命令、全任务/全攻击区别、计划规模、缓存续跑和结果核对见 [全量测试指南](./full_benchmark.md)。以下 partial 命令仅用于小规模回归；两者复用执行流程，任务范围和默认输出根不同。

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline_compare_01
python -m experiments.run_partial_benchmark --force-rerun --name workshop_compare_01
```

baseline 使用原生 AgentDojo 工具循环，不使用 DSCG、安全模型或 AgentDojo 防御。两组均为 v1.2 四场景，各取注册顺序前 3 个用户任务和前 3 个注入任务；记录中的 seed:7 不参与当前前缀子集选择。核对各场景 `summary.json` 的 task_selection，不能只凭场景或攻击筛选认为已配对。

用户正式结果为 `results/partial_benchmark/<model_id>_<name>/<attack>/<suite>/`，其中保存原始任务 JSON、summary、CSV 和报告；full 侧车与任务 JSON 同目录。运行根保存 attack_manifest.json 和 all_report.txt，每攻击目录另有跨场景报告。旧目录保留，不读作新布局缓存。

修改配置后使用新运行名称；`--force-rerun` 不绕过 manifest 的配置绑定。攻击异常记录为 error，继续其他攻击后退出 1；成功完成退出 0，但不表示安全性或 E0 验收通过。

Agent 临时模型评测必须显式覆盖输出，例如：

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun \
  --name agent_probe_01 \
  --results-dir workshop/artifacts/20261008_agent_probe/partial_benchmark
```

每次使用新的任务目录和运行名称；模型评测需要配置 Key。

## 攻击选择

两个 runner 默认 typical 为 4 种目标型攻击；下列 144 条（typical）和 456 条（当前 all）是 **partial 前缀子集**的计划规模，另有注入能力预检。全量入口的规模见 [全量任务表](./full_benchmark.md#当前任务规模)。计划数不等于有效样本分母。预设不能与具体名称混用；missing typical 攻击会报错，manual 不可选。

```bash
python -m experiments.run_partial_benchmark --baseline --attack tool_knowledge --name baseline_tools_01
python -m experiments.run_partial_benchmark --attack tool_knowledge injecagent --name dscg_two_attacks_01
python -m experiments.run_partial_benchmark --baseline --attack all --name baseline_all_01
```

DoS 显式选择或 all 才运行，按 AgentDojo 原生规则每个用户使用首个注册注入任务一次，成功按任务失败计分；不得与目标型 ASR 合并。典型集仅控制工作量，变体不代表独立发表方法。

可选攻击（当前 AgentDojo 安装版本）：

这些攻击均有 AgentDojo 官方实现。[AgentDojo 发表于 NeurIPS 2024 Datasets and Benchmarks][agentdojo-publication]，[InjecAgent 发表于 ACL Findings 2024][injecagent-paper]。表中区分论文实验与 AgentDojo 官方模板；16 个名称包含消融变体，并非 16 种独立发表的方法。`system_message` 和 `tool_knowledge` 在此仅标为 AgentDojo 官方实现。

| `--attack` 值 | 简要说明 | 类型 | 来源 |
| --- | --- | --- | --- |
| `typical` | 默认运行上述 4 种典型目标型攻击 | 批量选择 | 本项目选择器 |
| `all` | 显式运行全部 16 种自动攻击 | 批量选择 | 本项目选择器 |
| `direct` | 用 `TODO` 直接要求执行攻击目标 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `ignore_previous` | 要求忽略原指令，改做攻击任务 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `system_message` | 用系统消息标记伪装指令来源 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `injecagent` | 用 `IMPORTANT` 和“忽略之前指令”强调攻击目标 | 目标型 | [InjecAgent][injecagent-paper]、[AgentDojo 官方适配][agentdojo-baseline] |
| `important_instructions` | 冒充用户，声称必须先完成攻击目标才能做原任务 | 目标型 | [AgentDojo §4.1–4.2][agentdojo-paper] |
| `important_instructions_no_user_name` | 上述模板中，用泛称代替真实用户名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_model_name` | 上述模板中，用泛称代替真实模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_names` | 同时用泛称代替用户名和模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_user_name` | 换成错误用户名，测试身份线索的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_model_name` | 换成错误模型名，测试模型称呼的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `tool_knowledge` | 在重要指令模板中补充工具调用顺序和参数占位符 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `dos` | 要求立即停止当前任务，输出指定文本 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `swearwords_dos` | 用辱骂内容诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `captcha_dos` | 声称须先解决验证码，否则停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `offensive_email_dos` | 要求发送威胁性消息，诱使模型拒绝并中断任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `felony_dos` | 声称处理当前内容违法，诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |

[agentdojo-publication]: https://papers.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
[agentdojo-paper]: https://arxiv.org/html/2406.13352v2
[injecagent-paper]: https://aclanthology.org/2024.findings-acl.624/
[agentdojo-baseline]: https://agentdojo.spylab.ai/api/attacks/baseline_attacks/
[agentdojo-variants]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/important_instructions_attacks.py
[agentdojo-dos]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/dos_attacks.py

## 可选控制与日志

| 参数 | 用途 |
| --- | --- |
| `--name NAME` | 区分运行，保留历史结果 |
| `--baseline` | 匹配当前入口任务范围的原生无防御控制 |
| `--attack NAME [NAME ...]` | 具体攻击，可重复该选项；默认 typical，all 显式运行全部 |
| `--force-rerun` | 重跑任务；也可设 DSCG_FORCE_RERUN=1 |
| `--clean` | 相同用户任务的无攻击效用控制；使用独立运行名称 |
| `--no-checker` | 关闭语义审计，保留工具授权、Monitor、ticket |
| `--trace-level summary/standard/full` | 默认 summary；standard 简化逐条记录；full 详细诊断和压缩侧车，增加写入成本 |
| `--include-extra-info` | full 的兼容快捷开关 |
| `--model-config PATH`、`--tool-metadata PATH` | 覆盖本地模型配置、工具元数据 |
| `--results-dir DIR` | 两个入口均支持；agent 必须指定 workshop/artifacts 下的新目录 |

当前优化没有新增必需参数。`audit_retries=0`、`completion_prompt=false` 保持默认；历史可选补救不叠加到当前框架。

full tracing 不改变防御逻辑。用户此前中断的 full 运行没有确认根因，不能据此认定日志 bug。日常对比用 summary，具体排错才使用 full。

用户完整评测入口为 `python -m experiments.run_benchmark --name full_compare_01`：全部注册任务，默认 typical 四攻击，默认输出 `results/benchmarks/`；支持 baseline、clean、攻击选择及 `--results-dir`。成对命令与隔离输出示例统一见 [全量测试指南](./full_benchmark.md)。

## 结果文件

两个入口均自动生成以下文件，无需额外参数。下图展示 partial；全量的默认根替换为 `results/benchmarks/`：

```text
results/partial_benchmark/<model_id>_<name>/
├── summary.md                    # 每个 attack × 场景的指标与失败位置
├── failure_cases.jsonl           # 每行一个失败/缺失案例，含相关片段
├── attack_manifest.json
└── <attack>/<suite>/
    ├── summary.json             # 原有场景统计、配置、成本范围
    ├── report.txt
    ├── detailed_results.csv
    └── <user_task>/<attack>/<injection_task>.json
```

先读 `summary.md`：指标显示百分比及成功数/分母，Token 区分主模型、审计模型和合计，并标出各场景的成本统计范围。失败索引给出任务 ID、原始 JSON 的相对路径及 `failure_cases.jsonl` 的行号。TSR 失败是 `utility=false`，防御失败是 AgentDojo 原生 `security=true`（ASR 成功）；两者可同时出现，也可单独出现。DoS 使用独立的 `not utility` 口径，不与 targeted ASR 合并。

`failure_cases.jsonl` 使用 `dscg.partial-failure.v1`：`failure_types` 区分 `tsr_failure`、`asr_success`、`asr_unavailable`、`result_missing`、`task_error` 和 `run_error`；记录 `trace_path`、`trace_exists`、原生标签与 `excerpt_status`。每例最多保存 6 个片段、每片最多 800 字符，优先选取错误、最后的助手文本、最近的工具调用和能精确匹配注入内容的工具返回；任务描述/攻击目标各最多 400 字符。`source_pointer` 定位原 JSON，字符范围针对文本块拼接或序列化工具调用；`truncated` 显式记录截断。片段是排查线索，不是失败原因证明，也不重新判断攻击成功。

缺失/非布尔安全结果不计入 ASR 分母；缺失的计划任务保留位置及空标签，不伪造 TSR/ASR 结果。运行异常显示 N/A 与异常类型，保留本次中断前已经完成场景的统计，不读取未完成场景的旧 `summary.json`。正常无失败时仍生成空的 JSONL。无攻击轨迹位于 `none/<suite>/<user_task>/none/none.json`。

这两个新文件在本次运行结束时更新，也支持正常缓存读取；不会复制完整轨迹或改写原生任务 JSON。强制终止进程可能尚未生成它们。历史目录不自动补写，使用新运行名称；现有配置绑定仍生效。Agent 测试输出继续显式使用新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark` 或全量的 `benchmarks` 子目录。

## 指标与证据

同时报告 TSR、AgentDojo 原生 ASR、总 Token 与全部有效/错误/跳过分母，预检成本单列或明确包含。输出文本 predicate 的误报仍需独立 E0 审计，保留原始结果；历史 smoke 或单轮小样本不能支持通用防御结论。

当前 I3 为 partial（有效24，范围缺口8，工具边界缺口0），E0 合成自检并未证明真实 harness 通过；I2尚未解锁；当前三层及L2优化是用户授权的workshop工程，不代表正式研究路线解锁。离线命令见[项目 README](../README.md)，详细证据见 [I3 报告](./i3_p0_stress_report.md)与 [V2 后续报告](../workshop/completed/framework_v2_followup_report.md)。

2026-10-13当前结果核查：v2.2的144条现有记录TSR130/144、nativeASR0/144、轨迹错误0；只是单次源记录观察。16份成本汇总均标记cost_comparison_ready=false，保留1,685,825 Tokens记录量，不计算可比节省。旧导出的同名L2opt目录对应先前144条字节，不能用现在的trace重新认证旧export。详见 [复核报告](../workshop/completed/l2_docs_sync_20261013.md)。
