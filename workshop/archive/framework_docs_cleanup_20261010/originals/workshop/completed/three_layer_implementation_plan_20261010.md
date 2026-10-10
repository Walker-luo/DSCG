# 三层基础框架实施计划

> 使用 writing-plans 与 executing-plans 流程，在当前会话原生实施；完成后做一次独立代码审查。用户已明确要求按现有书面方案修改，继续执行，不增加重复批准步骤。

**Goal:** 实施 `3_layer_opt.md` 的零独立模型调用 L1、确定性 L2 前置检查和原 L3 单次审计，同步平台与文档。
**Architecture:** L1 只构造主模型视图，原工具消息保留给日志和审计；L2 使用原沙箱/宿主目录整体拒绝非法批次，Monitor 执行时重新检查；L3 保持公开读免审范围与读取 deny 例外。
**Tech Stack:** Python / AgentDojo / Flask / Bootstrap；不加依赖、训练模型或请求模型 API。
**Spec:** [三层方案](../3_layer_opt.md)。L3 学习免审不在本次实施范围。

## 调研结论与取舍

| 层 | 已核查主来源 | 采用 / 未采用 |
| --- | --- | --- |
| L1 | [Spotlighting §III、§V](https://arxiv.org/html/2403.14720v1) | 采用短来源提示、系统数据边界、可逆保留符转义。逐词标记/base64 会改变表示并增加输入处理；没有本项目效用与成本证据，不默认叠加 |
| L1 | [StruQ 官方论文](https://arxiv.org/abs/2402.06363) | 结构化前端加专门训练模型；当前黑盒部署不能通过复制分隔符继承训练模型效果 |
| L2 | [Progent 官方论文](https://arxiv.org/abs/2504.11703) | 可编程最小权限与确定性执行是近邻；复用现有工具级编译/沙箱，将拒绝前置。不引入动态扩权或新的参数策略 DSL |
| L2 | [AgentSpec 作者实现](https://github.com/haoyuwang99/AgentSpec) | 运行时规则机制可借鉴分离判断/执行；本轮不新增宿主对象 oracle 或猜测参数授权 |

以上是限定范围的一手资料调研，不是完整综述或“最佳算法”结论。不继承来源报告的成功率/安全保证。

## Global Constraints

- 用户本次显式选择基础三层工程实施，覆盖此前 workshop 候选“未实施”的限制；正式研究路线与 E0/I3/I2 闸门不改，不宣称论文机制获批。
- 原文、结果和凭证保留；新输出只进 `workshop/artifacts/20261010_three_layer_impl/`。不创建小写 Agents.md，更新已有 AGENTS.md。
- L1 不删除、摘要、截断正文，不将封装后的正文写回原 history。规则每个实际主模型请求只一份；每条结果只一个壳。
- L2 拒绝非法混合批次全部成员，记录每个真实候选。Monitor 再检查当前授权/元数据；模型意见不补权限。
- 原 L3 上下文与公开 read bypass 不扩展。默认 retries=0、completion_prompt=false；不实现 CSA、DRV、对象/数据 provenance 或恢复机制。
- 保留本次开始时 `8f608618171d4ffac8c8ec99d1278302282204fe` 的结果报告功能。基线仍原生 AgentDojo。

## Review Focus

- 正文伪造框架标记、角色或工具名：只作为可逆转义数据，元数据由真实调用/注册目录决定。
- 同一历史多轮规划和工具错误：原消息不污染、规则/封装不累加、真实调用 ID/error 不变。
- 混合批次非法调用在任意位置：所有候选登记且无工具副作用、无审计调用。
- L2 之后任务/目录/候选改变：Monitor 不接收旧前置结果，不能靠只读 deny 例外发票据。
- 基线/消融/缓存：实际防御模式写入配置/manifest；原生 baseline 无新增 L1/L2 元数据。

## Task 1：L1 主模型视图

Files: 新增 `dscg/input_isolation.py` 与 `tests/test_input_isolation.py`；修改 `OurFrameExecutor`。
接口：`build_isolated_view(messages, runtime) -> (view, numeric_stats)`；原 history、role、tool_call_id、tool_call、error 不变。
- [x] 先写行为测试：原输入不变、工具名来自实际调用、普通事实保真、保留标记转义、系统规则单份、重复请求不嵌套、禁用时原视图。
- [x] 跑新测试，记录 RED；实现最小视图及主模型接入，记录 GREEN 与完整回归。
- [x] 记录累计表示字符数；实际 Tokens 仍来自现有 tracker，不将字符数称 Token。

## Task 2：L2 前置与 L3/Monitor 路由

Files: 修改 `defended.py`；新增 `tests/test_authorization_precheck.py`。
接口：`ToolAuthorizationPrecheck(sandbox).check(calls,runtime)` 返回不可变、绑定批次/策略/目录的宿主结果；其 query 位于 checker 前；checker 免掉确定性拒绝的模型请求；Monitor 消费并复核。
- [x] 先写无副作用/无模型调用、混合整批拒绝、无元数据、陈旧状态、公开免审/私有审计的测试并观察 RED。
- [x] 实施整体拒绝与完整候选记账，保持既有读取 deny 例外；记录 GREEN 与完整回归。
- [x] factory 默认启用；可用 API 关闭 L1/L2 作匹配对照。NoSandbox 不启用 L2；两旧开关全关时不残留 L1。
- [x] 新框架配置写入 trace 与 partial manifest，防止旧运行目录接受新策略。

## Task 3：展示、文档与证据

Files: README、AGENTS、docs/framework_updates、docs/dashboard、dashboard/templates/index.html、workshop 索引/方案状态/迁移 helper。
- [x] 更新三层实际执行顺序与开销边界；L1 提示不保证事实真实，L2 为工具级，L3 当前 read-deny 例外准确。
- [x] Flask 本地页面验证、既有 Node 检查与适当窄屏检查；不启动模型或正式 benchmark。
- [x] 完整离线回归、I3/E0 既有 fixture、新路由诊断与输入增量检查；日志全部进本次 artifact。
- [x] 独立代码审查后修正有实质影响的问题；保留日期化 hash，通过新增修订 manifest 而非改旧预期维护 helper。
- [x] 报告精确命令/退出码/源码 hashes/样本分母/限制，按 AGENTS 要求追加研究实施状态。

不自动提交、推送或部署；工作树与源码 hashes 绑定本次验证。下一步为用户选择模型预算后跑匹配三层消融；本轮离线结果不能证明实际 ASR/TSR/Token 改善。

独立审查发现并修正3个 Important 问题：有效 error 封装、默认缓存身份、原地目录变化失效；对应回归先 RED 后 GREEN。实际验证与限制见 [阶段报告](./three_layer_implementation_20261010.md)。
