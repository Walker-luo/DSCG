# 三层基础框架实施记录（2026-10-10）

当前默认已改为 **three-layer-v1**：L1 构造工具返回的来源隔离视图，L2 复用可信任务授权并把确定性拒绝前置，L3 保留原当前动作审计。用户本次明确要求实施 [基础方案](../3_layer_opt.md)，覆盖此前候选的“仅研究”限制；正式研究路线与闸门未改。L3 学习免审、DRV、参数/对象/数据权限与恢复机制均未实现。

实施基线为 `8f608618171d4ffac8c8ec99d1278302282204fe`，起始源码工作树干净；准备快照中的唯一 untracked 是本次刚创建的原文归档。修改留在工作树，未自动提交、推送或部署。具体文件 hashes、工作树状态与命令见 [证据 JSON](../artifacts/20261010_three_layer_impl/evidence.json)；[实施计划](./three_layer_implementation_plan_20261010.md)和[过程记录](../artifacts/20261010_three_layer_impl/ledger.md)保留。

## 调研与采用的算法边界

修改前核查了 [Spotlighting §III/§V](https://arxiv.org/html/2403.14720v1)、[StruQ](https://arxiv.org/abs/2402.06363)、[Progent](https://arxiv.org/abs/2504.11703) 与 [AgentSpec 作者实现](https://github.com/haoyuwang99/AgentSpec)。这是定向一手资料检查，不能证明没有更好的算法。

L1 采用短来源头尾、系统数据边界与可逆转义。逐词标记/base64 的表示变化没有本项目效用证据；StruQ 依赖专门训练模型，复制其分隔符不能继承其结果。L2 采用现有编译器、最小工具权限与确定性前置，保留排序、温度0、条件任务语义和任务内缓存；不引入动态扩权或新的参数 DSL。来源隔离和权限执行均有直接近邻，未宣称新算法、形式保证或成功率优越性。

## 已实施行为

- **L1**：每次主模型请求从原历史生成独立视图，真实 role/调用 ID 保留；工具名取真实调用与宿主目录。content 和优先发送的非空 error 均封装、转义保留符。原历史正文/error、原生日志和 L3 最近返回窗口不变；重复规划不叠加封装。普通事实不删改，保留符可逆；模型能否正确引用仍待实测。
- **L2**：任务开始编译权限，每个候选批次前检查注册工具、白名单、状态与风险元数据。任何成员失败则整批拒绝；每个原提议仍记账，无审计调用、无工具副作用。混合批次从原有部分执行改为全部阻断，可能降低任务效用。
- **L2 交接**：不可变宿主结果绑定候选、契约、权限与目录；目录包含名称/描述/schema、执行函数与依赖身份/定义。L3 和 Monitor 重新检查当前快照；原地目录修改、权限撤销、候选修改或缺失结果阻断。此处防陈旧交接，不是完整来源跟踪或抗宿主恶意修改保证。
- **L3**：原 public read、sink=none 的免审范围未扩展。其他合法批次保留一次语义审计，默认 retries=0/completion_prompt=false；审计上下文与描述上限保持。原 Monitor 的已授权、无 sink 读取有效 deny 放行例外保留；L2 拒绝不能被例外覆盖，abstain/错误仍阻断。
- **版本与缓存**：默认 factory 名增加版本与实际 L1/L2 标志，避免全量 native 缓存复用旧 V2/其他新消融；显式 --name 仍覆盖默认名，必须使用新名称。partial manifest 增加版本/开关，保留模型、任务、攻击与源码绑定。API 双 false 可建立 V2 对照，尚无新 CLI 或网页独立 L1 开关。
- **同步**：README、AGENTS.md、docs/framework_updates.md、docs/dashboard.md、网页三层架构/开关文案、workshop 状态与索引均已更新。正式结果与下载目录不迁移、不重标历史三层结果。

## 验证命令与结果

命令在 DSCG 根运行，日志/输出统一在 `workshop/artifacts/20261010_three_layer_impl/`。

| 命令 | 退出码 | 结果 / 产物 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -p test_input_isolation.py -v` | RED1 → GREEN0 | 初轮7/7；适配器回归8tests/1failure →8/8，`l1_*`/`review_*_1.log` |
| `conda run -n ipi python -m unittest discover -s tests -p test_authorization_precheck.py -v` | RED1 → GREEN0 | 初轮11tests/13subtest failures →11/11；目录回归12tests/3failures+1error →12/12，`l2_*`/`review_*_2.log` |
| `conda run -n ipi python -m unittest discover -s tests -p test_three_layer_pipeline.py -v` | RED1 → GREEN0 | 工厂集成4/4；缓存回归5tests/1failure →5/5，`integration.log`/`review_*_3.log` |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | **204/204**，`final_regression.log`；早期L1全回归碰到已写待实现L2测试而失败，原日志保留 |
| `node --test tests/test_history*.cjs` | 0 | **21/21**，`node.log` |
| `conda run -n ipi python -m experiments.i3_p0_stress --output workshop/artifacts/20261010_three_layer_impl/i3` | 1（预期） | 24 valid/8 scope/0 tool-boundary violations，仍 **partial**，`i3`/`i3.log` |
| `conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output workshop/artifacts/20261010_three_layer_impl/e0` | 0 | 6synthetic：valid1/tool_error1/infrastructure_error4，`e0`/`e0.log` |
| `conda run -n ipi python workshop/artifacts/20261010_three_layer_impl/diagnose.py` | 初次1 →0 | 初次传跨suite目录被拒后，修正为每suite实际目录；Flask `/` 和 `/history` 200，宿主处理诊断，`diagnostic*.log`/`diagnostic.json` |
| `python workshop/verify_migration.py` | 1 | 完整历史检查仍遇到研究侧已删除兼容路径；见 `migration.log`，未重建旧证据或修补研究侧删除 |
| `python workshop/artifacts/20261010_three_layer_impl/validate.py` | 首次1 →0 | 修正macOS大小写不敏感路径检查后，本次原始归档、链接、语法、修订链、允许变更与结果目录一致性检查，`validation.json` |
| `git diff --check` | 0 | 文本差异检查，`diff_check.log` |

已有 TaskResults 类型重建 warning 仍在日志中；不是本次新失败。I3/E0 是原 P0 离线 fixture 路径，不能作为新 L1/L2 的模型安全评价或通过真实 E0 的证据。本轮新增25个离线测试用例，未新增 benchmark/training/calibration 样本，实际模型 API 调用0。

独立读代码审查发现 **Critical0 / Important3 / Minor0**：有效 error 未封装、默认缓存身份复用、原地目录修改未失效。三个问题均先观察新测试 RED 后修正为 GREEN；无延期项。审查者未再次独立复审修正，最终回归由主实施者执行。原生 baseline、原工具级授权语义和只读审计例外保持。

网页在本机临时 Flask 服务中检查了实际弹窗与滚动：桌面1280×720和窄屏390×844；关闭测试页、恢复视口并停止服务。截图：[桌面](../artifacts/20261010_three_layer_impl/desktop.jpg)、[窄屏](../artifacts/20261010_three_layer_impl/mobile.jpg)、[窄屏下方](../artifacts/20261010_three_layer_impl/mobile_lower.jpg)。未启动评测。初次沙箱禁止本地监听，经授权复核后仅绑定127.0.0.1验证；无部署。

## 开销与仍未验证的部分

本地4个实际工具目录各做30次 L2 check，11–28tools 的单次中位数约0.72–2.15ms；完整路由会重复复核，这不是端到端延迟。10条合成工具返回的一次 L1 视图新增1265–1385字符（含一次规则），不是 Tokens；规则/旧返回封装会随后续请求反复计费。无新增独立模型调用，**不代表总成本下降**，未验证方案的+5%工程目标。

L2 只省掉确定性拒绝的审计；合法私有读取/写入比例高时 L3 仍频繁触发。原 NoSandbox 在新 runtime 上不会安装传入 factory 元数据的行为是继承限制：缺少元数据时L3倾向审计，不能据此计算公开读取免审收益。无 token 实测、ASR/TSR实测、真实payload/终态审计或防御感知攻击测试。

12份原始文件字节保存于 `workshop/archive/three_layer_impl_20261010/originals/`；第四修订 manifest 明确承接前3份历史清单，并把用户此前 partial-reporting 导致的中间索引变化绑定到基线 Git 原文。不改旧SHA、不重建缺失历史结果字节。root results913files、download13files 的名称/大小/mtime与准备快照一致；正式technical_route字节保持。证据和研究回报另行记录当前hash/工作树。

下一步：用新运行名称与匹配模型/任务/攻击运行 V2、L1、L2前置、完整三层四臂小规模消融，独立检查真实终态、合法混合批次损失、引用保真与总/分阶段 Tokens，再决定是否保留 L1 或投入 L3 学习免审。
