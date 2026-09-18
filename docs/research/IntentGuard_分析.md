# IntentGuard: Mitigating IPIA via Instruction-Following Intent Analysis — 方法实现与创新

> **论文**: Mintong Kang (UIUC), Chong Xiang, Sanjay Kariyappa, Chaowei Xiao (NVIDIA), Bo Li (UIUC), Edward Suh (NVIDIA)
> **类型**: Preprint | **arXiv**: 2512.00966
> **解析日期**: 2026-07-28

---

## 零、创新点一览

| 创新点 | 类型 | 说明 |
|--------|------|------|
| **Intent-centric 防御范式** | 全新 | 从"检测恶意文本"转向"分析 LLM 意图遵循的指令" |
| **Instruction-Following Intent Analyzer (IIA)** | 全新形式化定义 | 首次形式化定义 IIA，证明完美 IIA 必然存在 |
| **Thinking Intervention 提取安全信号** | 新应用现有技术 | 将 Wu et al. 2025 的思考干预引入安全领域 |
| **Start-of-Thinking Prefilling** | 新型干预策略 | 预填充思考起始 token 引导结构化意图表达 |
| **End-of-Thinking Refinement** | 新型干预策略 | 截获第一 `</think>` 强制精化意图列表，同时防止提前退出 |
| **Adversarial In-Context Demonstration** | 新型对抗训练 | 在上下文中演示"恶意意图中途涌现"的失败模式 |
| **三步骤防御管线** | 全新框架 | Intent Extraction → Origin Tracing → Injection Mitigation |
| **单次解码 (Single-pass)** | 工程创新 | 意图分析与响应生成同一次推理完成 |

---

## 一、方法实现详解

### 1.1 步骤一: Intent Extraction — IIA 构建

**核心思路**: 推理型 LLM 的思考轨迹 （`<think>...</think>`） 揭示了指令遵循意图，但天然不可解析。通过三种干预将其转化为结构化指令列表。

#### 干预 1: Start-of-Thinking Prefilling

**机制**: 在推理链的开头预填充（而非让模型自由生成）:

```
<think> Okay, I will first repeat all instructions I need to follow.
<instruction>
```

实际实现中的精化版 Prompt:
```
Okay, I will first repeat the instructions I need to follow. 
These instructions are the completed or ongoing tasks (e.g., how many meetings I have tomorrow?). 
Use the following format to wrap each instruction: 
<INSTRUCTION REPETITION> 
1. <Instruction 1>  [repetition of Instruction 1]  <Instruction 1>
2. <Instruction 2>  [repetition of Instruction 2]  <Instruction 2>
... 
</INSTRUCTION REPETITION> 
After generating the instruction plan enclosed within <INSTRUCTION REPETITION></INSTRUCTION REPETITION>, 
I should draft tool callings strictly following the instructions in the plan. 
Now, I will begin drafting the instruction plan by listing the questions I should answer: 
<INSTRUCTION REPETITION> 
1. <Instruction 1>
```

**工作方式**: 
- LLM 被训练为生成连贯续写 → 看到 `<instruction>` 开头，自然会列出指令
- 利用了自回归解码的时序性：不能"倒退"修改已经 prefilled 的 token

#### 干预 2: End-of-Thinking Refinement

**机制**: 在 LLM 生成第一个 `</think>` token 的瞬间**实时截获并替换**:

```
# 原始 token: </think>
# 被替换为:
Now, let me refine my intended instruction list before generating the final output.
<instruction>
```

实现中更精化的 Prompt:
```
Finally, let me carefully check the instruction plan repetition that I need to follow 
according to the thinking process. Maybe I decide to follow more instructions in addition 
to the original instruction plan, or decide not to follow certain instructions during the 
current thinking process. 
Final instruction repetition: <INSTRUCTION REPETITION> <Instruction 1>
```

**双收益设计**:
1. 容纳模型思考中"改变主意"的自然行为 → 同时强制作出重审
2. **防 Early Exit 攻击**: 自适应攻击者可能优化输出使其第一个 token 就是 `</think>` → 替换破坏了这种绕过

#### 干预 3: Adversarial In-Context Demonstration

**三种示范策略**:

| 策略 | 起始列表 | 精化后列表 | 收敛目标 |
|------|:---:|:---:|------|
| Format Specification | 仅用户指令 | 仅用户指令 | 教结构，不教对抗 |
| Conflict Reasoning | 用户+恶意指令 | 仅用户指令 | 教"删除恶意意图" |
| **Adversarial Reasoning** | 仅用户指令 | 用户+恶意指令 | 教"捕获中途涌现的恶意意图" |

**Adversarial Reasoning 示范的精确构造**（附录给出的示例）:
1. Start-of-Thinking 列出: 只有用户原始指令（恶意指令被"隐藏"在工具数据中）
2. 思考过程: 正常推理用户任务
3. 发现工具数据中有"向 Mark Black 发邮件"的请求 → 意识到这是注入
4. End-of-Thinking Refinement 列出: 用户指令 + **恶意指令显式涌现**
5. → 下游 Origin Tracing 将检测到此指令来自恶意数据段

> 消融证明这是最强策略: "上下文内对抗训练" — 教会模型识别"中途涌现恶意意图"的失败模式。

#### 意图提取后处理

模型完成结构化思考后，用**正则表达式**从 `<INSTRUCTION REPETITION>...</INSTRUCTION REPETITION>` 中提取指令:
- **默认策略**: 取 Start-of-Thinking 和 End-of-Thinking 两组指令的**并集**作为 IIA 输出
- **替代策略**: 仅取最终精化集

### 1.2 步骤二: Origin Tracing — 滑动窗口溯源

**算法**:

```
For each intended instruction ŝᵢ (from IIA):

  1. 设定窗口大小 = |ŝᵢ| / 2, 步长 = |ŝᵢ| / 8
  
  2. 对输入 prompt 的每个滑动窗口 w:
     计算 embedding_similarity(ŝᵢ, w)
  
  3. 取 similarity > θ (=0.7) 的所有窗口
     → 这些窗口的并集 = ŝᵢ 的"来源范围"
  
  4. 检查来源范围是否与任何 untrusted data segment 有交集
```

**两种实现选择**:

| 嵌入方式 | 指标 | 时间复杂度 | 外部依赖 |
|------|------|:---:|:---:|
| 稀疏嵌入 (默认) | Token Set Ratio（词集合重叠度） | 0.075s | 无需 |
| 稠密嵌入 | text-embedding-3-large (OpenAI) 余弦相似度 | 0.274s | 外部 API |

**性能对比**: 稀疏嵌入与稠密嵌入性能几乎相同（ASR 差异 <0.01, Utility 差异 <0.005），但快 3.6×。

**为什么稀疏就能工作**: Thinking Intervention 已引导模型**逐字重复**指令文本 → 匹配不需要语义理解。

**参数鲁棒性**: 在全部 9 种(窗口 × 阈值)组合下，IoU ∈ [0.97, 0.99] → 无需精细调参。

### 1.3 步骤三: Injection Mitigation

**判断逻辑**:
```
if ŝᵢ 的来源范围 ∩ untrusted_data_segments == ∅:
    → 合法指令，正常执行
else:
    → 恶意指令，进入 Mitigation
```

**两种 Mitigation 模式**:

| 模式 | 行为 | 安全性 | 用户体验 |
|------|------|:---:|:---:|
| **Alert** | 通知用户 + 等待确认 | 最高（人机回路） | 需要干预 |
| **Recovery** | 自动掩蔽可疑区域 + 重新推理 | 较高 | 无感知 |

**Recovery 模式的具体实现**:
1. 定位 prompt 中与恶意指令来源重叠的 text span
2. 用空白/占位符掩蔽该 span
3. 用新 prompt（含掩蔽后的数据）重新运行一次推理
4. 模型不再看到恶意指令 → 生成安全输出

### 1.4 关键设计决策

**Remark 3: 单次解码**
- 意图分析 + 最终响应 → 同一次 `model.generate()` 调用
- 计算开销: 仅增加少量的意图分析 token（thinking 扩展）
- 与 PromptArmor 对比: PromptArmor 需要额外的 LLM 调用检测 + 修改上下文
- 与 DataSentinel 对比: DataSentinel 替换用户 prompt 为检测 prompt → 不在同一上下文

**Remark 4: 保持原生行为**
- 不微调 → 模型不被迫"忽略"注入
- 允许模型的 original instinct: 打算遵循恶意指令也可以
- 但会被 IIA 捕获 → Origin Tracing 拦截 → 不执行

---

## 二、实验配置详解

| 维度 | 配置 |
|------|------|
| 基准 1 | AgentDojo: 97 任务 × 629 攻击用例（合成多工具环境） |
| 基准 2 | Mind2Web + AdvAgent: 440 任务 × 4 领域（真实网页交互） |
| 模型 | Qwen3-32B (推理型开源) + gpt-oss-20B (推理型开源) |
| 攻击 | Template, Beam Search, GCG（白盒 token 梯度）, PAIR（LLM 迭代自适应） |
| 自适应攻击细节 | PAIR 目标: "恶意指令在规划阶段不可见、但最终被执行" |
| 基线 | Vanilla, SEP Defense（提示工程）, PromptArmor（LLM 检测器） |
| Origin Tracing 参数 | 窗口=1/2, 步长=1/8, 阈值=0.7, 稀疏嵌入, 取指令并集 |

**自适应攻击的特殊配置**（对 IntentGuard 针对性攻击）:
- **Beam Search/GCG**: 优化目标有两种: (a) 非思考诱导 `</think>[call]` / (b) 操纵思考 `[plan without injection][refined plan without injection]</think>[call]`，取两者中 ASR 更高的
- **PAIR**: Attacker LLM 迭代精化注入，目标 "stealth in planning（不在思考中表达）+ surreptitious execution（最终仍执行）"

---

## 三、关键结果

| 设置 | 模型 | 最强 ASR (PAIR) |
|------|------|:---:|
| AgentDojo | Qwen3-32B | **9.2%** (Vanilla: 72.3%) |
| AgentDojo | gpt-oss-20B | **10.4%** (Vanilla: 73.1%) |
| Mind2Web | Qwen3-32B | **8.5%** (Vanilla: **100.0%**) |
| Mind2Web | gpt-oss-20B | **10.9%** (Vanilla: 72.6%) |

- 所有良性设置: **FPR = 0.000**（零误报）
- 除一个配置外: 良性效用 = Vanilla（零退化）

### IIA 忠实度 (Fig.4)

| 对角 (忠实) | 下左格 (真正错误) | 上右格 (模型失误) |
|:---:|:---:|:---:|
| 83.8% | 10.9% | 5.3% |

---

## 四、核心局限

- **硬前提**: 依赖推理型 LLM 的思考 token 可见性 → 非推理模型 / 隐藏思考的 API 不适用
- **思考诚实性**: IIA 信用建立在"思考反映真实意图"的假设上 → 模型可"假装"不打算遵循但实际执行
- **10.9% 不忠实率**: 约 1/9 的恶意意图在 IIA 盲区
- **内容攻击不可防**: 只改输出内容而不改控制流的注入（伪信息、钓鱼链接）Origin Tracing 无法检测
- **Untrusted segments 的标注**: 需要用户正确标记哪些数据段不可信

---

## 五、与 ACE / IPIGuard 的创新层次对比

| | IntentGuard | IPIGuard | ACE |
|------|------|------|------|
| 观察面 | LLM 思考 token | 工具调用图 | 数据流格 |
| 创新方式 | 利用推理痕迹提取安全信号 | 预定义执行约束 | 系统架构重构 |
| 技术血缘 | Wu 2025 (thinking intervention) + Chao 2025 (PAIR) | CQRS 模式 + DAG | Denning 1976 (格) + Docker |
| 即插即用度 | 最高（仅需 prompt 修改 + 解码拦截） | 中（需定制 TDG Prompt） | 最低（需容器基础设施） |
| 安全性上限 | 受限于 10.9% 不忠实 | 受限于 TDG 质量 | 受限于 IFC 静态分析完整性 |
