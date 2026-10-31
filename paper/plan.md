# AIMLL Workshop 投稿计划（DSCG）

> 2026-10-31 · 目标：IWCMC 2027 AIMLL Workshop（Barcelona，2027-06-13~17；IEEE Xplore）
> 底稿：`paper/main.tex`（IEEEtran 双栏）· 架构图：`paper/fig/system-architecture.png`
> 结论：材料够投，但要先补 4 类证据并重写叙事；预计 4 周 + 1 周缓冲。

## 1. 一句话主张（先冻结，再补实验）

**任务级工具授权 + 动作审计，把动作级 ASR 从 36.9% 降到 0.1%，同时 TSR 从 65.1% 升到 71.2%；代价集中在 banking（−46 例）。**

现有底稿最大的问题不是实验少，而是**漏报了 baseline ASR**，只写了 TSR。baseline 与 v3.5.4 的 1,115 个共同有效键上：

| 集合 | baseline TSR / ASR | v3.5.4 TSR / ASR |
| --- | --- | --- |
| banking（384） | 70.57% / 27.08% | 58.59% / 0% |
| Slack（315） | 70.79% / 57.78% | 70.48% / 0% |
| travel（416） | 55.77% / 30.29% | 83.41% / 0.24% |
| 合计（1,115） | 65.11% / 36.95% | 71.21% / 0.09% |

（来源：`download/dscg-history-analysis-20261031T021053Z/analysis.json`，只读重算；论文表格目前用四版共同 1,112，需统一口径。）

## 2. 现状与缺口

| 已有 | 还缺 |
| --- | --- |
| 可运行实现、1,115 键配对、错误投影、失败分类、架构图、token 记录 | baseline ASR 未进正文；无组件消融；无外部防御基线；无同版本 clean 对照；最终文本回显未量化；AgentDyn 无在线结果；报告读取器把 2,882 条固定免审判成 `invalid_event`（影响成本/审计表）；截止、页数、作者信息未确认 |

## 3. 投稿前必须确认（未确认不要开写）

1. **重复投稿**：`paper/DSCG_IWCMC2027.zip` 是否已投 IWCMC 2027 主会？CFP 要求“未发表且未同时投稿”；同会主会 + workshop 通常算重复。需你确认。
2. **截止与页数**：CFP 只写“与主会相同”；按 IWCMC 惯例 IEEE 双栏 6 页（超页付费），以官网为准。
3. **作者信息**：CFP 未要求匿名；底稿的 `Anonymous Authors` 要按官网模板改成真实作者与单位（若实际双盲再准备匿名版）。

## 4. 实验与测试清单

新增产物一律放 `workshop/artifacts/20261101_aimll/`；在线只用 `qwen3.7-flash`；**不重跑已关闭 campaign、不擅自开全量**（本计划复用已有全量结果，只补 partial 规模）。

### P0：不做就没有论文

| # | 实验 | 规模 / 做法 | 产出 |
| --- | --- | --- | --- |
| 1 | 修报告读取器 | 让 `sink-free-read-v4` 固定免审在 shadow 下合法；用本批 2,882 条事件只读回归 | 正确的审计/成本表；不改执行规则 |
| 2 | 冻结口径 | 定一个版本（建议 v3.5.4；v3.6 备选：1,944 有效、ASR 0，但任务集合不同）、一个键集、一个分母；重算 TSR/ASR/错误并导出 CSV | Table 1 + 图数据 |
| 3 | 组件消融 | partial 网格（3 suite × 3 用户 × 3 目标 × 3 攻击 = 81 键/臂）：baseline / full / `--no-checker` / `--no-tool-view` / `--prompt-profile legacy`；L2-off 臂可补一个仅诊断用的 `use_sandbox=False` 开关 | Table 2，回答“哪个模块在起作用” |
| 4 | 外部基线 | 至少 1 个：AgentDojo 自带防御性 system prompt（零依赖）优先；`OpenAILLMToolFilter`（需适配 Qwen 兼容端点）次之；`pi_detector` 需本地权重，可选 | Table 2，避免“只跟自己比” |

示例命令（每个臂换 `--name`）：

```bash
conda run -n ipi python -B -m experiments.run_partial_benchmark \
  --suites banking slack travel --attack typical --name abl_no_checker \
  --no-checker --results-dir workshop/artifacts/20261101_aimll
```

### P1：决定论文强度

| # | 实验 | 规模 / 做法 | 产出 |
| --- | --- | --- | --- |
| 5 | clean 对照 | 同版本、~30 个用户任务、无攻击（baseline + DSCG 各一份） | 分离“攻击致任务失败”与“防御误拒” |
| 6 | 最终文本回显 | **零新调用**：在已有 1,115 条轨迹里统计“恶意动作被拦、但最终答复出现攻击目标串”的比例；再补 10–20 例定向复检 | 明确 ASR≈0 只是动作级；v3.6.1 曾出现 2/836 回显 |
| 7 | 泛化 | AgentDyn 1 个 suite（shopping 或 dailylife）≥30 例，clean + 1 攻击 | 一句“跨基准”证据；超时则删去并限定 AgentDojo |
| 8 | 成本/延迟 | 从已有 usage 汇总主模型/审计模型 token、L3 调用数、墙钟 | Table 3 或正文一段 |

### P2：可后置

9. **复现包**：代码快照、config、prompt/profile 哈希、任务清单、`fliter.json`、结果 CSV。
10. **离线回归**：两环境 `unittest` + `node --test`，确认无新增失败（不进论文，保证发布代码可用）。

## 5. 论文改写（6 页）

从“工程报告”改成“防御系统 + 受控测量”。叙事顺序：

1. Intro：移动/IoT 场景下的工具型 agent；注入可劫持后续动作；现有 prompt 防御脆、工具白名单查不了对象/参数 → DSCG 的可执行边界。
2. Threat model & scope：动作级边界；不认证事实、不保证完成、无最终文本审计。
3. Design（1.5 页 + Fig. 1）：L1 规划视图 / L2 静态任务与工具授权 / L3 四字段审计 / 一次性票据。
4. Evaluation（2 页）：协议与分母；Table 1 主结果（按 suite 与攻击）；Table 2 消融 + 外部基线；Table 3 失败分类 + 成本；Fig. 2 用“每类攻击 ASR 对比”或“效用–安全”散点。
5. Related work（8–12 篇）：AgentDojo、AgentDyn、IPIGuard、MELON、CaMeL、spotlighting、注入综述。
6. Limitations / ethics / conclusion：单模型、三 suite、原生谓词、banking 退步、文本回显；合成数据、无新攻击能力。

写作要点：摘要第一句就给 36.9%→0.1% 与 65.1%→71.2%；不要写“general prompt-injection resistance”；banking 退步要单独解释（缺参、未查询、授权漏项），不要用总平均掩盖。

## 6. 时间线

| 周 | 任务 |
| --- | --- |
| W1 | 确认投稿资格；修读取器；冻结口径；跑消融臂 |
| W2 | 外部基线；clean 对照；出 Table 1/2 |
| W3 | 文本回显统计；AgentDyn（可选）；成本表；写 Design + Evaluation |
| W4 | 全文、图、引用、格式；内部 review（`pre-submission-reviewer`）；提交 |
| W5 | 缓冲：补实验或按审稿意见修改 |

## 7. 风险与止损

| 风险 | 止损 |
| --- | --- |
| 消融显示 L3 贡献很小 | 如实报告：主闸门是授权，审计主要影响误拒/成本；卖点转为“可部署边界 + 失败分类” |
| 外部基线跑不通 | 退化为“防御性 system prompt + 内部消融”，正文注明未复现强基线 |
| 文本回显比例偏高 | 把主张收缩为“动作级安全”，回显单列为 open problem，不新增文本闸门 |
| 时间不够 | 砍 AgentDyn 与 pi_detector，保 Table 1/2 与失败分析 |

## 8. 明确不做

- 不调参追 TSR、不为凑数改分母或重标原生分数。
- 不新增机制（最终文本审计仍 locked，需研究侧另行决定）。
- 不使用 Qwen 以外的模型；不擅自开全量重跑。
- 不把工程测试或小样本当作通用安全证明。
