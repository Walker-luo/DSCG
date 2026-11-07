# CLI测试结果按后端归类（2026-10-18）

状态：工程实现与双后端离线验收完成。新CLI测量/预检保存为分类根/后端/运行名称；旧目录不移动，配置匹配时原地续跑。网页发起实验的保存结构保持原样，历史页兼容新旧CLI目录。不调用付费模型或真实benchmark，无速度、防御效果或研究闸门结论。

## 当前布局与兼容

```text
results/partial_benchmark/agentdojo/qwen3.7-flash_baseline/
results/partial_benchmark/agentdyn/qwen3.7-flash_baseline/
results/benchmarks/agentdojo/qwen3.7-flash_baseline/
results/injection_precheck/agentdojo/qwen3.7-flash_injection_screen_01/
```

共享路径模块统一处理full/partial、cohort及screen，模型/运行basename中不再额外拼接后端。未传name保留原pipeline默认名；results-dir始终是分类根，即使其末尾已经是agentdojo也仍追加后端层，不隐式去重。内部攻击/场景/原生JSON、报告、锁及原生缓存层级保持不变，aggregate记录所选实际result_layout。

测量reuse及screen隐式续跑优先已有新路径；只有新路径不存在才查找原model_backend_name目录。新路径存在但绑定不完整或配置冲突时拒绝，不回退旧目录；两者同时存在时用新目录。测量未传reuse时只使用新布局的原生缓存。旧目录选定后，该位置贯穿完整准备、执行、缓存、汇总及cohort报告，不重新拼接成新目录。

原manifest、attempt、cohort及绝对证据路径不移动、不改写。显式cohort/reuse-from可直接提供任一实际布局路径，沿用配置/证据校验。后端身份仍来自安装元数据与运行绑定，不能从目录名补造。Dashboard历史通过已有递归发现与相对路径分组读取新结构，新旧运行与后端分别展示；本次不修改网页启动、结果接口或历史生产逻辑。

用法见[完整指南](../../docs/benchmark.md#结果文件)、[partial指南](../../docs/partial_benchmark.md)、[预检指南](../../docs/injection_precheck.md)。[上一轮顺序执行与轻量校验](./serial_lightweight_20261018.md)的工作区改动保持，未恢复workers、源码扫描或旧兼容映射依赖。

## 离线验证

基准HEAD：`f79e59030d5f12df3594dbe179b23bf3756b6275`。任务开始时工作区已有上一轮未提交改动；本次以当时工作区原字节作为基线，未重置、提交或覆盖上一轮报告/归档/证据。当前交付仍未提交。

| 检查 | 精确命令与结果 |
| --- | --- |
| AgentDojo完整回归 | `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v` → exit0；496项，495通过/1跳过；dojo_verified.log |
| AgentDyn完整回归 | `conda run --no-capture-output -n ipi-agentdyn python -B -u -m unittest discover -s tests -v` → exit0；500项，499通过/1跳过；dyn_final.log。首轮仅原生错误fixture的旧目录glob失配，更新层级后完整重跑通过 |
| Node | `node --test tests/*.cjs` → exit0；41/41；node.log |
| CLI/help/任务导出 | `python workshop/artifacts/20261018_backend_result_layout/verify_interfaces.py` → exit0；10项，无模型创建；interfaces.json |
| 链接、当前改动与原字节 | `python workshop/artifacts/20261018_backend_result_layout/verify_delivery.py` → exit0；见validation.json |
| 空白检查 | `git diff --check` → exit0 |

新路径模块先观察到缺失模块（RED），实现后3项GREEN。新增4项原生布局集成用例和1项历史分析/导出用例；两个后端都执行实际安装的native logger/cache，模型与任务执行使用离线fixture。覆盖full/partial、clean/攻击、legacy缺失任务单次补跑、已完成失败缓存复用、旧预检来源读取、旧screen/cohort证据原字节、旧筛选测量原地续跑、新路径优先、空/冲突新绑定零factory、默认名称及自定义根目录。既有baseline/DSCG、cohort空场景/不补位与Token/错误分母回归同步通过。

只读独立审查未发现可操作问题。审查边界：上一轮未提交代码以本次基线保留，不重新判定；真实模型效果因本次不调用模型而不判断；交付报告/归档/交接由最终自动检查补齐，不以代码审查替代。没有待处理审查项或新增机制。

## 证据与下一步

新产物位于[任务目录](../artifacts/20261018_backend_result_layout/)，修改前字节与路径/哈希见[本次归档](../archive/backend_result_layout_20261018/README.md)。历史报告、原结果、锁及兼容映射保持原样；已存在的plan/report缺失引用单列，不重建旧文件。

无真实模型请求或计分rollout；离线测试计数不是TSR/ASR样本分母。E0、I3、I2及研究路线状态保持。

下一步：服务器同步后照常运行原命令；新实验自动进入后端子目录。已有具备完整绑定的旧实验使用原name加reuse原地恢复；显式cohort/reuse-from保留旧路径即可。新旧同名目录同时存在时优先新目录，不能借删除绑定绕过冲突检查。
