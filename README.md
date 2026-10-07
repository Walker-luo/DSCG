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

## 防御改进

| 改进 | 当前实现 |
| --- | --- |
| P0.1：默认拒绝 | 区分未初始化、空白名单、有效白名单和错误状态；授权异常撤销旧权限，未知工具被阻断 |
| P0.2：授权先于候选 | 仅根据当前可信用户请求、固定策略和工具目录编译不可变契约；同一可信回合复用契约 |
| P0.3：统一执行入口 | 每个动作经过 Monitor 和一次性票据校验，账本记录提出、批准、执行、失败或阻断 |
| P0.4：结构化审计 | 严格校验审计输出，限制不可信参数与历史输入；审计缺失或异常时默认阻断需审计的动作 |
| P0.5：工具风险元数据 | 显式描述 effect、source、sink、sensitivity 等；缺失或非法分类按 critical 处理，公共读取可走低成本路径 |
| Workshop：harness 可靠性 | 缺失安全结果单列基础设施错误；小批量任务按固定 seed 排序；保留 payload 投递、宿主 predicate 与有效分母 |
| Workshop：记录精简 | summary/standard 去除重复输入、目录和参数哈希；保留运行时校验与 full 压缩侧车；每次运行一个 manifest hash、每样本一个 payload hash |
| I3：恢复压力测试 | 补齐真实错误反馈与恢复回路；修复并发重复票据误改首个动作状态的问题，重复提交独立记为 blocked |

截至 **2026-10-06** 的验证状态：

- 仓库离线测试 **102/102 通过**，其中 I3 测试 18 项。
- I3 fixture 有效样本 **24/24**，无运行错误或跳过；仍有 **8 个范围断言失败**，涉及全新调用扩大对象、目的地、数据选择或重做已完成义务，回报 **`partial`**。
- E0 合成自检共 6 样本：valid 1、tool_error 1、infrastructure_error 4。自检包含预设错误样本，不代表真实 harness 已通过研究闸门；I2 fixture/pilot 仍锁定。

这些是离线工程证据。现有模型 benchmark 与历史消融结果仍属有限子集的 smoke 记录，不能据此推出一般防御率、完整 AgentDojo 结果或论文新颖性。

详细证据见 [I3 报告](./docs/i3_p0_stress_report.md)、[Workshop 历史报告](./docs/workshop_optimization_report.md) 和 [I3 原始结果](./examples/results/i3_p0_stress/20261006_01a10fca/)。后续机制只按研究侧解锁的任务实现。

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

离线测试和 fixture 无需 API Key：

```bash
conda run -n ipi python -m unittest discover -s tests -v
conda run -n ipi python -m experiments.i3_p0_stress --output /tmp/dscg-i3-check.json
conda run -n ipi python -m experiments.harness_audit \
  --fixture tests/fixtures/harness_audit_cases.json --output /tmp/dscg-e0-check.json
```

I3 退出码：`0` 表示所有有效样本约束通过，按路线记 `no_go`；`1` 表示发现约束缺口；`2` 表示样本运行错误。当前预期为 `1`，回归测试通过不表示范围断言已成立。运行时使用新的输出路径，保留已有结果。

模型评测需先配置连接与 Key：

```bash
python -m experiments.run_partial_benchmark --name partial-check
python -m experiments.run_benchmark --name full-check
```

两个入口默认均启用完整 DSCG，覆盖 workspace、travel、banking、slack，使用 `important_instructions` 攻击。partial 是固定 seed 的小批量回归，full 使用全部任务；结果分别保存到 `results/partial_benchmark/` 和 `results/benchmarks/` 的 `<model_id>_<name>/` 目录。正式实验需另行固定 manifest、模型、攻击、seed 和防御开关。

重新运行与 partial 相同任务的**无防御 baseline**：

```bash
conda run -n ipi python -m experiments.run_partial_benchmark \
  --baseline --force-rerun --name baseline-20261006
```

该模式使用原生 AgentDojo 工具循环和当前主模型配置，不启用 DSCG、安全模型或 AgentDojo 防御。保留 `important_instructions` 注入攻击；与防御版共用 v1.2 套件和 seed `20260927`，每场景选 2 个用户任务 × 2 个注入任务，四场景共计划 16 个组合。各场景 `summary.json` 的 `task_selection` 保存 seed 和具体任务 ID，`defense: null` 表示无防御。比较时保持主模型配置一致，使用不同运行名称保留两组结果；旧版本若采用不同任务选择规则，需核对原始任务 ID。

常用选项：

| 选项 | 用途 |
| --- | --- |
| `--name NAME` | 区分运行版本，避免复用其他实验的结果 |
| `--baseline` | partial 入口使用无防御基线，任务子集和攻击保持一致 |
| `--force-rerun` | partial 入口重新执行已有任务，不复用缓存 |
| `--trace-level summary/standard/full` | 默认摘要、裁剪后的逐条记录、完整记录与 `.dscg_trace.jsonl.gz` 侧车 |
| `--include-extra-info` | 等价于 `--trace-level full` |
| `--tool-metadata PATH` | 指定工具风险元数据 TOML；也可设置 `DSCG_TOOL_METADATA` |
| `--model-config PATH`、`--results-dir DIR` | partial 入口支持的配置与结果路径覆盖 |

工具目录可用 `python -m experiments.generate_tool_metadata` 生成，默认不覆盖已有本地文件；分类规则见 [`dscg/tool_metadata.py`](./dscg/tool_metadata.py)。评测默认可能复用缓存；partial 可用 `--force-rerun` 或 `DSCG_FORCE_RERUN=1` 强制重跑。调整实验配置时使用新的运行名称并保留原始结果。

启动 Web 面板：

```bash
python -m dashboard.app
```

默认地址为 [http://127.0.0.1:8888](http://127.0.0.1:8888)，可用 `PORT` 覆盖；结果保存到 `results/dashboard/`。面板支持实验配置、历史分析和图表。绘图脚本位于 [`experiments/plots/`](./experiments/plots/)，输出到 `docs/figures/benchmarks/`。

“历史分析”的指标支持多选，默认选择 TSR 与 ASR，每个指标各自成图，桌面端并排、窄屏纵向展示。同一实验的颜色与点形在各图、图例和实验列表中一致，取消部分实验或切换指标时保留颜色对应。Token 图使用自身的千单位纵轴；百分比图继续保留 −5%～105% 的范围，雷达图外圈为 110%。雷达图仅适用于全部场景的百分比指标，散点图与任务热图使用固定指标。验收证据见[历史分析分图与颜色报告](./docs/history_separate_report.md)。

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

<!-- framework-optimization-20261007 -->
## 本轮框架优化

| 阶段 | 工程状态 |
|---|---|
| P0-A 任务隔离 | 顶层调用新建 context，清除旧授权缓存和历史、撤销票据；任务内循环沿用。 |
| P0-B 成本与诊断 | 记录主模型/授权/审计 API、Token、耗时；历史分析显示两模型合计。官方攻击分数保留，E0 独立送达/环境复核仍待完成。 |
| P0-C 外部请求 | 网页请求按外部接收方路由至现有审计；离线成对样例覆盖合法访问和注入网址。未实现 URL 对象约束。 |
| P1-A 有界重审 | 可选一次语义 abstain 重审；保留当前任务历史，parser/超时不重试，持续不确定阻断。 |
| P1-B 任务完成提示 | 可选通用提示继续已授权任务并覆盖用户要求字段；每次工具动作仍受现有 monitor/ticket 检查。 |

离线验证与限制见 [优化实施报告](docs/framework_optimization_report.md)。上述工程测试不证明 benchmark 防御收益；I3 仍为 partial，参数、对象和数据约束及 I2 保持锁定。
