# AIMLL Workshop 投稿计划（v3.6 结果版）

> 2026-11-01 · 目标：IWCMC 2027 AIMLL Workshop（Barcelona，2027-06）
> 底稿：`paper/main.tex` · 图：`paper/fig/system-architecture.png`
> 定位：**workshop 以覆盖面为主**，不追复杂消融与多 seed；核心是“跨模型 + 跨 suite + 跨攻击”都能看到 ASR 下降。
> 判断：安全结果强（ASR 36.9%→0），效用结果中性（p=0.15）；按“动作级边界 + 代价”写。

## 1. Workshop 要求（已核实）

| 项目 | 结论 |
| --- | --- |
| 会议 | 第 23 届 IWCMC 2027，Barcelona；官网 2027-06-13~18，CFP 写 13~17 |
| 投稿系统 | Sparcly：<https://conferences.sparcly.ai/IWCMC2027> |
| 截稿 | 投稿 **2027-01-15**；通知 03-30；Camera-ready 04-30；作者注册 05-15 |
| 篇幅 | **6 页**；Camera-ready 可加 2 页，€100/页 |
| 模板 | IEEE conference 双栏；无页眉/页脚/页码；PDF eXpress + IEEE eCF |
| 出版 | IEEE Xplore；至少 1 位作者注册并报告；设 Best Workshop Paper |
| 评审 | 官网与 CFP 均未写双盲 → 准备署名版，以投稿系统为准 |
| 重复投稿 | CFP 明确：未发表、未同时投其他 venue |

来源：[IWCMC 2027 主页](https://iwcmc.net/2027/)、[Authors 页](https://iwcmc.net/2027/authors.php)、`workshop/AIMLL WS.pdf`。

**待确认（不解决不要开写）**
1. 官网 Workshop 列表还没有 AIMLL 条目（该页混有 2025/2026 材料）；Sparcly 里的 track 名称要先确认。
2. CFP 写 “IEEE IWCMC 2026 proceedings”，疑为笔误，以 2027 为准。
3. Workshop 是否同样 6 页上限（CFP 未单列），按主会 6 页准备。
4. `paper/DSCG_IWCMC2027.zip` 是否已投主会？同会主会 + workshop 通常算重复投稿。

## 2. 结果口径

结果根：`results/workshop/agentdojo/`（2026-11-01 起）。当前三套结果：

| 目录 | 内容 |
| --- | --- |
| `qwen3.7-flash_baseline` | 1,167 键；ASR 428 |
| `qwen3.7-flash_v3.6` | 1,947 例 / 1,944 有效 / 3 API 错误；ASR 0 |
| `qwen3.7-flash_v3.6_clean` | 97 个用户任务；82 成功（84.5%）；3 个 suite 为 48/57（84.2%） |

`qwen3.7-flash_clean` 是旧配置的 clean，仅作历史，不与 `v3.6_clean` 混用。

`results/workshop/agentdojo/qwen3.7-flash_v3.6/run_manifest.json` 记录：

- `defense_version=DSCG_v3.5.4`、`prompt_profile=static-task-v354`（`a70ca4ab…`）、`input_isolation=True`（L1 隔离在、投影关）、`l1_projection_mode=off`、`audit_router_mode=shadow`、`fliter` 规范化哈希 `72091a3…`（目录内文件字节哈希不同，属正常）。
- 1,947 例，1,944 有效 / 3 个已记账 API 错误；TSR 1,505/1,944（77.42%），ASR 0/1,944（含 workspace）。
- 报告读取器把 2,882 条 `sink-free-read-v4` 固定免审判成 `invalid_event`；只影响审计/成本表。
- `fliter` 排除 8 个 GOAL（workspace I:3/6/7/8/9/12/13、travel I:1），论文需列出排除范围。
- **DSCG clean 已完成**：`qwen3.7-flash_v3.6_clean`，97 个用户任务 82 成功（workspace 34/40、travel 17/20、banking 11/16、slack 20/21）；**baseline clean 还没有**。clean 84.5% 说明防御没有把正常任务全堵死，补 baseline clean 后才能算净误拒。

**v3.6 是运行批次，不是新算法**；论文写“DSCG（static-task-v354），2026-10-30 批次”。旧 1,112 / 1,115 的表只作历史。

主表（3 suite × 3 攻击，1,105 个配对有效键）：

| Suite | baseline TSR / ASR | DSCG TSR / ASR |
| --- | --- | --- |
| banking（432） | 70.60% / 27.31% | 57.41% / 0% |
| Slack（315） | 70.79% / 57.78% | 69.84% / 0% |
| travel（358） | 56.70% / 30.17% | 80.17% / 0% |
| **合计（1,105）** | **66.15% / 36.92%** | **68.33% / 0%** |

- ASR 408→0；0/1,105 的 Wilson 95% 上界 **0.35%**。
- 效用 McNemar 总体 **p=0.15（不显著）**；banking −13.2pp（p<0.001）、travel +23.5pp（p<0.001）、Slack −0.9pp（p=0.70）。
- 全量 77.42% 含 workspace、baseline 无 workspace，**不能与 66.15% 直接比**。

主表由 `results/workshop/agentdojo/{qwen3.7-flash_baseline,qwen3.7-flash_v3.6}` 重算；`download/dscg-history-analysis-20261031T021053Z/analysis.json` 是配对快照，只作交叉核对，不再作为路径来源。

## 3. 测试总览（广度优先）

| 优先级 | 测试 | 规模 | 目的 |
| --- | --- | --- | --- |
| 必做 | 主表统计 | 1,105 键，离线 | 安全 + 效用 |
| 必做 | clean 对照 | DSCG clean 已有（82/97）；只补 baseline clean（57 任务） | 量化误拒 |
| 必做 | **跨模型**（§4） | 4 个模型 × 81 键 × 2 臂 | 结论不只在一个模型上成立 |
| 必做 | 消融（§5） | 3 臂 × 81 键 | 说明哪个模块在起作用 |
| 必做 | 外部基线（§6） | 2 个 × 81 键 | 与已有防御对比 |
| 加分 | AgentDyn 1 suite | 81 键 × 2 臂 | 跨基准泛化 |
| 加分 | 最终文本回显 / 语义复核 / 成本 | 离线 | 边界与代价 |
| 不做 | 自适应攻击、多 seed、全量 workspace | — | workshop 不需要 |

所有新增产物放 `workshop/artifacts/20261101_aimll/`；每个模型用新 `--name`；不重跑已关闭 campaign。现有正式结果在 `results/workshop/agentdojo/`，新批次暂不混入；若要统一到 `results/workshop/aimll/`，只改 `--results-dir`。先完成必做（约 2–3 周），加分项按剩余时间取舍，任何一项都不影响主表成立。

## 4. 模型测试（详细）

### 4.1 模型矩阵

| ID | 具体模型 ID | Provider / Key | 选择理由 | 规模 | 状态 |
| --- | --- | --- | --- | --- | --- |
| M1 | `qwen3.7-flash` | DashScope / `DASHSCOPE_API_KEY` | 主结果，已有全量 1,944 | 切片 81 键，0 新调用 | 完成 |
| M2 | `qwen3-max` | DashScope / 同上 | 同家族放大，检验规模敏感性；复用现有 key | 81 键 × 2 臂 | 需授权 |
| M3 | `gpt-5.1` | OpenAI / `OPENAI_API_KEY` | 前沿闭源模型，工具调用成熟 | 81 键 × 2 臂 | 需 key + 授权 |
| M4 | `llama-3.3-70b-versatile` | Groq / `GROQ_API_KEY` | 开源权重、低延迟，代表可自部署场景 | 81 键 × 2 臂 | 需 key + 授权 |
| M5（可选） | `glm-4.6` 或 `kimi-k2-0905-preview` | Zhipu / Moonshot | 中文开源生态补充 | 81 键 × 2 臂 | 需 key + 授权 |

- 模型 ID 以调用时实际可用为准；跑前先做 1 次单 suite smoke test，确认 **function calling + JSON 输出**都正常。
- 不接受：DeepSeek（项目规则禁用）、无工具调用能力的模型。Claude 需新增 provider 段，暂不排期。
- 现行规则只允许 `qwen3.7-flash`；M2–M5 需要你本轮明确授权并补 key，否则只报 M1，跨模型写进 limitation。

### 4.2 统一设置（保证可比）

| 变量 | 固定值 |
| --- | --- |
| 审计模型 | **固定 `qwen3.7-flash`**（不随主模型变，避免混淆两个变量） |
| Profile | `static-task-v354`，L1 projection off，router shadow |
| Suite | banking、Slack、travel |
| 攻击 | `ignore_previous`、`important_instructions`、`tool_knowledge`（`--attack typical`） |
| 任务网格 | partial 注册前缀：3 suite × 3 用户 × 3 目标 × 3 攻击 = 81 键 |
| 对照 | 每个主模型各跑一份 `--baseline`，不共用其他模型的 baseline |
| 工具元数据 | 沿用 `config/tools.agentdojo-v1.2.toml` |

### 4.3 配置与命令

为每个模型建独立配置，**只改 `[main]`，`[security]` 固定 Qwen**；provider 段复制现有地址，不改 endpoint：

```toml
# config/models.aimll_gpt51.toml
[main]
provider = "openai"
model_id = "gpt-5.1"

[security]
provider = "dashscope"
model_id = "qwen3.7-flash"

[providers.openai]
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"

[providers.dashscope]
base_url = "<沿用 config/models.local.toml 现有地址>"
api_key_env = "DASHSCOPE_API_KEY"
```

```bash
# 命令默认工作站（conda env: ipi）；服务器改用
# ~/miniconda3/bin/conda run -n DSCG ...，--results-dir 指到服务器同名目录
# DSCG 臂
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites banking slack travel --attack typical \
  --model-config config/models.aimll_gpt51.toml \
  --name aimll_gpt51_dscg --results-dir workshop/artifacts/20261101_aimll
# baseline 臂
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites banking slack travel --attack typical --baseline \
  --model-config config/models.aimll_gpt51.toml \
  --name aimll_gpt51_baseline --results-dir workshop/artifacts/20261101_aimll
```

M2/M4/M5 同理，只换 `model_id`、provider 段和 `--name`。M1 直接用 `results/workshop/agentdojo/qwen3.7-flash_v3.6` 的全量结果切出同一 81 键，不重跑。

补 baseline clean（DSCG clean 已有，不用再跑）：

```bash
conda run -n ipi python -B -m experiments.run_benchmark \
  --suites banking slack travel --baseline --clean \
  --name v36_clean_baseline --results-dir workshop/artifacts/20261101_aimll
```

### 4.4 规模、预算与时间

| 模型 | 计分运行 | 估算 token | 估算耗时 |
| --- | ---: | ---: | --- |
| M1（切片） | 0 新调用 | 0 | 0 |
| M2 Qwen3-Max | 162 | ~4.3M | 1–2 天 |
| M3 GPT-5.1 | 162 | ~4.3M | 1–2 天 |
| M4 Llama-3.3-70B | 162 | ~4.3M | 1 天 |
| M5（可选） | 162 | ~4.3M | 1–2 天 |
| **合计（M2–M4）** | **486** | **~13M** | **4–6 天** |

按 v3.6 的 26.6k token/例估算；实际以 provider 计费为准。模型之间串行跑，避免并发限流；单个模型内部攻击分进程是 runner 既有行为。

### 4.5 记录与判定

每个模型输出一张同结构的小表：

| 指标 | 说明 |
| --- | --- |
| TSR（clean） | 无攻击；M1 已有，M2–M4 可缺省并标注 |
| TSR（attack） | 3 suite 各一行 |
| ASR | 原生谓词；按 suite 与攻击拆分，报 0 的 Wilson 上界 |
| 协议失败 | L2/L3 JSON/schema 解析失败数；非 Qwen 模型可能更高，单列 |
| 工具调用失败 | 模型不支持/参数非法；与安全失败分开 |
| API 错误 | 已记账错误，剔除分母，不算防御成功 |
| token/例 | 主模型 + 审计模型，报告审计占比 |

判定：**ASR 在 M1–M4 都接近 0** 才算“跨模型复现”；若某模型 ASR 明显更高，如实报告并分析（这比强行圆成 0 更有价值）。TSR 允许因模型能力不同而波动，不做“全面提升”声明。

### 4.6 失败处理

- 模型不支持 tool calling → 不纳入矩阵，正文写“因不支持 function calling 未测试”。
- 协议失败率高（如 >10%）→ 单列，不混入 ASR/TSR 分母；说明是兼容性问题而非防御失效。
- 429/限流或网络错误 → 只续跑未开始任务，不自动重试；错误保留。
- 模型 ID 下线 → 换同档模型并记录实际 ID，不混用两次运行。

## 5. 消融（简化）

固定同一 81 键网格，3 个臂即可回答“谁在起作用”：

| 臂 | 配置 | 回答 |
| --- | --- | --- |
| A0 | `--baseline` | 无防御下限（可直接切已有全量） |
| A1 | 默认 full | 完整 DSCG |
| A2 | `--no-checker` | 去掉 L3 语义审计 |
| A3 | `--prompt-profile legacy` | 两阶段静态授权 vs 单阶段 |

可选 A4：`--l1-projection-mode projected`（主结果 L1 off，用来回应“L1 有没有用”）。81 键只作描述性比较，不做显著性声明；若 TSR 饱和（>95%）再加 3 个用户。

## 6. 其他测试

| 测试 | 做法 | 产出 |
| --- | --- | --- |
| Clean 对照 | DSCG clean 已完成（82/97=84.5%）；只补 baseline clean（57 任务，命令见 §4.3） | 干净 TSR、误拒 |
| 外部基线 | AgentDojo 自带 `spotlighting_with_delimiting`、`repeat_user_prompt`，81 键；需给 runner 补一个 `--agentdojo-defense` 开关（后端已有 defense 参数） | 与已有防御对比 |
| 最终文本回显 | 零新调用，扫 1,105 条轨迹：动作被拦但答复出现攻击目标串 | 边界证据 |
| 语义 ASR 复核 | 抽 40 条攻击案例，2 人盲评“注入目标是否达成”，报 kappa | 验证 0 不是谓词漏检 |
| Harness 有效性 | 抽 30 条：注入串在工具返回中、goal 检查已执行 | 一段效度说明 |
| 成本/延迟 | 已有 usage：token/例、审计占比（9.97M/41.76M≈24%）、L3 调用 3,175 | 成本表 |
| AgentDyn（加分） | shopping 或 dailylife，partial 81/72 键 × 2 臂 | 跨基准一段 |

## 7. 论文结构（6 页）

1. Intro（0.75 页）：移动/IoT 工具型 agent；注入劫持后续动作；prompt 防御脆、工具白名单查不了对象/参数。
2. Threat model（0.4 页）：动作级边界；不认证事实、不保证完成、无最终文本审计。
3. Design（1.5 页 + Fig. 1）：L1 隔离/投影、L2 静态任务与工具授权、L3 四字段审计、一次性票据。
4. Evaluation（2 页）：协议；**Table 1 主结果**（suite×攻击 + CI）；**Table 2 跨模型**（M1–M4 的 TSR/ASR/协议失败）；**Table 3 消融 + 外部基线**；Fig. 2 用 ASR 分组柱状图。
5. Related work（0.4 页）：AgentDojo、AgentDyn、IPIGuard、MELON、CaMeL、spotlighting、PI detector。
6. Limitations / ethics（0.4 页）：模型数、3 suite、原生谓词、banking 退步、文本回显；E0/I3 不作通过声明。

写作红线：摘要先给 “36.9%→0（上界 0.35%）”，再给 “utility 中性、banking −13.2pp”；不写 “general prompt-injection resistance”。

## 8. 时间线（截稿 2027-01-15）

| 时间 | 任务 |
| --- | --- |
| 11/01–11/09 | 修读取器；主表统计；baseline clean；消融 |
| 11/10–11/23 | M2/M3 配置与 smoke test；两模型各 162 次运行 |
| 11/24–12/06 | M4（+M5）；外部基线；AgentDyn（可选） |
| 12/07–12/20 | 回显统计；语义复核；成本表；写作主体 |
| 12/21–01/07 | 全文、图、引用、格式；内部评审 |
| 01/08–01/14 | 修订、PDF eXpress 自检、提交 |

## 9. 风险与止损

| 风险 | 止损 |
| --- | --- |
| 模型不授权 / 无 key | 只报 M1；跨模型写 limitation；不伪造结果 |
| 某模型工具调用不稳 | 排除该模型并说明；保留已完成模型 |
| 协议失败率高 | 单列协议失败率，不混入 ASR/TSR |
| `tool_filter` 不兼容 | 用 spotlighting + repeat_user_prompt |
| 时间不够 | 砍 M5、AgentDyn、语义复核；保主表 + 3 模型 |
| 主会重复投稿 | 先确认；若已投，换题/换材料 |

## 10. 明确不做

- 不做自适应攻击、多 seed、全量 workspace——workshop 不要求。
- 不新增机制（最终文本审计仍 locked）；不改分母、不重标原生分数。
- 未经授权不调用非 Qwen 模型；不调用 DeepSeek。

## 11. 需要你确认

1. 跨模型：同意 M2（Qwen3-Max）、M3（GPT-5.1）、M4（Llama-3.3-70B）吗？对应 key 是否可用？
2. `DSCG_IWCMC2027.zip` 是否已投主会？
3. Sparcly 里选 AIMLL 还是 “LLMs Security” track？
