# 冻结 cohort 的无效请求适配变更兼容

本次修复旧 AgentDojo/DashScope cohort 因缺少新增 `chat_request_adapter` 标记而被拒绝的问题。名单与模型请求设置绑定仍有效；仅当已验证新增适配在预检消息上不改变请求时，继续读取原名单。此修复不重新预检、不修改 cohort、轨迹、原生评分或请求适配器。

## 原因与修复范围

原校验直接比较整个 `main_model` 字典。旧记录没有 `chat_request_adapter`，当前公共配置包含 `dashscope-system-v1`，仅新增标记也被视作模型变化。对当前 AgentDojo 系统消息序列化输出仍为system的路径，DashScope适配器没有实际转换，因此要求重新筛选过于严格。

共享的冻结名单读取增加一个明确兼容分支：

1. 只接受AgentDojo、相同DashScope provider、旧记录缺字段而当前为已知`dashscope-system-v1`；其余模型/请求配置、任务、GOAL、规则与后端仍须匹配。
2. 完整验证原cohort摘要、有效尝试轨迹摘要、任务/GOAL及原生判定，再检查原始消息无developer、当前原生system序列化仍为system。读取原生转换函数，不遍历或哈希安装源码，不创建客户端。
3. 明确发出no-op兼容提示。新测量的`screened_cohort.json`记录`request_adapter_compatibility`，同时保留原cohort内容；当前实际模型/适配身份仍进入测量绑定。

未知适配版本、需要真实角色转换的路径、模型/provider/endpoint/thinking变化、证据损坏仍拒绝。该分支不放宽旧攻击缓存或未完成screen的绑定，不声称历史源码等价，也不扩展到DeepSeek/AgentDyn。

## 验证

任务开始时工作树干净；基线commit及最终文件摘要见[验证清单](../artifacts/20261021_cohort_adapter_noop/validation.json)。新产物统一位于`workshop/artifacts/20261021_cohort_adapter_noop/`。

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `conda run -n ipi python -B -m unittest discover -s tests -p test_cohort_adapter_compatibility.py -v` | 1→0 | RED暴露旧cohort拒绝；GREEN六项：无改写、实际转换拒绝、未知/模型设置拒绝、篡改拒绝、full/partial透传和兼容记录 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 598项，跳过9；ipi.log |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 0 | 602项，跳过1；agentdyn.log |
| `PYTHONPATH=. conda run -n ipi python -B workshop/artifacts/20261021_cohort_adapter_noop/check_local_evidence.py` | 0 | 两份本地cohort副本各44条有效尝试逐条核对原摘要/GOAL/结果及当前转换no-op；local_evidence.json |
| 文档链接与`git diff --check` | 0 | 无失效本地链接或空白错误 |

本地复制目录保留的原绝对证据路径不可访问；核查脚本只读相同目录结构下的复制字节，未修补路径。服务器完整运行仍要求原证据路径可访问、当前原生转换通过。此验证不代表服务器端benchmark已成功。

原AgentDojo预检目录274文件逐哈希不变。付费模型调用0、真实新rollout0；无防御效果或模型行为稳定性结论。未修改默认路由、阈值、工具与评分。本次改动限共享名单读取、六项测试和预检文档；无新增CLI选项。

下一步：服务器同步本次代码后，使用原cohort和原benchmark命令；符合上述条件时无需再运行screen。
