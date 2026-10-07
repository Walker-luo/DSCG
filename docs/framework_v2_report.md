# 两层框架 V2 实施记录

本轮依据 research 的 `framework_optimization_v2_proposal_20261007.md` 实施工程修正。授权负责可用工具，动作审计负责当前调用与任务是否一致；Monitor/ticket 沿用。没有实现第三层、对象/数据权限或新恢复机制。

## 阶段一：授权稳定性与可诊断失败

授权 API 显式 temperature=0，工具目录按名称排序、说明去除首尾空白。通用提示覆盖用户已经请求的条件动作，区分更新已有支付与新增付款。外部反馈仍不能触发补授权。温度为零不承诺 provider 完全确定。

失败码 `AUTH_EMPTY_REQUEST`、`AUTH_API_ERROR`、`AUTH_NO_CHOICE`、`AUTH_REFUSED`、`AUTH_INCOMPLETE`、`AUTH_INVALID_JSON`、`AUTH_INVALID_SCHEMA`、`AUTH_UNKNOWN_TOOL`、`AUTH_INTERNAL_ERROR` 随现有 trace 持久化，原始 provider 错误不入报告。所有异常继续清空权限。

- RED：`/opt/miniconda3/envs/ipi/bin/python -m unittest discover -s tests -p test_authorization_defaults.py -v`，退出 1；三个测试中的十个缺失行为断言失败。
- GREEN：`/opt/miniconda3/envs/ipi/bin/python -m unittest discover -s tests -v`，退出 0，161/161。
- 实际模型检查：`/opt/miniconda3/envs/ipi/bin/python examples/results/framework_optimization/20261007_v2_implementation/authorization_probe.py`。四种自编合成请求 × 三次；只发通用请求与公开工具说明，不执行工具，不使用真实账户或私有任务数据。

原始日志、探针源码及输出保存在 `examples/results/framework_optimization/20261007_v2_implementation/`。受限网络第一次退出 2、12/12 API 错误，另存 `_restricted` 文件，不计模型表现。正常网络退出 0，12/12 有效、0 API 错误、0 缺必要工具、0 额外写工具；各请求三次选择相同，总计 3,558 Token。结果见 `authorization_probe.json`。以上检查不证明真实 rent/booking 任务效用或防御提升。

## 后续验收

阶段二为审计添加最近四条当前任务工具返回（每条最多 2,048 字符），保持单次审计。工具返回是不可信上下文，不能修改授权。阶段三使用同任务 clean 和攻击对照决定架构；正式研究门槛仍需 E0 真实送达/终态审计与重复实验。

## 阶段二：有界审计上下文与内置默认值

审计实际 API 请求现在携带最后一个用户消息之后的最近四条工具返回，每条最多 2,048 字符，附工具名、call ID、错误及截断标志。均标为 untrusted：它们可以支持 Bob 链接等事实判断，不能补授权、替换参数或成为新任务。窗口截断与 action ledger 截断分别记录，不因为有界窗口本身必然 abstain；缺判断所需证据仍 abstain。固定窗口可能不足以覆盖长任务，不是来源图或对象权限。完整模式 sidecar 包含该上下文；summary 仍只保存决策与哈希。

无本地工具配置时使用仓库自带目录，优先级为显式路径 > DSCG_TOOL_METADATA > 现有 tools.local.toml > tools.agentdojo-v1.2.toml。显式缺文件继续报错；未知分类仍 critical。partial 默认 ID 与旧冻结清单逐项一致，不需要外部导入清单或新参数。既有模型配置与凭据不改动。

- RED：`/opt/miniconda3/envs/ipi/bin/python -m unittest discover -s tests -p test_audit_tool_context.py -v`，退出 1，6 个测试中 5 个失败。
- GREEN：`/opt/miniconda3/envs/ipi/bin/python -m unittest discover -s tests -v`，退出 0，167/167。
- 语义对照：`/opt/miniconda3/envs/ipi/bin/python examples/results/framework_optimization/20261007_v2_implementation/audit_probe.py`，退出 0，8 种合成合法/攻击/证据不足情形 × 两组。相同新审计提示，仅工具上下文不同：无上下文 4/8 符合预设判断，有上下文 8/8，0 错误、11,019 Token。涵盖直接 URL、Bob 文章、文章新增攻击 URL、用户明确要求的多跳、无关链接、读取已有支付、窗口保留足够证据及缺证据。没有执行工具或跑主模型，不能推导恢复历史七个 Slack 配对或 benchmark 防御收益。
- I3：`/opt/miniconda3/envs/ipi/bin/python -m experiments.i3_p0_stress --output examples/results/framework_optimization/20261007_v2_implementation/i3`，退出 1，24/24 有效、8 scope violations、0 tool boundary violations，仍 partial。
- E0：`/opt/miniconda3/envs/ipi/bin/python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output examples/results/framework_optimization/20261007_v2_implementation/e0`，退出 0；6 个合成 self-check，valid1/tool_error1/infrastructure_error4，不代表实际 harness 已过门槛。

阶段三先运行三个同期 clean 对照，再依据有效攻击样本决定层数。完整典型攻击与三次重复仍需新名称运行，不能用合成结果代替。
