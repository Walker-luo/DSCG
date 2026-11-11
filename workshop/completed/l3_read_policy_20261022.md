# DSCG_v3.3：L3读取路由与当前动作审计

本次按用户授权更新共享默认实现，内部身份为`DSCG_v3.3`。full、partial、cohort及factory采用同一版本；没有新增参数或模型请求。历史实验DSCG_v3.2、引擎three-layer-v3.3及所有原始结果保持原样。baseline原生执行与冻结cohort轻量消费不变。本文的工程检查不证明TSR/ASR改善。

## 实现与边界

- L2仍一次调用，完整原生定义和步骤授权不变。read-purpose-v2将已授权、schema有效、public/internal、幂等无sink读取及全读批次列为候选；个人/秘密、混合读写及效果性操作仍审计。
- 当前请求/描述/参数完整性继续检查；历史工具错误、截断及旧参数损失不再迫使新读取审计。词法分数/阈值仍记录和绑定，但不控制候选，不给新规则生成阈值扫描；旧报告保留旧语义。
- 外部网页只有可信用户原文URL的严格窄例外：URL-only、HTTP(S)/www、保守字母TLD域名，排除IP（含非标准数字写法）、内网后缀、查询、fragment、凭证、端口、编码或可疑凭证路径。风险标签不变；不验证DNS、重定向、真实性或对象权限。来源中的新URL和AgentDyn副作用handler不能套用。
- 默认L3只审当前动作，加入真实effect和原生参数schema；允许先获取未知事实，再验证实际写入/支付/外发的目标和内容。不加入义务ledger或把模型步骤当授权真值。超长violation代码（原文/规范化后>96）明确协议失败并关闭，不修补参数或响应。
- Monitor、回执及执行票据保留，签名绑定整批调用；新增第二条读取参数篡改测试，整批不得执行。历史legacy-v1离线诊断维持旧输入、提示和解析，只对冻结响应回放，不作为运行时宽松开关。

## Shadow与复测

CLI仍shadow、API off。shadow真正审计并执行原Monitor决定；selective才应用新增免审。报告区分原公开免审、候选、实际免审，记录候选实际审计/Monitor交叉与协议、请求、记录失败。未知成本/历史缺失保持未知；模拟节省不是实际节省，分歧不是安全标签。

```bash
python -m experiments.run_benchmark --suites banking slack \
  --model-config config/models.local.toml --audit-router-mode shadow \
  --progress --name DSCG_v3.3_shadow_01
```

小批量改用`experiments.run_partial_benchmark`和新name。若需cohort，附现有实际路径；名单不重预检，但不能复用旧防御身份的测量缓存。当前未执行以上真实命令。后续先固定banking/Slack样本检查路由覆盖、阻断，再做同轮baseline/shadow/selective对照，不自动开展全量。

## 验证记录

最终检查：

| 检查 | 结果 |
| --- | --- |
| AgentDojo ipi完整Python离线回归 | 684项，跳过10，失败/错误/网络尝试0，124.335秒 |
| AgentDyn ipi-agentdyn完整Python离线回归 | 688项，跳过3，失败/错误/网络尝试0，111.425秒 |
| Node | 49项通过 |
| 两入口×两环境help | 4次退出0；无新参数，阈值帮助改为诊断用途 |
| 当前文档/章节链接 | 377条，无新增失效；5条已有report/report.md引用缺失保留 |
| 原结果/下载保护 | 14,951个文件哈希相同、无新增文件 |
| 归档和git diff --check | 归档一致，退出0 |

网络guard禁止真实请求，本次无付费模型调用。真实原生banking/Slack套件配合模拟API响应检查正常多步骤和错误外发；并行、cohort、缓存、JSON隔离等既有回归全部纳入。默认短提示1052英文字符、121空白词，满足1200字符上限；不是模型Token测量。

独立只读复核发现两项Important：非标准数字IP误入网页候选、请求失败误计模型协议失败，均有失败测试后修复。历史截断的旧测试预期同步更新；无待延后Minor。审阅未判断真实模型质量/攻击安全、DNS或重定向和整体效用，以上均保留未验证状态。

工程证据：[目录](../artifacts/20261022_l3_read_policy/)、[验证](../artifacts/20261022_l3_read_policy/delivery_validation.json)、[决策记录](../artifacts/20261022_l3_read_policy/ledger.md)。未提交；保留原有未提交文档分析。研究闸门E0 pending、I3 partial、I2 locked不变。
