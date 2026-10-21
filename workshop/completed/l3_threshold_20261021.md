# L3 直接阈值路由交付（2026-10-21）

本阶段按用户批准的方案实现 `threshold-read-v1`。当前运行不再读取独立校准artifact，默认经验阈值0.70，不宣称风险保证。字符三元组与四信号最大值公式保持原实现；历史校准器、预设、旧结果和原生评分保留。

## 实际行为

- 单个L2已授权、元数据有效、幂等、无sink的internal/personal读取，输入完整、参数有效且分数严格小于阈值时，selective才免审；等于阈值仍审计。secret、带副作用/外发和不适用情况继续既有审计/阻断流程。原公开免审独立。
- CLI full/partial默认shadow；Python/Dashboard默认off。阈值经full、partial、cohort、screen测量和Dashboard API透传，统一验证有限数值[0,1]且拒绝布尔值。非空旧artifact参数在创建模型前报迁移错误。
- Monitor、一次性交接与执行票据保持；策略、资格和阈值纳入运行/缓存及路由凭据绑定。修改阈值使用新name，不复用旧绑定。
- 新shadow使用相同资格和评分，继续真实审计。记录四分项、分数、阈值、would_bypass、实际审计/协议状态、Monitor决定、审计Token及延迟。
- 根级报告按场景/攻击/配置比较0.65、0.70、0.75和配置阈值；缺失轨迹、未知成本保持未知，已知小计单列。审计分歧不是误放率，模拟Token不是实际节省。旧事件不重新评分；旧v1工具报告仍支持显式refresh并输出v2。

```bash
# 同一代码在两个conda环境均可使用，使用新的运行名
python -m experiments.run_benchmark --suites banking slack --name threshold_shadow_new \
  --audit-router-mode shadow --audit-router-threshold 0.70
# 实际免审需显式指定 --audit-router-mode selective
```

## 验证与复核

基点 `0235fbf5b6af22e4fd88c8d02f9d4e25a713c533`，分支workshop，含用户已有暂存/未暂存改动，无新提交。任务前163个源码/文档快照用于区分原有改动；测试针对当前合并工作树，不把原有改动归为本阶段。新证据根目录为 `workshop/artifacts/20261021_l3_threshold/`。

| 命令（仓库根目录） | 退出码 | 验证结果/日志 |
| --- | --- | --- |
| `conda run -n ipi python -B workshop/artifacts/20261021_l3_threshold/run_offline_tests.py` | 0 | 592项，583通过、9跳过；final_verified_ipi.log |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261021_l3_threshold/run_offline_tests.py` | 0 | 596项，595通过、1跳过；final_verified_agentdyn.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 47通过；node.log |
| `python -B workshop/artifacts/20261021_l3_threshold/verify_delivery.py` | 0 | delivery_validation.json：保护12165份原始结果/导出、公式及风险目录 |
| `git diff --check` | 0 | 无空白错误 |

Python验证器与原unittest discover相同，另在导入/运行阶段禁止socket连接并计数；最终两套均network_attempts=0。覆盖阈值边界/非法值、personal读取、secret/sink/多动作/无效输入、授权与票据重放/参数篡改、shadow实际审计、selective交接、入口透传及身份、旧artifact拒绝、历史报告刷新、未知成本和协议失败分布。独立只读复核发现并修复旧报告刷新和缺失轨迹的配置成本/调用数问题；定向RED→GREEN记录均保留。测试计数属于离线工程验证，不是模型成功率。

原始results/download共12165文件逐个SHA256核对，无修改、缺失或新增；字符处理和risk_score函数AST一致，三份受跟踪工具目录字节不变。原L3方案按原字节归档。现有研究闸门保持E0 pending、I3 partial（24 valid/8 scope）、I2 locked。

## 测试隔离事故（必须保留的限制）

最初迁移拒绝RED测试遗漏模型入口隔离，在尚未实现启动拒绝时意外进入配置中的DeepSeek GOAL预检。立即中断；记录聚合为40次API调用计数，其中39失败、1中断/未完成，记录Token为0、无HTTP响应状态。无法据此确认服务端未收到请求或没有计费，不能宣称整个任务无模型请求。没有生成有效评分或效用/安全样本。

仅本次意外新建、任务前不存在的目录移入本轮 `inadvertent_request_run/`，原始用户结果未移动。事故说明见 `inadvertent_request_incident.json`。修正测试采用临时目录和入口mock；随后全部回归加连接硬隔离，最终网络尝试为0。

## 文档与下一步

README、配置/测试/结果/平台指南、`report/frame_tnro.md`、AGENTS、workshop索引和根plan的L3部分同步；保留TSR与AgentDyn事项。[当前方案](../L3_checker_opt.md) · [参数](../../docs/model_tool_configuration.md#l3直接阈值路由) · [结果说明](../../docs/result_files.md)。report目录现有gitignore状态保持，本地框架介绍已修改。

扩大personal读取资格的安全与效用尚未真实测量。下一步使用新name先采集新的shadow数据，再进行同配置clean/攻击对照；手动比较阈值，不自动选取，不承诺TSR、ASR或实际Token收益。
