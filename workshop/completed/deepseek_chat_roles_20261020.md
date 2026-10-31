# AgentDyn / DeepSeek Chat 角色兼容（2026-10-20）

基点 `0235fbf5b6af22e4fd88c8d02f9d4e25a713c533`。用户新运行 `results/partial_benchmark/agentdyn/deepseek-flash_test/` 的九个攻击×场景组均在 `injection_task_0` GOAL 预检收到 `UnprocessableEntityError`：受限诊断为 HTTP 422、`invalid_request_error`，实际请求角色计数为 `developer:1,user:1`。该目录本任务开始和结束均为 27 文件，路径与文件 SHA256 聚合为 `39d61792e540e2a4211ddecd8688387730ac560731da7f880ae99d16d4c0e342`；没有修改或续跑原目录。前一轮 TypeError 报告的哈希对应用户随后重跑前的旧状态，不能代表这批新结果。

## 原因和变更

本机锁定的 AgentDyn 原生消息序列化会把受信任的 `system` 消息作为 `developer` 发给 `deepseek-flash`，正文是文本块数组；DSCG 先前只对 DashScope 转换该角色。[DeepSeek Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)列出的请求消息角色是 system、user、assistant、tool，不含 developer，且 system 正文要求字符串。这里的 422 没有提供受限的错误参数名，因此无法仅凭服务端状态在角色与正文类型之间作唯一归因；但真实 AgentDyn 序列化、公开接口契约和模拟 HTTP 的拒绝/通过行为一致。

共享 `create_openai_client` 现在对实际 `provider=deepseek` 使用 `deepseek-system-text-v1`：将结构化 `developer` 转成 `system`，并把仅由标准纯文本块组成的 system 正文按原顺序拼接成字符串。不识别的块不静默删除或改写。原 `dashscope-system-v1` 和其他服务的行为不变；源消息对象、文本、消息顺序、工具与其余请求参数保持，不增加 fallback 或额外请求。baseline、DSCG 主/审计、GOAL 预检、screen 与 Dashboard 共用该客户端入口；没有修改 conda 中的 AgentDyn、原生任务或评分。受限 API 诊断在转换后报告实际发送的角色。

`chat_request_adapter` 进入 DeepSeek 公开模型配置，沿既有 run/cohort/router 绑定传播。旧 DeepSeek 运行缺少该身份，配置比较会拒绝静默 `--reuse`；旧 cohort 可能需要重新预检并冻结。保留所有旧结果和证据，真实复测使用新运行名。

## 离线验证与限制

先新增两个失败测试，分别观察到旧 DeepSeek 客户端仍是原客户端、公开配置缺少适配身份；角色转换后，再用严格模拟接口发现原生 system 正文仍是数组，取得第二个失败测试，补上纯文本正文转换。以真实 AgentDyn shopping 工具目录和原生 `OpenAILLM` 序列化测试首轮和工具回合，并用 `httpx.MockTransport` 检查单次请求、其他字段不变、baseline/DSCG/审计共用、旧绑定拒绝及 422 受限诊断。没有发起真实模型请求。

| 检查 | 结果 |
| --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 退出 0，568 tests，skipped 2 |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 退出 0，572 tests，skipped 1 |
| bundled Node `--test tests/*.cjs` | 退出 0，47 pass |
| AgentDyn full/partial `--help` | 均退出 0 |
| `git diff --check` | 退出 0 |

日志与哈希见 [`validation.json`](../artifacts/20261020_deepseek_chat_roles/validation.json)。本轮没有真实 DeepSeek 修复后响应或有效计分样本，不能宣称在线问题已经消失；若新运行仍出现 422，应依据新的实际角色计数和受限 code/param 检查其他请求字段。文档检查中本次新增的链接有效；全局扫描发现 README/AGENTS 中 5 个既有的 `plan.md`、`report/report.md` 失效引用，本次没有改写这些无关历史引用。

下一步：在 AgentDyn 服务器环境中使用全新运行名和 shopping 小范围任务清单先跑一种目标攻击，确认原来失败的 GOAL 预检请求及随后的工具回合；可使用已创建的 `workshop/artifacts/20261020_deepseek_agentdyn_typeerror/shopping_two_goals.json`（须确保服务器也有该文件）。不要复用 `deepseek-flash_test`，通过后再考虑扩大到完整 partial。
