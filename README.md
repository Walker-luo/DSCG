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

项目使用 Python 3.10、AgentDojo 0.1.35 和 OpenAI-compatible Chat Completions 接口。所有命令应在项目根目录执行。

## 模型配置

模型接入统一由 [`dscg/model_config.py`](./dscg/model_config.py) 管理。Qwen、DeepSeek 等模型都通过 OpenAI-compatible API 调用；每个模型只需要提供模型 ID、API Key 和（必要时）Base URL。API Key 可以通过环境变量、函数参数或本地 `config/models.local.toml` 传入，但不要写入代码或提交到 Git。

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

如果不想每次手动 export，可以复制示例文件并填写本机配置：

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

如果想把配置文件放到其他位置，可以设置：

```bash
export DSCG_MODEL_CONFIG="/absolute/path/to/models.local.toml"
```

DeepSeek 内置配置使用当前 API 文档中的模型 ID `deepseek-flash` 和 `deepseek-v4-pro`，Base URL 为 `https://api.deepseek.com`。模型可用性可能随账号和地区变化；正式实验前请以 DeepSeek 控制台或 `GET /models` 返回为准。

### Python 调用

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

原始基线同样支持这些参数：

```python
from dscg.pipelines.baseline import make_openai_compatible_pipeline

pipeline, tracker = make_openai_compatible_pipeline(
    model_id="deepseek-flash",
    provider="deepseek",
)
```

如果省略 `sec_model_id`，安全审计模型会复用主模型的模型配置；启用安全校验器时仍建议显式指定一个独立的审计模型，便于进行异构模型消融实验。

## 运行评测

运行当前 DSCG 主实验：

```bash
python -m experiments.run_benchmark
```

运行保留的局部任务实验：

```bash
python -m experiments.run_partial_benchmark
```

直接运行原始基线模块：

```bash
python -m dscg.pipelines.baseline
```

评测输出统一写入 `results/`。主入口当前默认运行 Workspace 的 `important_instructions` 攻击；正式实验前应根据 [TODO.md](./TODO.md) 扩展领域、攻击类型和随机种子。

## Web 面板

```bash
python -m dashboard.app
```

默认地址为 `http://127.0.0.1:8888`，可通过 `PORT=5000 python -m dashboard.app` 覆盖端口。面板结果保存到 `results/dashboard/`。

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
