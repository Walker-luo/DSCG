# DSCG

DSCG 是一个面向工具使用型 LLM Agent 的间接提示词注入（IPI）防御研究原型，基于 AgentDojo 评测工具动作、任务效用和运行开销。

当前实现以**工具级授权和执行完整性**为底座，LLM 安全审计提供补充信号。对象、参数和数据范围约束尚未实现；论文路线与工程验收以 [`../research/technical_route.md`](../research/technical_route.md) 和 [`implementation_status.md`](../research/paper/implementation_status.md) 为准。

## 防御流程

```text
可信用户请求 → 编译工具级契约 → 主模型提出动作
            → 安全审计（启用时）→ Reference Monitor 仲裁
            → 消费一次性 execution ticket → 真实工具执行
```

核心实现位于 [`dscg/pipelines/defended.py`](./dscg/pipelines/defended.py)：

| 模块 | 职责 |
| --- | --- |
| `OurFrameExecutor` | 在生成候选前编译授权；工具反馈后重新规划 |
| `PermissionSandbox` | 检查工具注册和白名单；未初始化、空策略或错误状态均拒绝 |
| `ActionSecurityChecker` | 输出结构化 `allow/deny/abstain`；`allow` 不增加工具权限 |
| `ReferenceMonitor` | 汇总策略与审计结果，记录动作状态并签发票据 |
| `TicketedToolsExecutor` | 唯一真实执行入口；验证调用指纹和票据的一次性状态 |

被阻断的动作返回工具错误，恢复时的新候选继续经过同一仲裁路径。一次性票据绑定具体调用，但不能约束已授权工具的全新调用所选择的对象或数据。

## 本轮框架优化

当前 V2 保持两层防御，无需新增配置文件或参数：

| 层 | 本次优化 |
| --- | --- |
| 工具授权 | 固定 `temperature=0`、排序工具目录，明确条件预订与已有支付更新；编译失败记录 `error_code` 并默认拒绝。授权只读取可信用户请求。 |
| 动作审计 | 提供当前任务最近 4 条工具返回，每条最多 2,048 字符，并标明不可信与截断；判断当前动作是否符合任务。合法查询可以获取未知事实，具体目标或网址仍需任务证据。 |

Reference Monitor 和一次性 ticket 沿用；默认每批一次审计，重审和完成提示保持关闭。缺少本地工具元数据时自动使用内置 [`config/tools.agentdojo-v1.2.toml`](./config/tools.agentdojo-v1.2.toml)，显式配置和已有本地配置优先。

最新[历史分析导出](./download/dscg-history-analysis-20261007T153203Z/analysis.json)覆盖 4 种典型攻击、4 个场景。三组的任务 ID、攻击和模型 ID 已对齐，每组 144 条：

| 版本 | 任务成功 TSR ↑ | 官方攻击成功 ASR ↓ | 总 Token ↓ |
| --- | --- | --- | --- |
| `baseline` | 118/144（81.94%） | 6/144（4.17%） | 1,735,456 |
| `workshop_new`（旧版） | 111/144（77.08%） | 6/144（4.17%） | 2,520,100 |
| `workshop_v2`（当前） | **122/144（84.72%）** | **5/144（3.47%）** | **2,077,620** |

V2 相比旧版多完成 11 条任务，总 Token 减少 17.56%；相比 baseline 多完成 4 条任务，总 Token 增加 19.72%。这是单轮观察结果；ASR 仅少 1 条命中，仍需逐条核查原始轨迹和重复对照。Token 按导出汇总统计，包含攻击预检成本。

导出的 432 条记录均标为 valid，无缺失或截断告警；该状态来自源结果，不代替 E0 独立载荷/终态审计。I3 仍为 `partial`（24 条有效样例中 8 个范围缺口），对象/数据权限与 I2 未实现。实现和历史试验保留在 [V2 实施记录](./docs/framework_v2_report.md) 与 [I3 报告](./docs/i3_p0_stress_report.md)。

### 对比测试命令

默认已进入 `ipi` 环境，沿用当前模型配置；不需要导入任务清单。默认运行 4 种典型攻击，每组 144 条，自动记录实际任务 ID 与运行配置。使用新名称保留已有结果：

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline_v2_control_r2
python -m experiments.run_partial_benchmark --force-rerun --name workshop_v2_r2
```

默认 `summary` 日志足够用于历史分析；`--trace-level full` 仅在排查具体决策时启用，会增加日志写入开销。可加 `--no-checker` 做授权层消融，或加 `--clean` 测无攻击效用控制，并使用独立运行名称。

在“历史分析”勾选 baseline 与 V2，选择相同攻击和场景，对比 TSR、官方 ASR 和总 Token；历史组仅作参照，模型服务版本未固定时不能仅凭差异归因。

## 安装与模型配置

在 `DSCG/` 目录执行：

```bash
conda env create -f environment.yml
conda activate ipi
cp config/models.example.toml config/models.local.toml
```

已有 `ipi` 环境可用 `conda env update -n ipi -f environment.yml` 更新。项目依赖 Python 3.10、AgentDojo 0.1.35 和 OpenAI-compatible Chat Completions 接口。

在本地 TOML 配置主模型与安全模型，例如：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
api_key_env = "DEEPSEEK_API_KEY"

[security]
provider = "dashscope"
model_id = "qwen-plus"
api_key_env = "DASHSCOPE_API_KEY"
```

设置对应的 Key 环境变量即可；省略整个 `[security]` 时复用主模型配置。自定义服务可填写 `base_url`，其他 Provider 见[配置模板](./config/models.example.toml)。`config/models.local.toml` 已被 Git 忽略，不要提交真实凭证。

配置优先级：函数参数 > `DSCG_MAIN_*` / `DSCG_SEC_*` 环境变量 > 本地 TOML > Provider 默认值。`DSCG_MODEL_CONFIG` 可指定配置文件路径，解析实现见 [`dscg/model_config.py`](./dscg/model_config.py)。当前 AgentDojo 适配层不保留 DeepSeek 的 `reasoning_content`，项目自动使用 `reasoning_effort="none"`；重建环境时还需核对消息角色兼容性。

Python 中可直接使用本地配置，并通过开关做消融：

```python
from dscg.pipelines.defended import make_defended_pipeline

pipeline, main_tracker, sec_tracker = make_defended_pipeline(
    use_sandbox=True,
    use_security_checker=True,
)
```

`use_security_checker=False` 对应 NoChecker；`use_sandbox=False` 对应 NoSandbox。原始基线入口为 [`dscg/pipelines/baseline.py`](./dscg/pipelines/baseline.py)。

## 运行与验证

以下命令默认已进入 `ipi` 环境，直接使用 `python`。

离线测试和 fixture 无需 API Key：

```bash
python -m unittest discover -s tests -v
python -m experiments.i3_p0_stress --output /tmp/dscg-i3-check.json
python -m experiments.harness_audit \
  --fixture tests/fixtures/harness_audit_cases.json --output /tmp/dscg-e0-check.json
```

I3 退出码：`0` 表示所有有效样本约束通过，按路线记 `no_go`；`1` 表示发现约束缺口；`2` 表示样本运行错误。当前预期为 `1`，回归测试通过不表示范围断言已成立。运行时使用新的输出路径，保留已有结果。

模型评测需先配置连接与 Key：

```bash
python -m experiments.run_partial_benchmark --name partial-check
python -m experiments.run_benchmark --name full-check
```

两个入口默认均启用完整 DSCG，覆盖 workspace、travel、banking、slack。partial 默认使用 `typical`：`ignore_previous`、`injecagent`、`important_instructions`、`tool_knowledge` 这 4 种典型目标型攻击；full 使用全部任务和固定的 `important_instructions` 攻击。结果分别保存到 `results/partial_benchmark/` 和 `results/benchmarks/`。正式实验需另行固定 manifest、模型、攻击、seed 和防御开关。

重新运行与 partial 相同任务的**无防御 baseline**：

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline-typical-20261007
```

该模式使用原生 AgentDojo 工具循环和当前主模型配置，不启用 DSCG、安全模型或 AgentDojo 防御。与防御版共用 v1.2 套件、每场景按注册顺序取前 3 个用户任务和前 3 个注入任务。目标型攻击每场景计划 9 个组合，默认 4 种攻击共计划 **144** 条攻击评测，另有注入任务能力预检。典型集覆盖指令覆盖、InjecAgent 模板、用户身份伪装和工具知识提示；这是控制测试规模的固定选择，不表示已验证攻击强度。

`--attack all` 可运行全部 16 种自动攻击，当前共计划 **456** 条。DoS 攻击须显式选择或使用 `all`；它们遵循 AgentDojo 原生规则，每用户只运行一次，ASR 按任务失败计算。计划数不等于有效样本数。

指定一种或多种攻击：

```bash
python -m experiments.run_partial_benchmark --baseline --attack tool_knowledge --name baseline-tools
python -m experiments.run_partial_benchmark --attack tool_knowledge injecagent --name dscg-two-attacks
python -m experiments.run_partial_benchmark --baseline --attack all --name baseline-all
```

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

partial 的单攻击和多攻击统一保存到 `results/partial_benchmark/<model_id>_<name>/<attack>/<suite>/`。例如 `--baseline --name baseline` 的 workspace 结果为 `<model_id>_baseline/<attack>/workspace/`，其中包含 summary/CSV/文本报告及原始任务 JSON；完整 trace 侧车与对应 JSON 同目录。新运行按此层级读取缓存，旧目录和结果保留。

`<model_id>_<name>/` 下保存 `attack_manifest.json` 和 `all_report.txt`；每个攻击目录下另有跨场景的 `all_report.txt`，不混合目标型与 DoS 的 ASR。攻击运行异常会记录为 error，并继续其他攻击，最终退出码为 1；全部运行完成为 0，不表示 harness 或安全性验收通过。

各场景 `summary.json` 的 `task_selection` 保存具体任务 ID，`defense: null` 表示无防御。当前 partial 保留的 `seed: 7` 字段不参与前 3 项选择，应以具体 ID 为准。比较时保持主模型配置和攻击选择一致，使用不同运行名称保留两组结果；旧版本若采用不同任务选择规则，需核对原始任务 ID。当前 AgentDojo 输出文本 predicate 的已知误报仍需 E0 审计，新增攻击入口不修改原始判定。

常用选项：

| 选项 | 用途 |
| --- | --- |
| `--name NAME` | 区分运行版本，避免复用其他实验的结果 |
| `--attack typical/all/NAME [NAME ...]` | partial 默认 typical；all 测全部，或指定一个/多个名称；预设不能与具体名称混用，非法选择在模型初始化前拒绝 |
| `--baseline` | partial 入口使用无防御基线，任务子集和攻击保持一致 |
| `--force-rerun` | partial 入口重新执行已有任务，不复用缓存 |
| `--trace-level summary/standard/full` | 默认 summary 用于日常对比；standard 保存简化逐条记录；full 保存详细诊断及压缩侧车，增加写入开销，不改变防御逻辑 |
| `--include-extra-info` | 等价于 `--trace-level full` |
| `--tool-metadata PATH` | 指定工具风险元数据 TOML；也可设置 `DSCG_TOOL_METADATA` |
| `--model-config PATH`、`--results-dir DIR` | partial 入口支持的配置与结果路径覆盖 |

工具目录可用 `python -m experiments.generate_tool_metadata` 生成，默认不覆盖已有本地文件；分类规则见 [`dscg/tool_metadata.py`](./dscg/tool_metadata.py)。评测默认可能复用缓存；partial 可用 `--force-rerun` 或 `DSCG_FORCE_RERUN=1` 强制重跑。调整实验配置时使用新的运行名称并保留原始结果。

启动 Web 面板：

```bash
python -m dashboard.app
```

默认地址为 [http://127.0.0.1:8888](http://127.0.0.1:8888)，可用 `PORT` 覆盖；结果保存到 `results/dashboard/`。面板支持实验配置、历史分析和图表。绘图脚本位于 [`experiments/plots/`](./experiments/plots/)，输出到 `docs/figures/benchmarks/`。

顶部 **实验配置** 与 **历史分析** 是并列页面；历史分析可直接访问 [http://127.0.0.1:8888/history](http://127.0.0.1:8888/history)。按 **结果目录 → 模型 / 运行名称（可多选）→ 攻击名称** 筛选。比较框架版本时，先清空模型，勾选 baseline 与改进版本，再选择同一攻击和场景，生成 TSR / ASR 对比或下载数据。每次更新筛选默认勾选全部匹配结果，也可在结果列表逐项取消；自动刷新保留当前选择。

目录沿用实际名称，如 `partial_benchmark/`、`benchmark/` 或 `benchmarks/`；新结果按 `<model>_<name>/<attack>/<suite>/` 分组，旧目录也可读取。攻击从已保存的汇总、CSV 或配置识别；缺失时显示“未记录攻击”，含多种攻击的旧汇总显示“混合攻击”。分析和下载仅使用当前勾选结果；比较改进前后时还需核对具体任务 ID 是否一致。验收见[独立历史页与模型多选报告](./docs/history_multiselect_page_report.md)。

桌面端左侧筛选、右侧分析；窄屏纵向排列。默认分别绘制 TSR 与 ASR，顶部图例突出 `baseline`、`workshop_new` 等版本名，可点击隐藏单项。同一模型 / 运行名称在列表、各图与明细表中共用颜色和字母标记，柱上也标出字母（含零值）；同时比较多个攻击时，另加攻击编号、点形和线型。对比超过 6 项时图表改为单列。完整运行名称与来源保留在提示和下载数据中。Token 使用独立的千单位轴；百分比范围为 −5%～105%，雷达图外圈为 110%。雷达图仅支持全部场景的百分比指标，散点图与任务热图使用固定指标。验收见[版本视觉区分报告](./docs/history_version_identity_report.md)。

在“历史分析”中勾选需要对比的实验、选择场景，点击 **下载分析数据** 即可下载 ZIP，无需先生成图表。下载同时包含 ASR 与 TSR，不受图表类型或指标选择影响：

- `analysis.json`：交给 agent 分析的结构化入口，包含实验来源、ASR/TSR 汇总、逐任务 outcome、明细分子/分母及缺失/截断告警。
- `summary.csv`：各实验与场景的指标对比；`task_records.csv`：按任务 ID、模型和攻击类型对齐的结果。
- `README.md`：指标口径、数据限制和 agent 分析建议。百分比统一为 0–100；缺失值保留为空，明确报错的明细不计入观察性 ASR/TSR 分母；旧记录状态为 unknown。

每个下载最多包含 50,000 条明细，截断与无明细场景会标注。原汇总与明细统计分开保存；下载结果不包含完整工具轨迹，历史 smoke 数据仍不能直接作为正式 benchmark 结论。
实现与验收证据见[历史分析下载报告](./docs/history_export_report.md)。

## 目录与研究交接

| 目录 / 文件 | 内容 |
| --- | --- |
| `dscg/` | 防御流水线、模型配置、工具元数据和 token 统计 |
| `experiments/`、`tests/` | 评测、离线 fixture 和回归测试 |
| `config/`、`dashboard/` | 配置模板与 Web 面板 |
| `docs/`、`examples/results/` | 工程说明、图表和可复核的示例结果 |
| `results/`、`archive/` | 被 Git 忽略的运行结果、历史实现 |
| [`AGENTS.md`](./AGENTS.md) | 工程协作规则与当前状态 |

论文问题、文献、创新点与实验协议统一维护在兄弟仓库 [`../research/`](../research/)。工程侧读取[技术路线](../research/technical_route.md)，完成已解锁任务后向[实现状态](../research/paper/implementation_status.md)追加证据；[`system_TODO.md`](./system_TODO.md) 保留工程历史，不能代替当前路线。不要在 DSCG 内复制研究目录或论文计划。

项目介绍：[Word](./docs/DSCG项目介绍.docx) · [可编辑文本](./docs/DSCG项目介绍.md)。
