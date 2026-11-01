# AIMLL Workshop 投稿计划（v3.6 结果版）

> 2026-10-31 · 目标：IWCMC 2027 AIMLL Workshop（Barcelona，2027-06）
> 底稿：`paper/main.tex` · 图：`paper/fig/system-architecture.png`
> 判断：**安全结果强（ASR 36.9%→0），效用结果中性（p=0.15）**。论文按“动作级边界 + 代价”写，补 clean、消融、外部基线、跨模型/泛化几类实验即可投。

## 1. Workshop 要求（已核实）

| 项目 | 结论 |
| --- | --- |
| 会议 | 第 23 届 IWCMC 2027，Barcelona；官网 2027-06-13~18，CFP 写 13~17 |
| 投稿系统 | Sparcly：<https://conferences.sparcly.ai/IWCMC2027> |
| 截稿 | 投稿 **2027-01-15**；通知 03-30；Camera-ready 04-30；作者注册 05-15 |
| 篇幅 | **6 页**；Camera-ready 可加 2 页，€100/页 |
| 模板 | IEEE conference 双栏；无页眉/页脚/页码；PDF eXpress + IEEE eCF |
| 出版 | IEEE Xplore（需满足范围与质量要求）；至少 1 位作者注册并报告；设 Best Workshop Paper |
| 评审 | 官网与 CFP 均未写双盲 → 准备署名版，以投稿系统为准 |
| 重复投稿 | CFP 明确：未发表、未同时投其他 venue |

来源：[IWCMC 2027 主页](https://iwcmc.net/2027/)、[Authors 页](https://iwcmc.net/2027/authors.php)、`workshop/AIMLL WS.pdf`。

**待确认（影响投稿，不解决不要开写）**
1. 官网 Workshop 列表还没有 AIMLL 条目（该页混有 2025/2026 材料，另有 “LLMs Security” workshop，主席有部分重叠但不一定是同一个）；投稿系统里的 track 名称要先确认。
2. CFP 写 “IEEE IWCMC 2026 proceedings”，疑为笔误，以 2027 为准。
3. Workshop 是否同样 6 页上限（CFP 未单列），按主会 6 页准备。
4. `paper/DSCG_IWCMC2027.zip` 是否已投主会？同会主会 + workshop 通常算重复投稿。

## 2. 口径：v3.6 是运行批次，不是新算法

`results/benchmarks/agentdojo/qwen3.7-flash_v3.6/run_manifest.json` 记录：

- `defense_version=DSCG_v3.5.4`、`prompt_profile=static-task-v354`（`a70ca4ab…`）、`input_isolation=True`（L1 隔离在、投影关）、`l1_projection_mode=off`、`audit_router_mode=shadow`、`fliter` 哈希 `72091a3…`。
- 1,947 例，1,944 有效 / 3 个已记账 API 错误；TSR 1,505/1,944（77.42%），ASR 0/1,944（含 workspace）。
- 报告读取器把 2,882 条 `sink-free-read-v4` 固定免审判成 `invalid_event`；只影响审计/成本表，不影响 TSR/ASR。
- `fliter` 排除 8 个 GOAL（workspace I:3/6/7/8/9/12/13、travel I:1），论文需列出排除范围，baseline 只用剩余目标比较。

论文应写“DSCG（static-task-v354），2026-10-30 批次”，**不要写成 v3.6 算法**。旧四版共同 1,112 / 两版 1,115 的表只作历史，不再作主表。

主表口径：3 个 suite（banking/Slack/travel）× 3 攻击，baseline 与 DSCG 都有效的 1,105 个键：

| Suite | baseline TSR / ASR | DSCG TSR / ASR |
| --- | --- | --- |
| banking（432） | 70.60% / 27.31% | 57.41% / 0% |
| Slack（315） | 70.79% / 57.78% | 69.84% / 0% |
| travel（358） | 56.70% / 30.17% | 80.17% / 0% |
| **合计（1,105）** | **66.15% / 36.92%** | **68.33% / 0%** |

- ASR：408→0；0/1,105 的 Wilson 95% 上界 **0.35%**。
- 效用：McNemar 总体 **p=0.15（不显著）**；banking −13.2pp（p<0.001，退步）、travel +23.5pp（p<0.001，提升）、Slack −0.9pp（p=0.70）。
- 结论写法：**安全增益显著且大；效用整体中性，收益与误拒按 suite 分离**。不要写“全面提升”。
- 全量 77.42% 含 workspace、baseline 无 workspace，**不能与 66.15% 直接比**；正文分开写。

## 3. 实验矩阵

新增产物放 `workshop/artifacts/20261101_aimll/`；在线只允许 `qwen3.7-flash`（模型扩展见 §4）；不重跑已关闭 campaign、不擅自开全量。

### P0：不做就没有论文

| # | 实验 | 做法 / 规模 | 产出 |
| --- | --- | --- | --- |
| 1 | 冻结口径与统计 | 1,105 键重算；按 suite×攻击出表；Wilson CI、McNemar、bootstrap | Table 1 + `stats.json` |
| 2 | 修报告读取器 | 让 `sink-free-read-v4` 在 shadow 下合法（`score=null`）；用 2,882 条事件只读回归 | 正确审计/成本表 |
| 3 | **Clean 对照** | 3 suite 全部用户任务（57 个）× baseline / DSCG，无攻击 | 干净 TSR；量化误拒 |
| 4 | **组件消融** | partial 网格 81 键/臂；5 臂见 §5 | Table 2 |
| 5 | **外部基线** | AgentDojo 自带 `spotlighting_with_delimiting`、`repeat_user_prompt`；`pi_detector` 可选；`tool_filter` 仅支持 OpenAILLM，暂缓 | Table 2 |
| 6 | Harness 有效性 | 抽 30 条攻击轨迹：注入串确在工具返回中、原生 goal 检查已执行、错误被排除 | 一段效度说明 |

示例（clean，两臂各跑一次）：

```bash
# DSCG 臂
conda run -n ipi python -B -m experiments.run_benchmark \
  --suites banking slack travel --clean --name v36_clean_dscg \
  --results-dir workshop/artifacts/20261101_aimll
# baseline 臂
conda run -n ipi python -B -m experiments.run_benchmark \
  --suites banking slack travel --baseline --clean --name v36_clean_baseline \
  --results-dir workshop/artifacts/20261101_aimll
```

### P1：决定论文强度

| # | 实验 | 做法 / 规模 | 产出 |
| --- | --- | --- | --- |
| 7 | 增加模型 | 见 §4；每模型 partial 81 键 × baseline/DSCG | Table 3 |
| 8 | 泛化 AgentDyn | shopping 或 dailylife，partial（81/72 可执行），baseline + DSCG | 一段跨基准结果 |
| 9 | 最终文本回显 | **零新调用**：扫 1,105 条轨迹，统计“动作被拦但答复出现攻击目标串” | 边界证据 |
| 10 | 语义 ASR 复核 | 分层抽 40 条攻击案例，2 人盲评“注入目标是否达成”，报 kappa | 验证 ASR=0 不是谓词漏检 |
| 11 | 成本/延迟 | 已有 usage：每例 token、审计占比（当前 9.97M/41.76M≈24%）、L3 调用 3,175、p50/p95 | 成本表 |

### P2：有余力再做

| # | 实验 | 说明 |
| --- | --- | --- |
| 12 | 自适应攻击探针 | 10 条针对 L2/L3 的手工注入（伪造授权、拆分目标、编码指令）；定性，不称 benchmark |
| 13 | baseline workspace | 补齐 4 suite 对照；筛后约 280 键/攻击，成本高 |
| 14 | 复现包 | 代码快照、config、prompt 哈希、任务清单、`fliter.json`、CSV、README |
| 15 | 离线回归 | 两环境 `unittest` + `node --test`，确认无新增失败 |

## 4. 增加模型（需授权）

| 编号 | 模型 | Provider | 目的 | 状态 |
| --- | --- | --- | --- | --- |
| M1 | qwen3.7-flash | DashScope | 主结果（已有） | 完成 |
| M2 | 同 Provider 更大 Qwen（Max/Plus 档） | DashScope | 模型规模敏感性 | **需你确认**（现行规则只允许 qwen3.7-flash） |
| M3 | GPT/Claude 类 | OpenAI/Anthropic | 跨厂商泛化 | 需 key + 明确授权 |
| M4 | Llama-3.3-70B 类 | SiliconFlow/Groq | 开源权重 | 需 key + 授权 |
| A1 | 更强/更弱审计模型 | 任一 | L3 审计器强度消融（`sec_model_id`） | 需授权 |

规则：DeepSeek 仍禁用；未授权前只跑 M1，M2–M4 写进论文“future work”不算结果。M3、M4 至少落地 1 个，才有“跨模型”结论；否则只能写单模型限制。

## 5. 消融设计

固定 partial 网格：3 suite × 3 用户 × 3 目标 × 3 攻击 = 81 键/臂；baseline 子集可直接复用已有全量结果。

| 臂 | 配置 | 回答的问题 |
| --- | --- | --- |
| A0 | `--baseline` | 无防御下限 |
| A1 | 默认（full） | 完整 DSCG |
| A2 | `--no-checker` | L3 语义审计的贡献 |
| A3 | `--prompt-profile legacy` | 两阶段静态授权 vs 单阶段 |
| A4 | `--l1-projection-mode projected` | L1 投影的贡献（主结果 L1 off） |
| A5 | `--no-tool-view` | 规划视图的贡献 |
| A6 | `use_sandbox=False`（需补诊断开关） | L2 执行侧（permission sandbox）的贡献 |

注意：partial 取注册前缀 3 用户，可能饱和；若某臂 TSR>95%，改用 6 用户或加入已知困难任务（banking u4/u11/u15、Slack u13、travel u3/u15/u19）。81 键的消融只作描述性比较，不做显著性声明。

## 6. 论文改写（6 页）

1. Intro（0.75 页）：移动/IoT 工具型 agent；注入劫持后续动作；prompt 防御脆、工具白名单查不了对象/参数 → 可执行边界。
2. Threat model（0.4 页）：动作级边界；不认证事实、不保证完成、无最终文本审计。
3. Design（1.5 页 + Fig. 1）：L1 隔离/投影、L2 静态任务与工具授权、L3 四字段审计、一次性票据。
4. Evaluation（2 页）：协议与分母；Table 1 主结果（suite×攻击 + CI）；Table 2 消融 + 外部基线；Table 3 clean/模型/成本；Fig. 2 用 ASR 分组柱状图（带 CI）。
5. Related work（0.4 页）：AgentDojo、AgentDyn、IPIGuard、MELON、CaMeL、spotlighting、PI detector。
6. Limitations / ethics（0.4 页）：单/少模型、3 suite、原生谓词、banking 退步、文本回显、无自适应攻击结论；E0 仍 pending、I3 partial，只写抽样 harness 检查，不声称通过研究门槛。

写作红线：摘要先给 “36.9%→0（上界 0.35%）”，再给 “utility 中性、banking −13.2pp”；不写 “general prompt-injection resistance”；不把 0/1,105 说成绝对安全。

## 7. 时间线（截稿 2027-01-15）

| 时间 | 任务 |
| --- | --- |
| 11/01–11/14 | 修读取器；冻结口径/统计；clean 两臂；消融启动 |
| 11/15–11/28 | 消融收尾；外部基线（spotlighting/repeat_user_prompt） |
| 11/29–12/12 | 模型扩展（若授权）；AgentDyn；回显统计；语义复核 |
| 12/13–12/26 | 写作主体；Table 1/2/3、Fig. 2 |
| 12/27–01/07 | 全文、引用、格式；内部评审 |
| 01/08–01/14 | 修订、PDF eXpress 自检、提交 |

## 8. 风险与止损

| 风险 | 止损 |
| --- | --- |
| 模型不授权/无 key | 只报 M1，明确“单模型”限制；不伪造跨模型结论 |
| `tool_filter` 不兼容 | 用 spotlighting + repeat_user_prompt 两个内置基线；正文说明 |
| 消融在 prefix 上饱和 | 扩到 6 用户或困难任务子集；报告饱和 |
| 语义复核发现谓词漏检 | 如实报告，把主张收缩为“原生谓词下 ASR=0” |
| 时间不够 | 砍 AgentDyn、pi_detector、自适应探针；保 Table 1/2 和 clean |
| 主会重复投稿 | 先确认；若已投，换题/换材料或改投 |

## 9. 明确不做

- 不新增机制（最终文本审计仍 locked）；不为凑数改分母、重标原生分数。
- 未经授权不调用非 Qwen 模型；不调用 DeepSeek。
- 不擅自重跑全量；不把工程测试或小样本当通用安全证明。

## 10. 需要你确认

1. `DSCG_IWCMC2027.zip` 是否已投 IWCMC 2027 主会？
2. 模型扩展：同意放开哪些（M2/M3/M4）？对应 key 是否可用？
3. Workshop track：Sparcly 里选 AIMLL 还是 “LLMs Security”？
