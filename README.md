# BaseIntent

BaseIntent 是工具使用型 LLM Agent 的间接提示词注入防御研究原型。它把可信任务拆成意图，冻结全局工具权限，再结合真实执行事件与有限语义判断推进；L3 审计具体动作，Monitor 约束实际执行。

当前默认 `prompt_profile=legacy`，框架标识为 `BaseIntent`。运行名称只命名实验，不选择策略。Python 包为 `baseintent`；旧结果保留原身份，兼容范围见[迁移说明](docs/migration.md)。

## 开始使用

从项目根目录执行；已有环境和本地配置可直接使用，无需覆盖：

```bash
# 首次安装时按需创建其中一个环境
conda env create -f environment.yml
# AgentDyn 使用 environment-agentdyn.yml
conda activate ipi
# 或 conda activate ipi-agentdyn
python -m baseintent.benchmark_catalog
```

最后一条命令只核对安装元数据并列出任务目录，不调用模型。配置参考 [config/models.example.toml](config/models.example.toml)，本地凭证放在忽略的 `config/models.local.toml` 或环境变量中。详见[模型与工具配置](docs/model_tool_configuration.md)。

| 环境 | 实际后端 / 场景 | Full clean 计划 | Partial clean / typical 计划 |
| --- | --- | ---: | ---: |
| `ipi` | AgentDojo：workspace、travel、banking、slack | 97 | 12 / 108 |
| `ipi-agentdyn` | AgentDyn：shopping、github、dailylife | 60 | 9 / 81 |

后端以实际导入路径、安装来源、版本及 revision 识别；环境名仅供操作。计划数不是有效评分分母，AgentDyn 部分 `tool_knowledge` 目标不支持。

下列命令会调用真实模型；新实验使用新名称和独立输出目录：

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --model-config config/models.local.toml --name baseintent_partial_01 \
  --results-dir artifacts/20261027_example/partial --progress

python -m dashboard.app
```

Dashboard 默认地址为 [http://127.0.0.1:8888/](http://127.0.0.1:8888/)。完整任务、baseline、clean、冻结 cohort 和续跑命令见[评测指南](docs/benchmark.md)。全量评测应由用户明确启动。

## 当前框架

- **L1** 从原始历史重建来源隔离视图；明确的银行月支出任务可使用有界六字段投影。原始返回保留用于审计和原生轨迹，无额外模型调用。
- **L2** 两次主模型调用依次生成目标类型与意图、选择全局工具及固定 ID 键的进度关联。宿主先无损归并连续准备前缀，再分配 ID。工具关联用于进度，不是每意图权限。
- **进度** 宿主记录真实成功执行和最终回答；准备读取可本地观察，复杂目标保留语义判断。自动完成仅覆盖严格有界的单次直接邀请模式。
- **L3 / Monitor** 用有限四字段判决检查当前意图与完整用户约束，再通过整批回执和一次性票据执行。注册、已授权、schema 有效的 public/internal 读取在所有路由模式固定免审；这不按 sink、URL 或对象隐私筛选。

CLI 路由默认 `shadow`，API/factory 默认 `off`；`off` 仍保留 L3，阈值不能调节固定读取免审范围。对象、参数、数据权限及最终文本独立动作审计尚未实现。机制、公式与例子见[框架说明](docs/framework.md)。

最近固定键 12 例观察：TSR **8/12 → 7/12**，原生 ASR **0/8 → 0/8**，progress 调用 **61 → 43**，计分 Token **551,741 → 470,265（−14.8%）**。这是有限范围的历史观察，效用验收仍为 partial，不能宣称一般防御有效或整体安全通过。项目整理本身不产生新的效用结论。

## 文档与代码

[文档索引](docs/README.md) · [框架](docs/framework.md) · [配置](docs/model_tool_configuration.md) · [测试](docs/evaluation.md) · [结果](docs/result_files.md) · [Dashboard](docs/dashboard.md) · [迁移](docs/migration.md)

核心入口：`baseintent/pipelines/defended.py`（共享执行）、`baseintent/intent_flow.py`（授权与进度）、`baseintent/input_isolation.py`（L1）、`baseintent/decision_schema.py`（L3 契约）。实验入口见 [experiments/README.md](experiments/README.md)。新检查和临时运行产物放在 `artifacts/<日期>_<任务>/`，保留现有用户结果与历史证据。
