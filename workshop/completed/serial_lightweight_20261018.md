# 顺序测试与轻量配置校验（2026-10-18）

状态：工程实施与双后端离线验收完成；无付费模型请求、真实benchmark或速度/防御收益结论。此报告替代[Qwen并发阶段](./qwen_parallel_20261018.md)的执行与校验规则，保留该阶段模型默认值及全部历史证据。

## 当前行为

- full、partial、cohort按攻击/场景顺序执行；删除workers CLI/API、spawn调度和进程专属fixture。保留原生目标预检、任务顺序、评分、缓存、错误分母、Token及汇总口径。
- 准备阶段静默核对全部任务与绑定，不创建pipeline/模型客户端。纯配置描述与真正factory共享命名、路由配置计算；每组实际执行时创建独立pipeline/tracker。启动打印一次模型、后端、攻击、场景、结果目录及缓存策略，每组打印计数和开始/结束。
- 后端只检查实际导入路径、distribution来源/版本、固定revision及场景范围；不遍历后端文件或扫描工程源码哈希。身份为verification_mode=metadata_only、runtime_variant=unverified。Git/Python/包版本只作参考记录，Git信息每进程读取一次。
- 新旧运行按后端、模型公开请求配置、完整任务ID、攻击/场景、cohort、工具元数据内容及有效防御配置匹配。源码哈希、commit、Python补丁版本及旧并发策略不阻止续跑；缺少必要身份、跨后端或配置变化仍拒绝。工具路径是来源信息，工具内容完整比较。
- 保留cohort摘要、原始轨迹、引用manifest哈希和GOAL/规则/原生utility一致性检查；取消预检脚本/任务实现源码哈希门槛。旧manifest、attempt与cohort不改写；测量和未完成screen在覆盖汇总前保存快照，configuration_only记录明确source_equivalence_verified=false。
- 结果锁、失败组继续执行及中断退出130保留；中断后使用原name加reuse。原生已接受的成功/失败/错误缓存不新增自动重试，不恢复单个工具动作。

命令与限制见[完整指南](../../docs/benchmark.md#顺序执行与准备信息)、[partial指南](../../docs/partial_benchmark.md#顺序运行)、[预检指南](../../docs/injection_precheck.md)。源码校验减少不等于模型请求减少；shadow仍保留L3审计。防御内部算法/profile/receipt摘要不属于本次移除的工程文件校验。

## 验证

基础revision：`f79e59030d5f12df3594dbe179b23bf3756b6275`；初始工作区干净，交付为未提交工作区改动。完整差异与原始文件清单保存在[任务产物](../artifacts/20261018_serial_lightweight/)，[归档索引](../archive/serial_lightweight_20261018/README.md)保留修改前原始字节及哈希。

| 检查 | 精确命令 / 结果 |
| --- | --- |
| AgentDojo完整离线回归 | `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v` → exit0，488项，487通过/1跳过；dojo_verified_final.log |
| AgentDyn完整离线回归 | `conda run --no-capture-output -n ipi-agentdyn python -B -u -m unittest discover -s tests -v` → exit0，492项，491通过/1跳过；dyn_verified_final.log |
| Node | `node --test tests/*.cjs` → exit0，41/41；node.log |
| CLI/导出 | `python workshop/artifacts/20261018_serial_lightweight/verify_interfaces.py` → exit0，10项；六项help、两后端各full/partial导出，未创建模型；interfaces.json |
| 当前链接、归档、受保护文件 | `python workshop/artifacts/20261018_serial_lightweight/verify_delivery.py`；结果见validation.json，既有缺失链接单列 |
| 空白检查 | `git diff --check` → exit0 |

离线范围包括full全部ID、partial前三个注册任务、clean、cohort空场景/不补位、baseline/DSCG、原生预检及任务级缓存、失败缓存复用、旧哈希绑定续跑/原绑定不改写、后续分组冲突时零pipeline创建、中断恢复、结果锁、真实原生错误分母及成本保留。

新metadata-only/source兼容用例先观察到源码扫描和旧哈希拒绝（RED），随后通过；工具路径内容比较也先RED再GREEN。最终独立审查发现两项P2：递归来源字段排除误丢工具内容、未完成screen缺少汇总快照/结构化校验标识。分别由test_effective_nested_source_fields_and_tool_names_are_not_provenance与test_pending_screen_preserves_previous_aggregates_and_configuration_only_record复现RED，修复后两套完整回归GREEN。没有待处理审查项。首位审查模型额度不足，由可用审查模型完成只读复核。

## 解释限制与下一步

运行时不再认证源码内容、任务实现或环境数据逐字节一致；configuration_only不能证明源码等价。历史哈希、锁、兼容映射和原结果保留，不扩充旧映射或伪造缺失身份。模型服务修订及实际加速没有测量；无真实计分样本，offline用例数不是TSR/ASR分母。不改变研究闸门、L1/L2/L3防御默认或原生评分。

下一步：服务器同步代码，去掉旧命令中的workers；同模型/配置/后端可用原name加reuse继续。若切换模型、任务、攻击或防御设置，使用新name；首次运行先选择小范围clean确认服务表现。
