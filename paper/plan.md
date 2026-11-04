# AIMLL Workshop 后续计划（2026-11-04，DashScope 版）

> **2026-11-04 稿件更新：**`main.tex` 已纳入工作区中新出现的 Qwen3.5-Flash v3.7 完整结果和 clean 对照，当前包含三个模型配置；图 1 更新了模块图标，图 2 更新为三模型配对结果。Qwen3.5 的有效配对任务成功为 1,805→1,175/2,139，clean 为 90→53/97。历史结果仍保留 v3.6.3 身份。下文原计划和“两模型”状态保留供参考；尚未完成的测试仍是计划，不代表授权或已运行。

> 现状：`paper/main.tex` + `paper/main.pdf` 为 4 页草稿（上限 6 页），Table 1 + Fig. 1 + Fig. 2 已落地，数字由 `paper/fig/paper_numbers.json` 统一生成。
> 模型策略：**只用 DashScope 第一方 Qwen**；先测 baseline ASR，再按观测到的易感性选模型，不按“强/弱”预设。
> 截稿：2027-01-15；当前约 10 周。

## 1. 当前已完成

| 项 | 状态 |
| --- | --- |
| 论文 | `paper/main.tex` 初稿；`paper/main.pdf` 5 页；0 overfull，无未定义引用 |
| 数据 | Qwen3.5 使用 v3.7 + baseline；Qwen3.7 和 DeepSeek 使用 v3.6.3 + baseline；不重标历史版本 |
| 主表 | 4 suite、三个模型配置、配对键；Qwen3.5 2,139 / Qwen3.7 1,943 / DeepSeek 1,836 |
| 图 1 | `paper/fig/system-architecture.png`，4325×2356，600 dpi；PDF 183×99.5 mm |
| 图 2 | `paper/fig/results-tradeoff.pdf/png`；ASR 配对点 + TSR delta；QA 全 PASS |
| 数字源 | `paper/fig/extract_paper_numbers.py` → `paper_numbers.json` / `results-tradeoff.csv` |

下表保留原两模型计划基线；三模型最新数字见 `paper/fig/paper_numbers.json` 和论文 Table 1：

| | Qwen3.7-Flash | DeepSeek-Flash |
|---|---:|---:|
| baseline ASR | 22.5%（438/1,943） | 2.1%（38/1,836） |
| DSCG ASR | 0（上界 0.2%） | 0.27%（5/1,836） |
| TSR | 73.3% → 79.3%（p<0.001） | 83.6% → 82.4%（p=0.08） |
| clean TSR | 85.6%（仅 DSCG） | 90.7% → 86.6% |

## 2. 观点评估：基线易感性 ≠ 模型强度

**数据支持**：Qwen baseline ASR 22.5%，DeepSeek 只有 2.1%；模型选择会显著改变防御看起来有没有用。

**不能直接推出**“强模型自带强 IPI 防御”：
1. “强”没有独立度量，只有 TSR/ASR 两个行为指标。
2. 两模型筛选集不同（Qwen 保留 27/35 个 GOAL，DeepSeek 24/35），ASR 不是同一把尺子。
3. 审计器 = 主模型；DeepSeek 的低 ASR 可能来自主模型不易被带偏，也可能来自审计器更保守。
4. 单次运行、静态攻击；2.1% 不是“强模型普遍安全”。

**只测弱模型的问题**：等于在“有提升空间”的样本上选模型，会高估 DSCG 收益，并丢掉“低 headroom 时防御成本占主导”的边界；审稿人会读成 cherry-picking。

**采用的说法**：把“强模型”改成“**低基线易感性模型**”；把“只测弱模型”改成“**以弱模型为主、保留低 ASR 边界**”。先测 baseline ASR，再定组合。

## 3. DashScope 模型调研（2026-11-02 官方页）

来源：[文本生成与视觉理解](https://help.aliyun.com/zh/model-studio/text-generation-model)、[模型调用价格](https://www.alibabacloud.com/help/zh/model-studio/model-pricing)、[深度思考](https://help.aliyun.com/zh/model-studio/deep-thinking)。价格为北京地域、人民币/百万 Token，有限时折扣，跑前以控制台为准。

### 3.1 候选

| 模型 ID | 价格（输入/输出） | 上下文 | 思考默认 | Function Calling / JSON | 角色 |
| --- | --- | ---: | --- | --- | --- |
| `qwen3.7-flash` | 0.2/0.8（≤32K）；0.6/2.4（32K–256K） | 1M | 支持；当前记录 `reasoning_effort=none` | 支持 / 支持 | 高易感 anchor（22.5%），最便宜 |
| `qwen3.8-flash` | 0.8/2.7 | 1M | 默认开 | 支持 / 支持 | 新一代小模型；候选高/中易感 |
| `qwen3.7-plus` | 2/8（≤256K）；6/24（256K–1M） | 1M | 默认开 | 支持 / 支持 | 中间档；候选低/中易感 |
| `qwen3.8-max` | 12/36 | 1M | 默认开 | 支持 / 支持 | 当前旗舰；候选低易感边界 |
| `qwen3.5-flash` | 0.2/2（≤128K） | 1M | 支持 | 支持 / 支持 | 旧一代小模型；高易感 fallback |
| `qwen3.7-max` | 12/36 | 1M | 默认开 | 支持 / 支持 | 旧旗舰；除非 3.8-max 不可用，否则不选 |

不选 `qwen3-max` / `qwen-plus` / `qwen-flash` / `qwen-turbo`：属于更旧代际，和 3.8/3.7 系列混在一起只会增加“代际”混杂，不如用 3.5-flash 作为唯一旧代际对照。

> DeepSeek-Flash 是已有低 ASR anchor，**不在 DashScope**；新增模型全部用 DashScope 第一方 Qwen。如果你要求所有模型同平台，可把 anchor 换成 DashScope 托管的 `deepseek-v4.1-flash`，但现有 1,836 键结果作废，不推荐。


### 3.2 选型逻辑（先筛后选）

不建议直接按“qwen3.8-max 一定最强/最稳”拍板；先用 **baseline-only 筛选** 测易感性：

- 每个候选跑 4 suite × 3 用户 × 3 目标 × `important_instructions` = **36 键**，只跑 baseline，不跑 DSCG。
- 记录 baseline ASR、TSR、工具调用失败、协议失败。
- 选 4 个模型：Qwen3.7-Flash（高 anchor）+ DeepSeek-Flash（低 anchor）+ **2 个新模型**，其中一个观测 ASR 高、一个观测 ASR 低。
- 高易感优先从 `qwen3.8-flash` / `qwen3.5-flash` 中选；低易感优先 `qwen3.8-max`，其次 `qwen3.7-plus`。
- 如果 `qwen3.8-flash` 的 baseline ASR 已经很低，就补 `qwen3.5-flash` 作为第二个高易感点，而不是硬说“新一代小模型也弱”。

筛选是用 baseline 结果选模型，不是用 DSCG 结果选模型；这个选择规则要写进论文，避免“按结果挑模型”的质疑。

### 3.3 非思考模式是前置条件

官方文档明确：`qwen3.8-max`、`qwen3.8-flash`、`qwen3.7-plus` **默认开启思考**，且 `enable_thinking` 是非标准参数，必须通过 `extra_body` 传；`qwen3.7-plus` 的思考 token 可占输出 60% 以上。当前 `dscg/model_config.py::reasoning_effort_for_config` 只对 `qwen3.7-flash` 返回 `none`，对 3.8/3.7-plus 返回 `None`，直接跑会变成 thinking 模式，和现有结果不可比。

需要的最小代码改动：

1. 在 `dscg/model_config.py` 增加一个 DashScope 非思考模型集合/判断（`qwen3.8-*`、`qwen3.7-plus` 等）。
2. 在 `dscg/pipelines/baseline.py`、`dscg/pipelines/defended.py` 的请求构造处，对集合内模型传 `extra_body={'enable_thinking': False}`，不再依赖 `reasoning_effort`；保留 `qwen3.7-flash` 现有行为，避免旧结果不可比。
3. `run_manifest.json` / 诊断记录实际 `enable_thinking`；现在 `task_diagnostics.py` 已能记录 `extra_body.enable_thinking`，复用即可。
4. 测试：mock client 捕获请求 kwargs，断言新模型有 `extra_body.enable_thinking=False`、没有 `reasoning_effort`；旧 Qwen3.7-Flash 路径不变。离线两环境跑 targeted tests；在线用 qwen3.7-flash 跑 ≥9 个计分案例确认无回归，再各模型 1 个 smoke。

如果 smoke 发现 `enable_thinking` 被忽略或返回 `reasoning_content`，停止该模型，不把 thinking 结果混进主表。

## 4. 后续测试

### P0：不做会留下明显缺口

common grid 用 `--write-task-manifest` 先导出 partial 清单，再取所有入选模型共同支持的 task/attack 键，写入同一份 `--task-manifest`；不要直接用各模型的 `--fliter` 做跨模型比较。


| # | 测试 | 规模 | 目的 |
| --- | --- | --- | --- |
| 1 | **Qwen baseline clean** | 97 个用户任务（4 suite） | 补当前唯一缺失的 clean 对照；和 DeepSeek 的 88/97 对齐 |
| 2 | **模型筛选** | 5 个候选 × 36 键 baseline-only | 按观测 baseline ASR 选 2 个新模型，不按“强弱”预设 |
| 3 | **冻结 common grid** | partial 4 suite × 3 用户 × 3 目标 × 3 攻击 = 108 键/模型臂 | 新模型与 Qwen/DeepSeek 用同一批键；已有全量结果切同一批键，不重跑 |
| 4 | **新模型 A（高易感）** | baseline + DSCG，108×2 | 验证弱模型收益可复现 |
| 5 | **新模型 B（低易感）** | baseline + DSCG，108×2 | 验证低 headroom 边界 |
| 6 | **固定审计器对照** | DeepSeek 主 + Qwen 审计，108 键 | 分离“主模型易感性”与“审计器行为” |

### P1：增强说服力，但不阻塞投稿

| # | 测试 | 规模 | 目的 |
| --- | --- | --- | --- |
| 7 | 新模型 clean | 97 任务/模型 | 算净误拒 |
| 8 | 最小消融 | 一个模型 full vs `--no-checker`，108×2 | 回答 L3 的贡献 |
| 9 | 外部基线 | spotlighting / repeat_user_prompt，108 键 | 与已有防御对比；需补 `--agentdojo-defense` 开关 |
| 10 | 成本/延迟 | 新 run 的 usage | 每模型 token/例、审计占比、人民币成本 |

### P2：有余力再做

| # | 测试 | 说明 |
| --- | --- | --- |
| 11 | 自适应攻击探针 | 10 条针对 L2/L3 的手工注入；定性，不称 benchmark |
| 12 | AgentDyn 1 suite | shopping 或 dailylife，partial 81/72 键 × 2 臂 |
| 13 | 语义 ASR 复核 | 抽 40 条攻击案例人工判读；新模型各抽 10 条 |
| 14 | 复现包 | 代码快照、config、prompt 哈希、任务清单、CSV、README |

### Commands（工作站 `ipi`；服务器改用 `~/miniconda3/bin/conda run -n DSCG`）

```bash
# 1) Qwen baseline clean
conda run -n ipi python -B -m experiments.run_benchmark \
  --suites workspace banking slack travel --baseline --clean \
  --name qwen_baseline_clean --results-dir workshop/artifacts/20261104_aimll_followup

# 2) 模型筛选：只跑 baseline，36 键
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites workspace banking slack travel --attack important_instructions --baseline \
  --model-config config/models.aimll_qwen38_flash.toml \
  --name screen_qwen38_flash --results-dir workshop/artifacts/20261104_aimll_screen

# 3) 选中模型后，baseline / DSCG 各一次，108 键
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites workspace banking slack travel --attack typical \
  --model-config config/models.aimll_qwen38_max.toml \
  --name aimll_qwen38_max_dscg --results-dir workshop/artifacts/20261104_aimll_followup
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites workspace banking slack travel --attack typical --baseline \
  --model-config config/models.aimll_qwen38_max.toml \
  --name aimll_qwen38_max_baseline --results-dir workshop/artifacts/20261104_aimll_followup
```


新模型配置示例（只改 `[main]`，`[security]` 固定 Qwen；provider 地址沿用现有 `config/models.local.toml`）：

```toml
[main]
provider = "dashscope"
model_id = "qwen3.8-max"

[security]
provider = "dashscope"
model_id = "qwen3.7-flash"

[providers.dashscope]
base_url = "<沿用现有地址>"
api_key_env = "DASHSCOPE_API_KEY"
```

固定审计器只改 `[security]`，主模型沿用现有 DeepSeek 配置：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
[security]
provider = "dashscope"
model_id = "qwen3.7-flash"
```

> 现有 DeepSeek 配置在 `config/models.local.toml` 的 deepseek provider；主模型 ID 以实际配置为准，不要照抄示例。

### 规模与预算（4 模型版）

| 项目 | 计分运行 | 估算 token |
| --- | ---: | ---: |
| Qwen baseline clean | 97 | ~0.8M |
| 模型筛选（5 候选 × 36） | 180 | ~2.5M |
| 新高易感模型（两臂） | 216 | ~5M |
| 新低易感模型（两臂，qwen3.8-max） | 216 | ~5M |
| 固定审计器（DeepSeek + Qwen） | 108 | ~2.5M |
| 新模型 clean（2 个） | 194 | ~2M |
| **合计** | **~1,011** | **~18M** |

按 ~26k token/例估。人民币成本主要来自 `qwen3.8-max` 的 216 例（约 5.6M token，按 12/36 约 80 元）；其余模型便宜，总成本预计 <200 元。实际以控制台计费为准。

## 5. 作图

### Fig. 1

已完成，不需要改；除非架构或版本标识变化。保持 `paper/fig/system-architecture.html` 为唯一源，PNG 600 dpi、PDF 183×99.5 mm；改文字后跑 `self_check.py` 并重新导出。

### Fig. 2

当前三模型版本使用每模型、每场景的配对结果；如果最终是 4 个模型，可考虑改成**模型级两面板**：

- (a) 横轴 baseline ASR、纵轴 DSCG ASR，画 y=x；每个点一个模型，标注模型名与 n。
- (b) 横轴 baseline ASR、纵轴 ΔTSR（pp）或 clean 代价；看低 headroom 是否转为成本。

per-suite 数字放 Table 1 或 artifact CSV；不要把 4 模型 × 4 suite 全塞进 dumbbell。

### QA

- 数据先写 `paper/fig/model-portfolio.csv`，脚本读 CSV，不手抄。
- `require_matplotlib_panel_alignment` + `audit_pdf_text.py` + `audit_figure_collisions.py` 全过；冲突审计不通过不交付。
- 图内字号 ≥5 pt；最终宽 7.16 in；Arial/Helvetica。

## 6. 论文修改（在图/表定稿后）

1. **摘要/Intro**：保留“baseline susceptibility”，不要写“strong models are robust”；新增一句模型选择规则（先测 baseline ASR，再选高/低两端）。
2. **Protocol**：写 common grid、每模型筛选集、固定审计器 arm、非思考模式设置。
3. **Results**：模型级表/图；Qwen clean baseline 补进 clean 段；写清“以弱模型为主、保留低 ASR 边界”。
4. **Limitations**：模型数、单 benchmark、无自适应、筛选集/审计器混杂、单次运行；模型是按 baseline ASR 选的，不是随机样本。
5. **页数**：当前 4 页；4 模型版的页数仍需重新编译核对。若超页，先压 Related Work 和失败分析细节，不压结果表。

## 7. 时间线

| 时间 | 任务 |
| --- | --- |
| 11/04–11/10 | 非思考模式小改动 + 测试；Qwen baseline clean；5 模型 baseline 筛选 |
| 11/11–11/24 | 冻结 common grid；新高/低模型两臂；固定审计器；新模型 clean |
| 11/25–12/01 | 重算数字；模型级表/图；更新 Results |
| 12/02–12/15 | 改摘要/Intro/Limitations；内部评审；图 QA |
| 12/16–12/31 | 格式、引用、页数；缓冲 |
| 01/01–01/14 | 最终检查、PDF eXpress 自检、提交 |

如果只做最小版本（Qwen baseline clean + 固定审计器，不扩模型）：11 月底可定稿。

## 8. 风险与止损

| 风险 | 止损 |
| --- | --- |
| 自定义 DashScope endpoint 不提供 qwen3.8 系列 | 先 smoke；不可用则切官方 `https://dashscope.aliyuncs.com/compatible-mode/v1`，记录实际 base_url；仍不可用就停，不换 provider |
| 非思考参数被忽略 | 检查响应 `reasoning_content`/reasoning tokens；有则停用该模型，不混入主表 |
| qwen3.8-flash 的 baseline ASR 也很低 | 补 qwen3.5-flash 作为第二个高易感点；不硬说“新一代小模型也弱” |
| 固定审计器显示 DeepSeek 低 ASR 主要来自审计器 | 如实报告；把“强模型”改成“主模型+审计器组合”，仍是有效发现 |
| 4 模型 6 页放不下 | 模型级表/图；per-suite 进 artifact；正文只留关键数字 |
| “只测弱模型”被质疑 | 保留 DeepSeek 低 ASR 边界；写明按 baseline ASR 选模型与 headroom 偏差 |

## 9. 明确不做

- 不把“强模型自带强防御”写成结论；不把 2.1% 当成模型普遍属性。
- 不用非 DashScope provider，不引入 GPT/Claude/Llama 等外部 key。
- 不做多 seed、全量重跑、超大模型矩阵。
- 不新增机制、不改评分/分母、不重标原生 ASR。

## 10. 需要你确认

1. 接受“Qwen3.7-Flash + DeepSeek-Flash + 2 个 DashScope 新模型”的 4 模型方案吗？
2. 同意先做非思考模式小改动（`extra_body.enable_thinking=false`）并跑 Qwen baseline clean + 5 模型 baseline 筛选吗？
3. 如果筛选后只能再跑一个：优先选观测 ASR 最高的新模型（弱模型复现），还是 `qwen3.8-max`（低 headroom 边界）？我建议前者 + 保留 DeepSeek 边界。
