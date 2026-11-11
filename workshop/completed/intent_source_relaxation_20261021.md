# 默认 L2/L3 意图与来源策略（2026-10-21）

用户批准直接更新默认防御为 `three-layer-v3.2`，profile 名仍为 `legacy`，无新增参数或候选。代码基于 `54fa09ce6e127a816ae7f9fe9d9d6e025c98738d`、`workshop` 分支既有未提交工作；本次不提交、不改写用户结果。

## 实现

L2基础提示由1084改为844英文字符：覆盖全部请求步骤、条件及必要后续操作，工具语义不确定时保留多个合理实现。仍仅一次模型调用及原`{"tools":[...]}`协议；宿主不添加同义词配对、不扩展模型返回的授权，纯读取/明确禁止/无关写入边界保留。

L3基础提示由1919改为1050英文字符：允许取得未知事实的准备读取及相关事实的派生参数，检查当前工具实际用途与写入/支付/外发的关键目标、金额和内容。外部命令不能新增任务或权限；风险标签或其他位置存在注入不单独构成违规。严格四字段解析、输入边界、风险元数据、阈值、Monitor及一次性回执/执行票据未放宽。

原有泛化`AUDIT_SCHEMA_INVALID`可能覆盖记录/回执失败的真实协议观察。现在受限`mediation_diagnostics`分别记录原始checker解析、审计记录和路由交接状态；失败分为model_protocol、model_request、audit_record、router_handoff，摘要独立计数。合法审计通过；记录篡改、缺失/绑定变化/重复回执仍拒绝。本次仅复现诊断信息被泛化覆盖，未复现需修复的交接执行缺陷，未添加绕过或推测性兼容补丁。

版本及有效提示继续进入既有运行/缓存/路由身份；旧策略同名reuse在执行前拒绝。冻结cohort轻量读取和原生baseline保持不变。使用新name测试v3.2，不改旧绑定。

旧诊断导出曾从实时默认提示重建历史请求。为保留历史144响应及哈希断言，legacy-v1使用从修改前原文提取的冻结策略；authorized-v2使用当前默认和新请求身份。旧audit bundle摘要仍为`9431ec034c7928d9171da96c3cf4da4fd66e499f7337a2205c21fa2c5e16bec8`，未改旧数据。另对原96条审计和48条授权响应重新离线比较，两份comparison.json与历史输出完全一致，退出0、无新请求。

## 离线验收

证据根目录为 [20261021_intent_source_relaxation](../artifacts/20261021_intent_source_relaxation/)，原文、起始工作树和14,022个results/download文件摘要在before.json及originals/；[交付清单](./intent_source_relaxation_20261021_manifest.json)记录最终日志与文件哈希。

新增8项策略/链路/绑定测试、2项真实AgentDojo套件测试。真实banking用户1/3/6与Slack用户1/3/5通过模拟API响应执行原生工具及效用谓词，progress开关的任务顺序、请求数、Token及结果一致；错误目的地/攻击正文被模拟审计拒绝。该测试验证宿主执行契约，不验证真实模型能否作出这些判决。AgentDyn跳过此AgentDojo专用类，仍运行其原生和公共回归。

最终双环境完整回归退出0：ipi 662项、跳过10；ipi-agentdyn 666项、跳过3，失败/错误均0、网络调用均0。Node 47项通过；两入口帮助在两环境均退出0；339处本地链接/锚点无新增错误，保留5处既有report/report.md失效引用。原文归档摘要一致，14,022个用户结果/导出文件无变化、无新增；git diff --check退出0。精确命令及日志哈希见清单。

```bash
# 分别将ENV替换为ipi、ipi-agentdyn；日志为*_verified.log
conda run --no-capture-output -n ENV env PYTHONPATH=$PWD/workshop/artifacts/20261021_intent_source_relaxation/network_guard python -B workshop/artifacts/20261021_intent_source_relaxation/run_offline_tests.py
# 包装脚本等价于unittest discover -s tests -v，并加网络禁止与计数
/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs
python workshop/artifacts/20261021_intent_source_relaxation/validate_delivery.py
git diff --check
```

测试包装脚本阻止网络连接，spawn继承同样限制；未调用付费模型、未运行真实benchmark。首次包装脚本缺少main保护，spawn重复发现测试，已停止仅本次测试派生进程并修正包装脚本；失败日志保留，最终以`*_verified.log`为准，未修改生产调度器来适配测试。

## 限制与下一步

离线通过仅证明协议、执行链路和身份绑定正确，不证明授权质量、TSR/ASR或模型Token成本改善。后续由用户以新name在相同模型/环境、固定banking/Slack小样本做baseline与v3.2 clean/攻击对照，再决定扩大；本次未授权或执行这些真实请求。历史结果及研究闸门不变。
