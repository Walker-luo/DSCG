# DSCG

DSCG 是一个面向 LLM Agent 间接提示词注入（Indirect Prompt Injection, IPI）的实验性防御框架。当前实现组合了动态工具权限、执行前拦截、动作历史和独立安全模型审计，并基于 AgentDojo 评估任务可用性、攻击成功率与运行开销。

> 当前代码属于研究原型。已知安全边界和后续论文路线见 [TODO.md](./TODO.md)。

## 项目结构

```text
DSCG/
├── dscg/                    # 核心 Python 包
│   ├── pipelines/
│   │   ├── defended.py     # DSCG 防御流水线
│   │   └── baseline.py     # 原始/AgentDojo 基线流水线
│   ├── paths.py            # 与工作目录无关的统一路径
│   └── token_tracking.py   # API token 统计
├── experiments/
│   ├── run_benchmark.py    # 主评测入口
│   ├── run_partial_benchmark.py
│   └── plots/              # 论文与实验绘图脚本
├── dashboard/              # Flask 可视化评测面板
├── docs/
│   ├── research/           # 论文阅读、方案分析与框架设计
│   ├── figures/            # 文档及论文图表
│   └── notes/              # 临时研究笔记
├── examples/results/       # 纳入版本控制的示例实验结果
├── assets/fonts/           # 绘图字体等静态资源
├── archive/                # 旧版框架，仅用于历史对照
├── results/                # 运行时生成，不纳入版本控制
├── environment.yml
└── TODO.md
```

## 环境安装

```bash
conda env create -f environment.yml
conda activate ipi
cp config/models.example.toml config/models.local.toml
```

如果 `ipi` 环境已经存在，请改用 `conda env update -n ipi -f environment.yml`，确保 Python 3.10 和 TOML 解析依赖 `tomli` 已安装。

项目使用 Python 3.10、AgentDojo 0.1.35 和 OpenAI-compatible Chat Completions 接口。所有命令应在项目根目录执行。

## 模型配置

模型接入统一由 [`dscg/model_config.py`](./dscg/model_config.py) 管理。Qwen、DeepSeek 等模型都通过 OpenAI-compatible API 调用；每个模型只需要提供模型 ID、API Key 和（必要时）Base URL。API Key 可以通过环境变量、函数参数或本地 [`config/models.local.toml`](./config/models.local.toml) 传入，但不要写入代码或提交到 Git。

配置相关源码位置：

- 配置解析与 Provider 默认值：[`dscg/model_config.py`](./dscg/model_config.py)
- 不含密钥的配置模板：[`config/models.example.toml`](./config/models.example.toml)
- 本机实际配置：[`config/models.local.toml`](./config/models.local.toml)
- 防御流水线的主模型与安全模型初始化：[`dscg/pipelines/defended.py`](./dscg/pipelines/defended.py)

配置优先级为：函数显式参数 > `DSCG_MAIN_*` / `DSCG_SEC_*` 环境变量 > `config/models.local.toml` > Provider 默认值。

### 内置 Provider

| Provider | 常用模型示例 | API Key 环境变量 | 默认 Base URL |
|---|---|---|---|
| `dashscope` / `qwen` | `qwen3-max`, `qwen-plus` | `DASHSCOPE_API_KEY` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `deepseek` | `deepseek-flash`, `deepseek-v4-pro` | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` |
| `openai` | `gpt-4o`, `gpt-4.1-mini` | `OPENAI_API_KEY` | `https://api.openai.com/v1` |
| `moonshot` / `kimi` | `kimi-k2` | `MOONSHOT_API_KEY` | `https://api.moonshot.cn/v1` |
| `zhipu` / `glm` | `glm-4.5` | `ZHIPUAI_API_KEY` | `https://open.bigmodel.cn/api/paas/v4` |
| `siliconflow` | 由平台提供的模型 ID | `SILICONFLOW_API_KEY` | `https://api.siliconflow.cn/v1` |
| `groq` | 由平台提供的模型 ID | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| `ollama` | 本地模型名称 | 不需要 | `http://localhost:11434/v1` |

### 环境变量配置

主模型使用 `DSCG_MAIN_*` 配置，审计模型使用 `DSCG_SEC_*` 配置。provider 预设会自动选择对应的 Base URL 和 API Key 变量：

```bash
# 主模型：DeepSeek
export DSCG_MAIN_MODEL_ID="deepseek-flash"
export DSCG_MAIN_PROVIDER="deepseek"
export DEEPSEEK_API_KEY="your-deepseek-key"

# 安全审计模型：Qwen
export DSCG_SEC_MODEL_ID="qwen-plus"
export DSCG_SEC_PROVIDER="dashscope"
export DASHSCOPE_API_KEY="your-dashscope-key"
```

如果使用自定义网关或中转服务，直接指定通用变量：

```bash
export DSCG_MAIN_MODEL_ID="your-model-id"
export DSCG_MAIN_API_KEY="your-api-key"
export DSCG_MAIN_BASE_URL="https://your-gateway.example.com/v1"
```

也可以通过 `DSCG_MAIN_API_KEY_ENV` 指定自定义 Key 变量名：

```bash
export DSCG_MAIN_API_KEY_ENV="MY_PROVIDER_API_KEY"
export MY_PROVIDER_API_KEY="your-api-key"
```

### 本地 TOML 配置

如果不想每次手动 export，可以复制 [`config/models.example.toml`](./config/models.example.toml) 为 [`config/models.local.toml`](./config/models.local.toml)，再填写本机配置：

```bash
cp config/models.example.toml config/models.local.toml
```

`config/models.local.toml` 已加入 `.gitignore`，可以保存本机 API Key 或 API Key 环境变量名。推荐在共享机器或服务器上继续使用 `api_key_env`，只在个人本机临时使用 `api_key`：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"

[security]
provider = "dashscope"
model_id = "qwen-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"
```

如果主模型和安全模型都使用 DeepSeek `deepseek-flash`，将 `[security]` 改为：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"

[security]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
```

然后设置一次环境变量：

```bash
export DEEPSEEK_API_KEY="your-deepseek-key"
```

`api_key_env` 只是环境变量名，两个角色可以共用同一个 Key；不要在两个配置段重复保存真实 `api_key`。如果省略整个 `[security]`，安全模型会在运行时复用 `[main]` 的模型配置。

如果想把配置文件放到其他位置，可以设置：

```bash
export DSCG_MODEL_CONFIG="/absolute/path/to/models.local.toml"
```

DeepSeek 内置配置使用当前 API 文档中的模型 ID `deepseek-flash` 和 `deepseek-v4-pro`，Base URL 为 `https://api.deepseek.com`。模型可用性可能随账号和地区变化；正式实验前请以 DeepSeek 控制台或 `GET /models` 返回为准。

### DeepSeek thinking 兼容性

DeepSeek 的 thinking 模式会在助手消息中返回 `reasoning_content`；带工具调用的下一轮请求必须完整回传该字段。当前项目使用 AgentDojo 0.1.35，而其 OpenAI 适配层不会保留这个字段，因此 [`dscg/model_config.py`](./dscg/model_config.py) 会对 DeepSeek 自动设置 `reasoning_effort="none"`，以使用非 thinking 模式完成稳定评测。若要重新开启 thinking，需要先在 AgentDojo 适配层中实现 `reasoning_content` 的完整 round-trip，再移除该兼容设置。

### Python 调用

下面的调用示例对应源码 [`dscg/pipelines/defended.py`](./dscg/pipelines/defended.py) 中的 `make_defended_pipeline`。

主模型和审计模型可以使用同一 Provider：

```python
from dscg.pipelines.defended import make_defended_pipeline

pipeline, main_tracker, sec_tracker = make_defended_pipeline(
    model_id="deepseek-flash",
    sec_model_id="deepseek-flash",
    provider="deepseek",
)
```

也可以分别配置不同 Provider：

```python
from dscg.pipelines.defended import make_defended_pipeline

pipeline, main_tracker, sec_tracker = make_defended_pipeline(
    model_id="deepseek-flash",
    provider="deepseek",
    sec_model_id="qwen-plus",
    sec_provider="dashscope",
)
```

对于任意 OpenAI-compatible 服务：

```python
from dscg.pipelines.defended import make_defended_pipeline

pipeline, main_tracker, sec_tracker = make_defended_pipeline(
    model_id="your-model-id",
    api_key="your-api-key",
    base_url="https://your-provider.example.com/v1",
)
```

原始基线同样支持这些参数，对应源码为 [`dscg/pipelines/baseline.py`](./dscg/pipelines/baseline.py)：

```python
from dscg.pipelines.baseline import make_openai_compatible_pipeline

pipeline, tracker = make_openai_compatible_pipeline(
    model_id="deepseek-flash",
    provider="deepseek",
)
```

如果省略 `sec_model_id`，安全审计模型会复用主模型的模型配置；启用安全校验器时仍建议显式指定一个独立的审计模型，便于进行异构模型消融实验。

## 防御改进记录

每次改进按编号简要记录“改进前 → 改进后”，并说明验证结果与剩余限制。

### P0.1：白名单 fail-closed

| 改进项 | 改进前 | 改进后 |
| --- | --- | --- |
| 空白名单 | `None` 和 `[]` 混用，空列表会跳过权限检查 | 区分未初始化、已初始化为空、有效白名单和错误状态；仅有效白名单可放行 |
| 授权异常 | 解析失败后仍可能保留首轮候选工具权限 | 超时、拒答、非法响应或策略更新失败时撤销权限，默认拒绝 |
| 未知工具 | 沙箱未显式核对工具是否注册 | 即使在白名单中，未注册的工具也被阻断 |
| 阻断后的新动作 | 沙箱内部重试或 Checker 纠错生成的动作可能跳过白名单检查 | 移除沙箱内部重试，Checker 替换动作在执行前再次检查 |

验证：21 项离线测试、Python 编译检查和 `git diff --check` 通过，未运行真实模型评测。混合批次仍采用逐动作裁剪；更保守的阻断可能影响任务效用，需后续评测量化。

当前 `PermissionSandbox`（实现见 [`dscg/pipelines/defended.py`](./dscg/pipelines/defended.py)）采用显式策略状态：

- `uninitialized`（`None`）：尚未完成授权，拒绝所有工具调用；
- `initialized_empty`（`[]`）：授权已完成但没有允许的工具，拒绝所有工具调用；
- `allowlist`：只允许白名单中、且确实注册在当前 `FunctionsRuntime` 的工具；
- `error`：意图解析、策略更新或模型响应异常后的安全失败状态，拒绝所有工具调用。

未知工具、单次请求超时、拒答、非法 JSON、非完整响应和策略更新错误都不会回退到旧权限。一个批次中如果同时出现合法和越权动作，当前实现逐动作裁剪并保留合法动作；如果全部动作被阻断，则停止当前批次，不在沙箱内部自动重试。安全检查器生成的替换动作在真实工具执行前还会再次经过沙箱。SDK 重试导致的总墙钟时间上限尚未统一纳入预算。

这些保证是工具级的研究基线，不是完整安全证明：P0.2–P0.5 的授权与执行改造、P1 的参数级授权和 P2 的 provenance 约束仍待完成，详见 [`TODO.md`](./TODO.md)。离线验证不需要 API Key，可在项目根目录运行：

```bash
conda run -n ipi python -m unittest discover -s tests -v
```

## 运行评测

主评测入口是 [`experiments/run_benchmark.py`](./experiments/run_benchmark.py)。在项目根目录执行 `python -m experiments.run_benchmark` 时，脚本会把 `DSCG_MAIN_MODEL_ID`、`DSCG_SEC_MODEL_ID` 等环境变量传给防御流水线；如果这些变量没有设置，模型 ID 会从 [`config/models.local.toml`](./config/models.local.toml) 的 `[main]` 和 `[security]` 中读取。

例如，使用 DeepSeek `deepseek-flash` 同时作为主模型和安全模型，可以只配置 `config/models.local.toml`：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"

[security]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
```

再设置 Key 并运行：

```bash
export DEEPSEEK_API_KEY="your-deepseek-key"
python -m experiments.run_benchmark
```

也可以不写 `[security]`，此时安全模型会复用 `[main]` 配置。若希望用环境变量覆盖 TOML，则设置 `DSCG_MAIN_MODEL_ID`、`DSCG_MAIN_PROVIDER`、`DSCG_SEC_MODEL_ID` 和 `DSCG_SEC_PROVIDER`；API Key 仍需通过对应的环境变量提供。

运行保留的局部任务实验：

```bash
python -m experiments.run_partial_benchmark
```

### `run_benchmark` 与 `run_partial_benchmark` 的区别

这两个入口都使用 AgentDojo 的 `important_instructions` 注入攻击，也都会输出 Utility、ASR、Defense Rate 和 token 开销；区别在于场景范围、任务取样、默认防御开关和结果目录。当前代码的实际行为如下：

| 入口 | 默认套件与任务取样 | 默认防御配置 | 结果目录 | 适用场景 |
|---|---|---|---|---|
| `python -m experiments.run_benchmark` | `workspace`、`travel`、`banking`、`slack` 四个套件；每个套件使用全部用户任务和全部注入任务 | `use_sandbox=True`、`use_security_checker=True`，运行完整 DSCG 防御 | `results/benchmarks/ablation_study/` | 正式全量评测、跨场景对比和论文主结果 |
| `python -m experiments.run_partial_benchmark` | 同样覆盖四个套件；每个套件只取前 3 个用户任务和前 2 个注入任务 | 使用防御流水线默认配置，即 Sandbox 和 Security Checker 均开启 | `results/partial_benchmark/` | 提交前回归、模型切换和低成本排查 |

因此，`run_partial_benchmark` 是四个场景上的固定小批量回归，而不是完整评测。全量入口的任务组合数等于四个套件中各自的“用户任务数 × 注入任务数”之和，运行时间、Token 消耗和 API 费用会明显高于局部入口。两个脚本当前都设置了 `force_rerun=False`，重复运行时可能复用已有结果；更换模型、Provider、攻击配置或防御开关后，应清理对应结果目录，或在代码中显式改为强制重跑。

运行全量评测：

```bash
python -m experiments.run_benchmark
```

运行小批量回归：

```bash
python -m experiments.run_partial_benchmark
```

如果需要从 Python 中覆盖套件或任务范围，也可以直接调用入口函数。完整防御配置示例：

```python
from experiments.run_benchmark import main

main(
    model_id="deepseek-flash",
    sec_model_id="deepseek-flash",
    suites=["workspace"],
    run_attack=True,
    use_sandbox=True,
    use_security_checker=True,
)
```

正式论文实验应固定套件、用户任务、注入任务、随机种子和防御开关，并记录实际任务数量；不要直接把上述两个入口的默认子集结果称为完整 AgentDojo 基准结果。

直接运行原始基线模块：

```bash
python -m dscg.pipelines.baseline
```

评测输出统一写入 `results/`。主入口默认运行四个 AgentDojo 套件的 `important_instructions` 攻击；正式论文实验前仍应固定模型、Provider、攻击类型、任务列表、随机种子和防御开关，并保留每个套件的独立报告。

## Web 面板

```bash
python -m dashboard.app
```

默认地址为 `http://127.0.0.1:8888`，可通过 `PORT=5000 python -m dashboard.app` 覆盖端口。面板结果保存到 `results/dashboard/`。

面板左侧的“自定义 API 连接”是本次运行级别的临时配置。可以直接填写主模型的 API Key 和 Base URL；安全审计模型可以单独填写覆盖值，留空时在同一 Provider 或未指定独立安全模型的情况下复用主连接。留空则继续使用环境变量或 `config/models.local.toml`。API Key 仅传给当前后台运行线程，不写入日志、运行结果或报告；在非本机部署时请使用 HTTPS，并避免通过不受信任的公网面板提交密钥。

## 生成图表

```bash
python -m experiments.plots.draw_comparison
python -m experiments.plots.draw_combined
python -m experiments.plots.draw_cost
python -m experiments.plots.draw_ablation
```

图表统一输出到 `docs/figures/benchmarks/`。

## 当前实验结果

Workspace 消融实验的历史记录：

| 配置 | Utility | ASR | Defense Rate |
|---|---:|---:|---:|
| DSCG Full | 67.14% | 0.00% | 100.00% |
| No Sandbox | 68.10% | 0.48% | 99.52% |
| No Security Checker | 67.14% | 5.24% | 94.76% |

这些结果来自有限任务子集和单一攻击模板，不能解释为对未知攻击的安全保证。可复现的小规模 Dashboard 样例位于 `examples/results/dashboard/`。

![Qwen Flash result](./docs/figures/qwen_flash_result_1.png)

## AgentDojo 兼容性说明

当前实验环境曾对 AgentDojo 的 OpenAI LLM 适配层做过本地调整，以处理部分模型将 `system` message 转换为 `developer` message 的行为。重新创建环境时，应检查当前 AgentDojo 版本的消息角色兼容性，不要依赖旧机器上的绝对环境路径。

## 研究资料

- 框架设计草稿：[docs/research/ours.md](./docs/research/ours.md)
- IPIGuard 分析：[docs/research/IPIGuard_分析.md](./docs/research/IPIGuard_分析.md)
- IntentGuard 分析：[docs/research/IntentGuard_分析.md](./docs/research/IntentGuard_分析.md)
- ACE 分析：[docs/research/ACE_分析.md](./docs/research/ACE_分析.md)
- 论文清单：[docs/research/papers.md](./docs/research/papers.md)
