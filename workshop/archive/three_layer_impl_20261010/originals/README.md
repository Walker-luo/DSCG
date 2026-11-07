# DSCG

DSCG 是工具使用型 LLM Agent 的间接提示词注入（IPI）防御研究原型，基于 AgentDojo 比较任务成功率（TSR）、攻击成功率（ASR）和模型开销。

## 当前框架与创新定位

当前保留 **V2 两层防御**；Reference Monitor 和一次性执行票据提供执行基础设施。

```text
可信用户请求 → 工具授权 → 主模型提出动作 → 当前动作审计
                                      → Monitor 仲裁 → 消费票据 → 工具执行
```

| 部分 | 当前实现 |
| --- | --- |
| 第一层：工具授权 | 只依据可信用户请求，使用排序工具目录和 temperature=0；编译错误、未初始化或空策略均拒绝执行。工具反馈不能授予权限。 |
| 第二层：动作审计 | 审查候选调用，区分必要前置读取与后续写入；使用宿主工具描述（最多 512 字符）及最近 4 条不可信工具返回（每条最多 2,048 字符）。 |
| 执行基础设施 | Monitor 统一仲裁；真实工具执行必须消费绑定调用指纹的一次性 ticket；阻断、重试和新候选均经过同一入口。 |

工程特点是把可信任务授权、语义审计和实际执行分开，并用离线状态转移测试检查错误反馈与恢复路径。**这些特点尚不是已证明的论文创新**；能力图、审计日志或票据本身不作为新算法贡献。

当前约束仍是工具级：对象、目的地、参数和数据权限尚未强制约束。I3 压力测试为 `partial`，24 条有效样例中有 8 条范围缺口；真实 E0 harness 验收和重复对照仍待完成。默认 `audit_retries=0`、`completion_prompt=false`，三层方案尚未实现。

实现见 [defended.py](./dscg/pipelines/defended.py)；当前优化与候选见 [workshop 索引](./workshop/README.md)，能力边界见 [I3 报告](./docs/i3_p0_stress_report.md)。论文贡献与路线由兄弟仓库 [research](../research/technical_route.md) 维护。

Dashboard 的“防御架构”按当前 V2 stage1 展示两层及已生效修改，Monitor／票据单列为执行基础设施，详见 [页面说明](./docs/dashboard.md)。

新的[两层重构候选](./workshop/original_framework_direction_20261008.md)研究授权对照校准：检验审计器对可信许可/禁止变化的响应；尚未实现，也未通过新颖性验收。

## 安装与配置

在 `DSCG/` 执行：

```bash
conda env create -f environment.yml
conda activate ipi
cp config/models.example.toml config/models.local.toml
```

在本地 TOML 中配置 `[main]`、`[security]` 的 provider、model_id 和 api_key_env，再设置对应 Key 环境变量；省略 `[security]` 会复用主模型。不要提交本地配置或凭证。项目使用 Python 3.10、AgentDojo 0.1.35；详细配置见[模板](./config/models.example.toml)与[评测指南](./docs/evaluation.md)。

## 对比测试

以下命令默认 `ipi` 已激活，无需额外任务清单。使用新运行名称保存每次对照：

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline_compare_01
python -m experiments.run_partial_benchmark --force-rerun --name workshop_compare_01
```

baseline 使用原生 AgentDojo 工具循环，不启用 DSCG 或安全模型；两组使用相同主模型配置及 v1.2 任务子集：workspace、travel、banking、slack 各取注册顺序前 3 个用户任务和前 3 个注入任务。默认 `typical` 共计划 144 条攻击评测，另有攻击能力预检；实际分母与任务 ID 以 `summary.json` 为准。

| 默认 `--attack typical` 的攻击 | 简要说明 | 来源 |
| --- | --- | --- |
| `ignore_previous` | 要求忽略原任务，改做攻击任务 | [AgentDojo 论文 §4.2][agentdojo-paper]及[AgentDojo 官方实现][agentdojo-baseline] |
| `injecagent` | 用强调标记和忽略指令模板提出攻击目标 | [InjecAgent 论文][injecagent-paper]、[AgentDojo 官方适配][agentdojo-baseline] |
| `important_instructions` | 冒充用户，要求先完成攻击目标 | [AgentDojo 论文 §4.1–4.2][agentdojo-paper]及[AgentDojo 官方实现][agentdojo-baseline] |
| `tool_knowledge` | 补充攻击所需工具顺序和参数提示 | [AgentDojo 官方实现][agentdojo-baseline] |

典型集用于控制测试规模，不表示已验证攻击强度。可用 `--attack NAME [NAME ...]` 指定攻击，或 `--attack all` 显式运行全部自动攻击；`manual` 不可选。完整攻击表、消融和指标口径见[评测指南](./docs/evaluation.md)。

默认 `summary` 足够用于对比。`--trace-level full` 保存详细诊断及压缩侧车，增加序列化和写入开销；按需排错时使用。正式对照还需匹配任务 ID、攻击、模型配置及预检口径，历史结果仅作参照。

用户运行的结果保存到：

```text
results/partial_benchmark/<model_id>_<name>/<attack>/<suite>/
```

每次 partial 运行还会在 `<model_id>_<name>/` 下生成 `summary.md`（attack × 场景指标、分母、Token 和失败案例位置）与 `failure_cases.jsonl`（逐例的失败标签、原始路径与有界片段）。TSR=false 和 ASR=true 分别记录；指标缺失/运行错误单列。详见[结果文件说明](./docs/evaluation.md#结果文件)。

## Dashboard

```bash
python -m dashboard.app
```

打开 [实验配置](http://127.0.0.1:8888/)或[历史分析](http://127.0.0.1:8888/history)。历史页按结果目录、模型/运行名称（多选）、攻击筛选；勾选 baseline 和优化版本后可比较 TSR、ASR、总 Token，并下载分析数据。使用说明见 [dashboard 指南](./docs/dashboard.md)。

## 离线检查

无需模型 Key。示例使用新的输出文件，已有文件应保留：

```bash
python -m unittest discover -s tests -v
python -m experiments.i3_p0_stress \
  --output workshop/artifacts/20261008_offline_check/i3.json
python -m experiments.harness_audit \
  --fixture tests/fixtures/harness_audit_cases.json \
  --output workshop/artifacts/20261008_offline_check/e0.json
```

当前 I3 预期退出码为 `1`（范围缺口）；`0` 才表示全部约束通过并按路线记录 `no_go`，`2` 表示样本错误。E0 合成自检不等于真实 harness 过闸。文档归档可用 `python workshop/verify_migration.py` 只读检查。

## 目录约定

| 路径 | 职责 |
| --- | --- |
| `dscg/`、`config/` | 防御实现、模型配置与内置工具元数据 |
| `experiments/`、`tests/` | 评测入口、fixture 定义与测试源码 |
| `dashboard/` | 实验配置与历史分析界面 |
| [docs/](./docs/README.md) | 当前使用指南及 I3 状态报告 |
| [workshop/](./workshop/README.md) | 顶层仅保留待优化方案与相关来源 |
| [workshop/completed/](./workshop/completed/README.md) | 已完成阶段的方案、报告与撤回记录 |
| `workshop/artifacts/<YYYYMMDD>_<task>/` | **新 agent 测试产物的固定位置**，包括日志、fixture 输出、探针、临时模型评测和图表 |
| `results/`、`download/` | 用户正式实验原始结果与历史分析导出 |
| `examples/`、`workshop/results/`、`archive/` | 保留的历史证据、示例与旧实现 |
| [AGENTS.md](./AGENTS.md) | 持久协作规则与工程状态 |

Agent 运行 partial 时必须用 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`；不得把测试产物写入根 `result/` 或 `results/`。详细规则见 AGENTS。

正式论文计划留在 `../research/`。工程侧读取[技术路线](../research/technical_route.md)，完成后向[实现状态](../research/paper/implementation_status.md)追加证据。

[agentdojo-paper]: https://arxiv.org/html/2406.13352v2
[injecagent-paper]: https://aclanthology.org/2024.findings-acl.624/
[agentdojo-baseline]: https://agentdojo.spylab.ai/api/attacks/baseline_attacks/
