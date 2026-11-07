# 模型与工具配置说明补全（2026-10-13）

用户要求新增一份外部配置/工具参数说明、在README指出，并进一步展开docs/evaluation.md的“模型与工具配置”。本轮已新增 [详细指南](../../docs/model_tool_configuration.md)，扩写 [评测配置节](../../docs/evaluation.md#模型与工具配置)，同步README、docs入口、workshop索引和AGENTS。

HEAD为 `0ec73ea`（精确SHA见evidence.json），分支workshop，开始工作树clean；本轮未提交、未修改runtime/UI/tests/config或本地凭证。当前框架仍three-layer-l2-v2.2，正式route/E0/I3/I2状态保持。

## 补充内容与实现依据

| 内容 | 说明 / 核查依据 |
| --- | --- |
| 输入分工 | 模型连接、注册工具schema/实现、风险目录、模拟任务环境和可选artifact各自作用；标准AgentDojo已提供工具，不要求真实邮箱/银行Key |
| 模型字段 | main/security角色、provider/model_id/base_url/api_key_env/api_key及获取方式；role/path/实际Key优先级和fallback，依据model_config.py |
| 复用与兼容 | 模板自带独立security，空Key不等于移除角色；主模型tools/JSON、审计JSON、当前DeepSeek none设置；离线解析不证明鉴权 |
| 工具参数获取 | 从当前get_suite.tools查看description和parameters.model_json_schema；required/default及未来真实参数值的区别；不调用工具 |
| 风险元数据 | 六字段/枚举/布尔、schema_version及派生字段；load_tool_metadata优先级、factory与runner区别、局部目录覆盖行为，依据tool_metadata.py/defended.py |
| 目录生成 | generate_tool_metadata核对固定AgentDojo0.1.35/v1.2后复制已审核目录；不推理/训练风险，不覆盖已有文件；validate_catalog只读检查 |
| 可选控制 | factory/API、CLI、网页支持域及默认值；routeroff与NoChecker、SDK重试与semantic重审、固定审计/任务源边界，不虚构TOML/CLI选项 |
| 排错 | Key/endpoint/地域/模型ID、工具协议、缺失元数据、目录变更、闭包冲突和委托支持域，保留工具级权限局限 |

外部获取链接按DeepSeek官方认证与Chat Completions、百炼官方Key和首次调用文档核查；只给官方入口与适用说明，不推断测试者账号权限，不执行模型服务请求。官方页与检索结果已在会话核对，根页一次超时未用于支持事实，采用可访问的API参考。

## 验证与边界

cwd：/Users/luo/Desktop/AgentDefence/DSCG。新证据root：workshop/artifacts/20261013_configuration_docs/。

| 命令 | exit / 结果 | 日志 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -p test_model_config.py -v` | 0，7/7 | model_config_tests.log |
| `conda run -n ipi python -m unittest discover -s tests -p test_tool_metadata.py -v` | 0，9/9 | tool_metadata_tests.log |
| `conda run -n ipi python -m experiments.run_partial_benchmark --help` | 0，只读核对参数入口，无模型调用 | partial_help.log |
| `conda run -n ipi python workshop/artifacts/20261013_configuration_docs/check_examples.py` | 0，3 TOML+3 Python示例；69 distinct工具分类校验、角色fallback及Key脱敏通过 | examples_check.json |
| `python workshop/archive/configuration_docs_20261013/validate_docs.py` | 0，当前links/anchors/字段/CLI/state与保护检查 | validation.json |
| `git diff --check` | 0；初次额外EOF空行问题已修正，原问题保留 | diff_check.log、format_issue.txt |

Python示例只使用内存合成配置和占位Key；不读取真实本地凭证、不请求模型、不执行send_email、不生成或替换tools.local.toml。工具参数/模型协议/目录覆盖检查不等于真实模型鉴权、工具能力或安全效用评测。无API调用、新rollouts、新fixtures；docs-only无runtime改变，未扩大运行测试。

6份原文和独立修订链保存在workshop/archive/configuration_docs_20261013/；保护85个runtime/UI/test/config源码hash、29份其他/历史文档hash、169份旧archive文件hash及1341个用户outputs size/mtime。元数据保护不是新内容hash或full历史migration认证，旧报告与结果不改。

精确revision/工作树、命令/exit/分母和artifact SHA256见 [evidence.json](../artifacts/20261013_configuration_docs/evidence.json)。按AGENTS向兄弟research/paper/implementation_status.md追加本轮文档证据，不改technical_route或论文计划。

下一步由测试者获取账号模型信息，先执行离线检查，再用新run名验证少量真实JSON/tool回合与匹配评测；本轮不代替测试者发起付费模型请求。
