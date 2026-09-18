# 2025-2026年顶会 Indirect Prompt Injection 相关论文综述

> 资料来源：arXiv 检索，最后一并搜索了2024年底发表、录用于2025顶会的相关论文。
> 分类维度：攻击（Attack）、防御（Defense）、测试/基准（Benchmark）、综述/立场（Survey/Position）

---

## 一、攻击（Attack）

### 1. Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents
- **会议**：NAACL 2025 Findings
- **arXiv**：2503.00061
- **作者**：Qiusi Zhan, Richard Fang, Henil Shalin Panchal, Daniel Kang
- **摘要**：针对8种现有IPI防御方法开展自适应攻击评估，发现所有防御均可被突破，攻击成功率超过50%。揭示了当前防御在自适应攻击面前的根本脆弱性，强调防御设计必须考虑自适应攻击场景。

### 2. Self-interpreting Adversarial Images
- **会议**：USENIX Security 2025
- **arXiv**：2407.08970
- **作者**：Tingwei Zhang, Collin Zhang, John X. Morris, Eugene Bagdasarian, Vitaly Shmatikov
- **摘要**：提出一种新型跨模态间接注入攻击——"自解释图像"。攻击者在图像中嵌入隐藏的"元指令"（meta-instructions），控制VLM如何解释图像内容，可实现政治倾向引导、风格操控等效果，且比纯文本注入更强。

### 3. When AI Meets the Web: Prompt Injection Risks in Third-Party AI Chatbot Plugins
- **会议**：IEEE S&P 2026
- **arXiv**：2511.05797
- **作者**：Yigitcan Kaya, Anton Landerer, Stijn Pletinckx, Michelle Zimmermann, Christopher Kruegel, Giovanni Vigna
- **摘要**：首个大规模实证研究，分析17款第三方聊天机器人插件（覆盖10,000+网站）的注入风险。发现8款插件无法保证对话历史完整性，15款插件的网页抓取工具不区分受信/非受信内容，导致间接注入漏洞。会话历史伪造可使攻击影响放大3-8倍。

### 4. CHAI: Command Hijacking against embodied AI
- **会议**：IEEE SaTML（Secure and Trustworthy Machine Learning）
- **arXiv**：2510.00181
- **作者**：Luis Burbano, Diego Ortiz, Qi Sun, Siwei Yang, Haoqin Tu, Cihang Xie, Yinzhi Cao, Alvaro A. Cardenas
- **摘要**：提出物理环境间接提示注入攻击CHAI，通过在视觉输入中嵌入欺骗性自然语言指令（如误导性路牌），劫持具身AI系统（如无人机、自动驾驶、机器人车辆）。实验证明CHAI持续优于SOTA攻击方法。

### 5. ChatInject: Abusing Chat Templates for Prompt Injection in LLM Agents
- **会议**：ICLR 2026
- **arXiv**：2509.22830
- **作者**：Hwan Chang, Yonghyun Jun, Hwanhee Lee
- **摘要**：利用LLM对聊天模板的结构化依赖，将恶意载荷格式化为原生聊天模板形式；并开发基于多轮说服的变体，逐轮诱导agent接受并执行恶意操作。在AgentDojo上ASR从5.18%提升至32.05%，多轮变体在InjecAgent上达52.33%。现有防御基本无效。

### 6. Manipulating LLM Web Agents with Indirect Prompt Injection Attack via HTML Accessibility Tree
- **会议**：EMNLP 2025 (System Demonstrations)
- **arXiv**：2507.14799
- **作者**：（待查）
- **摘要**：攻击者在网页HTML中嵌入针对无障碍树（accessibility tree）的通用对抗触发词，劫持LLM驱动的Web agent进行凭证窃取和强制广告点击。使用GCG配合Browser Gym agent进行攻击生成。

### 7. TopicAttack: An Indirect Prompt Injection Attack via Topic Transition
- **会议**：EMNLP 2025
- **arXiv**：2507.13686
- **作者**：（待查）
- **摘要**：提出TopicAttack，通过生成虚假的对话话题过渡提示，逐步将话题引向注入指令。即使面对多种防御方法，ASR仍超90%，核心机制是实现更高的注入与原始注意力比。

### 8. Hiding in Plain Floats: Steganographic Carriers for Indirect Prompt and Content Injection
- **会议**：FAGEN @ ICML 2026（Workshop Poster）
- **arXiv**：2606.08403
- **作者**：Mudit Sinha, Sanika Chavan
- **摘要**：研究利用结构化浮点参数作为隐写载体的IPI攻击方法。基于IFS的浮点数组载体在最强双层文本分类器防御下仍保持94.3%的注入泄露ASR，暴露了纯文本检测的边界。

### 9. VATS: Exploiting Implicit Authority in Error-Path Injection via Systematic Mutation
- **会议**：AIWILD @ ICML 2026（Workshop）
- **arXiv**：2606.07992
- **作者**：Harshil Patel, Kunal Pai
- **摘要**：提出VATS变异驱动框架，利用MCP-based agent中工具错误消息的隐式权威进行注入攻击。错误路径注入可将IPI成功率提升三倍（达100%合规率），其中在错误上下文中的"夹心"（sandwiching）指令是最有效的利用向量。

### 10. Attacks by Content: Automated Fact-checking is an AI Security Issue
- **会议**：EMNLP 2025
- **arXiv**：2510.11238
- **作者**：Michael Schlichtkrull
- **摘要**：提出"内容攻击"（Attack by Content）概念——攻击者无需注入指令，仅通过提供偏见性、误导性或虚假信息即可操控agent。现有基于指令检测的防御对此无效。提出将自动化事实核查改造为agent的认知自卫工具。

### 11. MIRAGE: Stealthy Visual Prompt Injection for Vulnerability Detection in Web Agents
- **会议**：2026年预印本（暂无会议信息）
- **arXiv**：2606.20717
- **作者**：Xuelong Dai, Jianyu Ma, Boyang Ma, Biwei Yan, Yijun Yang, Yue Zhang
- **摘要**：提出MIRAGE视觉间接注入框架，利用扩散模型在攻击者控制的受限区域内（如广告位、赞助卡片）生成感知上良性的对抗图像。采用曲率感知对抗扩散引导结合稀疏暗像素残差扰动，对SeeAct和OpenClaw agent有效。

---

## 二、防御（Defense）

### 1. MELON: Provable Defense Against Indirect Prompt Injection Attacks in AI Agents
- **会议**：ICML 2025
- **arXiv**：2502.05174
- **作者**：Kaijie Zhu, Xianjun Yang, Jindong Wang, Wenbo Guo, William Yang Wang
- **摘要**：核心观察：攻击成功时，agent的下一步动作对用户任务的依赖性降低，对恶意任务的依赖性升高。基于此设计MELON（Masked re-Execution and Tool ComparisON），通过重新执行带掩码用户提示的agent轨迹并比较动作相似度来检测攻击。在AgentDojo上优于SOTA防御，且可与提示增强防御结合。

### 2. Rennervate: Attention is All You Need to Defend Against Indirect Prompt Injection Attacks in LLMs
- **会议**：NDSS 2026
- **arXiv**：2512.08417
- **作者**：Yinan Zhong, Qianhao Miao, Yanjiao Chen, Jiangyi Deng, Yushi Cheng, Wenyuan Xu
- **摘要**：利用注意力特征进行细粒度token级IPI检测和精确净化。通过两步注意力池化机制聚合注意力头和响应token，实现IPI检测和移除。在5个LLM和6个数据集上超越15种商业和学术防御方法，且对未见攻击具有可迁移性。

### 3. SelfDefend: LLMs Can Defend Themselves against Jailbreaking in a Practical Manner
- **会议**：USENIX Security 2025
- **arXiv**：2406.05498
- **作者**：Xunguang Wang, Daoyuan Wu, Zhenlan Ji, Zongjie Li, Pingchuan Ma, Shuai Wang, Yingjiu Li, Yang Liu, Ning Liu, Juergen Rahmel
- **摘要**：受传统影子栈安全概念的启发，提出SelfDefend框架，建立影子LLM作为防御实例与目标LLM并发工作、协作进行基于检查点的访问控制。通过数据蒸馏训练专用开源防御模型，超越7种SOTA防御，且对自适应越狱和提示注入具有鲁棒性。

### 4. Can Indirect Prompt Injection Attacks Be Detected and Removed?
- **会议**：ACL 2025 Main
- **arXiv**：2502.16580
- **作者**：Yulin Chen, Haoran Li, Yuan Sui, Yufei He, Yue Liu, Yangqiu Song, Bryan Hooi
- **摘要**：研究IPI检测与移除的可行性。构建评估基准数据集，评估现有LLM和开源检测模型的检测性能，并训练专用检测模型。对于移除，评估分段移除法（分割文档去除注入部分）和提取移除法（训练提取模型识别并移除注入指令）。

### 5. InstructDetector: Defending against Indirect Prompt Injection by Instruction Detection
- **会议**：EMNLP 2025 Findings
- **arXiv**：2505.06311
- **作者**：（待查）
- **摘要**：利用中间LLM层的隐藏状态和梯度来检测外部内容中的指令。域内检测准确率99.60%，域外准确率96.90%。在BIPIA基准上将ASR降至0.03%，同时保持良性效用。

### 6. IPIGuard: A Novel Tool Dependency Graph-Based Defense Against Indirect Prompt Injection in LLM Agents
- **会议**：EMNLP 2025
- **arXiv**：2508.15310
- **作者**：（待查）
- **摘要**：将agent任务执行建模为在预先规划的工具依赖图（TDG）上的遍历，从而将动作规划与外部数据交互解耦，防止恶意工具调用。在标准IPI基准上验证了防御效果。
- [x] 已读


### 7. ACE: A Security Architecture for LLM-Integrated App Systems
- **会议**：NDSS 2026
- **arXiv**：2504.20984
- **作者**：（待查）
- **摘要**：提出ACE（Abstract-Concrete-Execute）安全架构，将应用规划解耦为受信的抽象计划和具体的应用映射，通过静态分析和数据/能力屏障强制执行安全信息流。在InjecAgent和ASB基准上验证了安全性。
- [x] 已读

### 8. IntentGuard: Mitigating Indirect Prompt Injection via Instruction-Following Intent Analysis
- **会议**：预印本（暂无会议信息）
- **arXiv**：2512.00966
- **作者**：Mintong Kang, Chong Xiang, Sanjay Kariyappa, Chaowei Xiao, Bo Li, Edward Suh
- **摘要**：核心洞察：IPI攻击的关键因素不是恶意文本的存在，而是LLM是否意图遵循来自非受信数据的指令。通过"思维干预"策略从推理LLM中提取结构化的预期指令列表，标记或中和与非受信数据重叠的部分。在AgentDojo和Mind2Web上将ASR从100%降至8.5%。

---

## 三、测试 / 基准（Benchmark / Evaluation）

### 1. Can LLMs Separate Instructions From Data? And What Do We Even Mean By That?
- **会议**：ICLR 2025
- **arXiv**：2403.06833
- **作者**：Egor Zverev, Sahar Abdelnabi, Soroush Tabesh, Mario Fritz, Christoph H. Lampert
- **摘要**：首次提出指令-数据分离的形式化度量及其实证变体，并发布SEP数据集。评估多种LLM发现：所有模型均无法实现高分离度；典型缓解措施（提示工程、微调）要么无法实质提升分离度，要么降低模型效用。为IPI问题提供了理论基础。

### 2. InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents
- **会议**：ACL 2024 Findings（2024年发表，为后续工作奠基）
- **arXiv**：2403.02691
- **作者**：Qiusi Zhan, Zhixiang Liang, Zifan Ying, Daniel Kang
- **摘要**：IPI领域最具影响力的基准之一。包含1,054个测试用例，覆盖17种用户工具和62种攻击者工具。将攻击意图分为直接伤害用户和窃取私有数据两类。评估30种LLM agent，发现ReAct-prompted GPT-4有24%的攻击成功率。使用hacking prompt强化后成功率翻倍。

### 3. Security--Fidelity Tradeoffs: The Hidden Cost of Prompt Injection Defense
- **会议**：ICML 2026
- **arXiv**：2606.30783
- **作者**：Mitchell Hermon, Rahul Gupta, Weitong Ruan, Ekraam Sabir, Haohan Wang
- **摘要**：揭示IPI防御中的安全-保真度权衡：防御通过抑制非受信文本来抵御注入攻击，但这会破坏需要保留该文本的任务（如翻译、文档编辑）。提出SecFid基准，使执行注入、作为数据处理注入和忽略注入产生可区分输出。在1,168个样本和48种配置下，没有模型或防御能同时达到两个目标。最高保真度模型达96.5%保真度但仅47.8%安全。

### 4. RedTeamCUA: Realistic Adversarial Testing of Computer-Use Agents in Hybrid Web-OS Environments
- **会议**：ICLR 2026（Oral）
- **arXiv**：2505.21936
- **作者**：（待查）
- **摘要**：提出新颖的混合沙箱框架和RTC-Bench（864个示例），在真实Web-OS混合攻击场景中基准测试CUA（Computer-Use Agent）对IPI的防御能力。Claude 4.5 Sonnet展现出60%的ASR，凸显了迫切的安全需求。

### 5. Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models
- **会议**：KDD 2025
- **arXiv**：2312.14197
- **作者**：Jingwei Yi, Yueqi Xie, Bin Zhu, Emre Kiciman, Guangzhong Sun, Xing Xie, Fangzhao Wu
- **摘要**：提出首个IPI基准BIPIA，评估现有LLM发现普遍存在脆弱性。识别两个关键因素：LLM无法区分信息上下文和可执行指令，以及缺乏避免执行外部内容中指令的感知。提出black-box防御（边界感知）和white-box防御（显式提醒），white-box防御将ASR降至接近零。

### 6. When AUC 0.998 Is Not Enough: A Candidate Evaluation Protocol for Hidden-State Probes of Indirect Prompt Injection in Multimodal Computer-Use Agents
- **会议**：EvalMG '26 @ SIGIR 2026（Workshop）
- **arXiv**：2606.22864
- **作者**：Yanhang Li, Zhichao Fan, Zexin Zhuang
- **摘要**：论证在clean-vs-attack划分上的高探测AUC不足以证明恶意内容检测能力。提出两种诊断检查（配对构造标量基线和同步骤干扰匹配视觉控制），在Qwen2.5-VL-7B上开展案例研究。

---

## 四、综述 / 立场（Survey / Position）

### 1. Agent Security Needs Redefinition through a Holistic Framework
- **会议**：ICML 2026 Position Paper
- **arXiv**：2607.22024
- **作者**：Vincent Siu, Jingxuan He, Kyle Montgomery, Zhun Wang, Chenguang Wang, Dawn Song
- **摘要**：论证agent安全本质上是上下文问题而非内容问题，当前基于内容的框架系统性地错误定义了安全问题。将IPI重新定义为Source Authorization违规。提出四项安全属性（来源授权、任务对齐、动作对齐、数据隔离），并重组现有防御方法。

### 2. Prompt Injections as a Tool for Preserving Identity in GAI Image Descriptions
- **会议**：SOUPS 2025（Poster）
- **arXiv**：2510.16128
- **作者**：Kate Glazko, Jennifer Mankoff
- **摘要**：创新性地将提示注入从恶意攻击向量重新定位为一种赋权工具：内容/图像所有者可利用注入来保留其在AI生成图像描述中的性别和残障身份。这是IPI的正面应用探索。

### 3. In-Context Watermarks for Large Language Models
- **会议**：ICLR 2026
- **arXiv**：2505.16934
- **作者**：（待查）
- **摘要**：提出"上下文水印"（In-Context Watermarking, ICW），仅通过提示工程在LLM生成文本中嵌入水印（无需解码访问）。探讨了将间接提示注入用作隐蔽触发机制，应用于学术同行评审等场景。间接注入在本文中作为工具而非攻击对象。

---

## 五、涉及IPI的跨领域论文

### 1. Systematization of Knowledge: Security and Safety in the Model Context Protocol Ecosystem
- **会议**：预印本（暂无会议信息）
- **arXiv**：2512.08290
- **摘要**：对MCP生态系统的安全与安全风险进行系统化梳理，区分对抗性安全威胁（如IPI、工具投毒）和认知安全危害。分析MCP原语（Resources, Prompts, Tools）的结构性漏洞。

### 2. SoK: The Attack Surface of Agentic AI -- Tools, and Autonomy
- **会议**：预印本（暂无会议信息）
- **arXiv**：2603.22928
- **摘要**：全面梳理agentic AI的攻击面，涵盖提示级注入、知识库投毒、工具/插件利用、多agent涌现威胁等。定义了新的评估指标如不安全动作率（Unsafe Action Rate）和提权距离（Privilege Escalation Distance）。

---

## 六、结合 DSCG TODO 的 2026 顶会优先阅读清单

> 本节按与 DSCG 当前主线的相关性排序：P0 完整仲裁 → P1 Task Contract → P2 provenance/source-to-sink → P4 评测 → P5 论文 framing。会议状态按 2026-09-18 已公开的官方会议页、论文页或 OpenReview 页面核对。

### 1. ACE: A Security Architecture for LLM-Integrated App Systems
- **会议**：NDSS 2026
- **论文页**：[NDSS official page](https://www.ndss-symposium.org/ndss-paper/ace-a-security-architecture-for-llm-integrated-app-systems/)
- **核心方法**：将规划拆成 trusted abstract plan 和 concrete plan，再用静态信息流检查、数据屏障和 capability barrier 约束执行；同时覆盖规划完整性、执行完整性、可用性和隐私风险。
- **为什么优先读**：这是最接近 DSCG “确定性策略层 + 动态能力图 + source-to-sink 约束”主线的系统安全架构，可作为 P0.2、P0.3、P1.2、P1.3 和 P2.2 的主要设计参照。
- **对 DSCG 的直接启发**：把当前 `PermissionSandbox` 升级为“可信抽象计划 → 参数化具体动作 → 唯一 Reference Monitor”三段式执行链；把 `Capability Graph` 的节点约束落到可检查的结构化计划上。

### 2. Security--Fidelity Tradeoffs: The Hidden Cost of Prompt Injection Defense
- **会议**：ICML 2026
- **论文页**：[arXiv:2606.30783](https://arxiv.org/abs/2606.30783)
- **核心方法**：提出 SecFid 基准，区分“执行注入”“把注入当作数据处理”和“直接忽略注入”，专门测量安全防御造成的内容保真度损失。
- **为什么优先读**：DSCG 当前重点记录 ASR 和 Utility，但 P4.2 还要求区分 benign utility、utility under attack、误拒绝和开销。SecFid 提供了比“拦截率越高越好”更严谨的评价视角。
- **对 DSCG 的直接启发**：新增 `fidelity_rate`、`false_refusal_rate`、`source-preserving utility` 和按风险等级加权的效用指标；把“安全裁剪”与“静默丢弃合法数据”分开统计。

### 3. Agent Security Needs Redefinition through a Holistic Framework
- **会议**：ICML 2026 Position Paper
- **论文页**：[arXiv:2607.22024](https://arxiv.org/abs/2607.22024)
- **核心观点**：将 Agent 安全从“动作内容是否有害”重新定义为上下文安全，提出 Source Authorization、Task Alignment、Action Alignment 和 Data Isolation 四个持续检查属性，并把 IPI 视为 Source Authorization 违规。
- **为什么优先读**：它几乎直接对应 TODO 的 P2 provenance、P2.2 source-to-sink、P3 delegation envelope 和 P5.1 研究问题；但它是立场/框架论文，不应替代实证防御论文。
- **对 DSCG 的直接启发**：将 `ActionHistoryTracker` 从动作日志升级为带来源、授权主体、任务契约和数据流的安全账本；论文中明确区分“谁发出的指令”和“指令内容是什么”。

### 4. Attention is All You Need to Defend Against Indirect Prompt Injection Attacks in LLMs (RENNERVATE)
- **会议**：NDSS 2026
- **论文页**：[NDSS official page](https://www.ndss-symposium.org/ndss-paper/attention-is-all-you-need-to-defend-against-indirect-prompt-injection-attacks-in-llms/)
- **核心方法**：利用 attention features 做 token-level IPI 检测和精确 sanitization，并通过两步 attentive pooling 聚合 response token 与 attention head 特征。
- **为什么优先读**：它适合作为 DSCG 的内容检测基线，对应 P2.1/P2.3 和 P4.4 的“无 LLM Security Checker / 无内容检测”消融；同时提醒我们不要把检测器当成唯一安全根。
- **对 DSCG 的直接启发**：在 provenance 策略之前加入可插拔的 token/span 风险告警器，但最终 allow/deny 仍由确定性 Reference Monitor 决定。

### 5. ChatInject: Abusing Chat Templates for Prompt Injection in LLM Agents
- **会议**：ICLR 2026
- **论文页**：[OpenReview paper](https://openreview.net/pdf?id=WVhgFSKniL)
- **核心方法**：把恶意载荷格式化成类似原生 chat template 的角色化、多轮对话结构，并利用模拟历史和上下文说服绕过传统纯文本防御。
- **为什么优先读**：它直接覆盖 TODO P4.3 的结构化注入、多轮攻击、审计器注入和“工具输出拼接 payload”，也是检验“只看文本分类器”是否失效的强攻击基线。
- **对 DSCG 的直接启发**：增加 role-confusion、伪造 assistant/system turn、跨工具多轮拼接和模板变体测试；验证策略层是否只信任真实消息来源，而不是消息表面的 role 字段。

### 6. RedTeamCUA: Realistic Adversarial Testing of Computer-Use Agents in Hybrid Web-OS Environments
- **会议**：ICLR 2026 Oral
- **项目与论文**：[official project page](https://osu-nlp-group.github.io/RedTeamCUA/) · [arXiv:2505.21936](https://arxiv.org/abs/2505.21936)
- **核心方法**：构建结合 Web 复刻环境和 OS 沙箱的混合测试平台，支持自动化注入、场景化攻击配置以及跨 Web/OS 的真实任务链。
- **为什么优先读**：它对应 TODO P4.2 和 P4.3 的“完整多领域、多阶段、自适应攻击”要求，能帮助 DSCG 从 AgentDojo 小子集扩展到更接近生产环境的长链路测试。
- **对 DSCG 的直接启发**：补充跨资源、跨应用、跨会话的攻击轨迹；记录 P50/P95 延迟、确认次数、恢复次数和 source-to-sink 违规，而不只记录最终 ASR。

### 建议阅读顺序

1. **ACE**：先建立可信规划、能力屏障和完整仲裁的系统框架。
2. **Security--Fidelity Tradeoffs**：补齐安全性、保真度和误拒绝的评价方法。
3. **Agent Security Needs Redefinition**：重新定义 DSCG 的威胁模型和论文研究问题。
4. **ChatInject + RedTeamCUA**：扩展自适应攻击与真实环境评测。
5. **RENNERVATE**：作为内容检测器和 sanitization 基线加入消融。

## 分类统计

| 分类 | 数量 | 涉及会议 |
|------|------|----------|
| 攻击（Attack） | 11 | NAACL 2025, USENIX Sec 2025, IEEE S&P 2026, SaTML, ICLR 2026, EMNLP 2025, ICML 2026 Workshop |
| 防御（Defense） | 8 | ICML 2025, NDSS 2026, USENIX Sec 2025, ACL 2025, EMNLP 2025, NDSS 2026 |
| 测试/基准（Benchmark） | 6 | ICLR 2025, ACL 2024 Findings, ICML 2026, ICLR 2026 Oral, KDD 2025, SIGIR 2026 Workshop |
| 综述/立场（Survey/Position） | 3 | ICML 2026, SOUPS 2025, ICLR 2026 |

**覆盖顶会**：ICML, ICLR, USENIX Security, IEEE S&P, NDSS, ACL, EMNLP, NAACL, KDD, SaTML, SOUPS

---

> **说明**：
> 1. 本文档聚焦于在顶会（CCF-A/B 或同等水平）正式接收/发表的论文。部分来自顶会Workshop的论文也一并收录，并标注为Workshop。
> 2. "暂无会议信息"的论文为arXiv预印本，尚未确认会议接收状态。
> 3. 部分2024年投稿、2025年发表的论文（如USENIX Sec 2025, ICLR 2025）也一并纳入，因其正式发表在2025年顶会。
> 4. 检索时间：2026年7月。检索范围：arXiv上indirect prompt injection相关论文（共169篇），从中筛选顶会论文。
