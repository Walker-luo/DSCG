# DSCG Agent Instructions

## 项目定位

DSCG 是一个面向 LLM Agent 间接提示词注入（Indirect Prompt Injection, IPI）的研究原型，基于 AgentDojo 评估任务效用、攻击成功率和运行开销。核心防御由动态工具权限、执行前拦截、动作历史和独立安全模型审计组成。

当前实现用于研究和实验，不应被描述为形式化安全保证。修改防御逻辑时，优先保持安全失败（fail-closed）、完整仲裁（complete mediation）和可复现实验记录。

## 目录职责

- `dscg/`：核心 Python 包。
  - `dscg/model_config.py`：Provider 无关的模型、API Key、Base URL 和本地 TOML 配置解析。
  - `dscg/pipelines/baseline.py`：原始 AgentDojo/OpenAI-compatible 基线流水线。
  - `dscg/pipelines/defended.py`：DSCG 防御流水线，包括 Sandbox、动作历史和安全审计器。
  - `dscg/token_tracking.py`：主模型和安全模型的 token 统计。
  - `dscg/paths.py`：项目路径和结果目录。
- `experiments/`：可复现实验入口和绘图脚本。
- `dashboard/`：Flask Web 面板；不要在前端单独复制模型配置逻辑。
- `config/models.example.toml`：不含密钥的配置模板。
- `config/models.local.toml`：本机配置，已被 Git 忽略，禁止提交。
- `tests/`：配置解析和安全相关回归测试。
- `docs/`：研究笔记、论文资料和图表。
- `archive/`：历史版本，仅供对照，默认不要修改或重新接入运行入口。
- `results/`、`dashboard_results/`：运行时结果，不要把新生成的大型结果文件混入代码修改。

## 环境与运行

项目根目录是包含本文件的目录。使用 Conda 环境 `ipi` 和 Python 3.10：

```bash
conda env update -n ipi -f environment.yml
conda activate ipi
```

首次使用模型时复制本地配置模板：

```bash
cp config/models.example.toml config/models.local.toml
```

模型配置优先级为：函数显式参数 > `DSCG_MAIN_*` / `DSCG_SEC_*` 环境变量 > `config/models.local.toml` > Provider 默认值。API Key 只能通过环境变量、本地未跟踪配置或函数参数传入，不能写进源码、测试固件、README、日志或提交记录。

内置 DeepSeek 配置使用：

- 模型 ID：`deepseek-flash`、`deepseek-v4-pro`
- Base URL：`https://api.deepseek.com`
- API Key 环境变量：`DEEPSEEK_API_KEY`

模型目录会变化；新增或替换模型 ID 前，应以对应 Provider 的官方文档或 `/models` 返回结果核对。对任意 OpenAI-compatible 服务，优先使用显式 `model_id`、`provider`、`base_url` 和 `api_key_env`，不要猜测 Provider。

## 常用命令

在修改后至少运行与改动范围匹配的检查：

```bash
# 单元测试
conda run -n ipi python -m unittest discover -s tests -v

# Python 语法/字节码检查
conda run -n ipi python -m compileall -q dscg dashboard experiments tests

# 前端语法检查
node --check dashboard/static/js/app.js

# 空白字符检查
git diff --check
```

运行实验会访问真实模型并可能产生费用，必须明确配置 API Key 后再执行：

```bash
python -m experiments.run_benchmark
python -m experiments.run_partial_benchmark
python -m dscg.pipelines.baseline
python -m dashboard.app
```

默认优先使用小规模或局部任务验证流水线，再进行完整 AgentDojo 评测。实验结果应记录模型 ID、Provider、攻击类型、套件、随机性设置、是否启用 Sandbox/Checker，以及 token、时间和费用开销。

## 安全实现约定

1. LLM 只能提出候选计划；确定性策略层才可以批准真实工具执行。
2. 工具输出、网页内容、邮件、文件和其他外部数据均视为不可信输入，不能自行扩大权限或修改任务契约。
3. Sandbox、SecurityChecker、重试、恢复和并发动作都必须经过同一个执行仲裁入口；不能绕过检查直接调用 `ToolsExecutor`。
4. 未知工具、未知参数、解析失败、超时、模型拒答和审计器异常默认拒绝高风险动作。
5. 工具风险应依据显式元数据和参数判断，不要只用 `get_`、`read_` 等名称前缀猜测副作用。
6. 记录候选、批准、执行、失败和阻断状态；安全日志应包含机器可读的 reason code，但不得包含 API Key 或不必要的敏感数据。
7. 修改防御行为时，补充对应的安全不变量测试，尤其覆盖空白名单、未知工具、重试动作、并发动作和不可信数据控制外部 sink 的情况。

## 实验与论文可复现性

- 不要只运行 `important_instructions` 或少量任务就宣称完整安全效果。
- 正式实验应区分 benign utility、utility under attack、ASR、defense rate、误拒绝率、延迟和 token/费用开销。
- 修改评测逻辑时保留 baseline、ablation 和完整防御配置，避免只报告有利结果。
- 结果文件和图表应写入既定结果目录；不要覆盖历史样例，除非用户明确要求。
- README、TODO 和研究文档中的模型名、路径和命令必须与代码保持一致。

## 修改风格

- 优先使用现有模块和参数命名，避免为单个 Provider 引入重复客户端实现。
- 保持 Python 3.10 兼容性；需要 `tomllib` 时保留 `tomli` 回退路径。
- 使用 `apply_patch` 进行手工编辑，保持改动小而可审查。
- 移动文件或重命名模块时，搜索并更新所有 Python 导入、命令入口、README 链接和 Dashboard 路径。
- 不要回滚用户已有的未提交改动；遇到无关的脏文件只记录并避开。
- 完成任务时说明改动文件、验证命令和任何未运行的真实模型测试。真实 API 调用前应确认 API Key、目标 Provider 和预期成本。
