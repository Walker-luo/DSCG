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
