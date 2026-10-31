# AgentDojo／AgentDyn 双基准自动切换交付（2026-10-18）

工程实现与离线验收完成。同一份代码只需切换conda环境：`ipi`选择AgentDojo，`ipi-agentdyn`选择AgentDyn；无需更换代码、基准参数或默认工具目录参数。保留上次尚未提交的AgentDyn改动，没有重置分支、提交、推送或修改既有环境。

本轮只支持两套新实验和历史查看；不迁移交付前缓存/cohort，不扩展历史源码兼容映射。没有付费模型请求或真实模型效果实验，不宣称TSR／ASR或攻击强度收益。

## 默认目录与范围

| 环境 / 后端 | 场景 | full clean | 注入目标总数 | 每目标型攻击组合 | typical三攻击 | partial clean / typical |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ipi / AgentDojo0.1.35 v1.2 | workspace、travel、banking、slack | 97 | 35 | 949 | 2847 | 12 / 108 |
| ipi-agentdyn / AgentDyn v1.2 | shopping、github、dailylife | 60 | 28 | 560 | 1680 | 9 / 81 |

任务数来自实际注册表，不是API请求数、有效标签分母或实验成绩。full使用所选场景全部任务；partial每场景仍取注册顺序前3个用户×前3个目标；GOAL预检另计。用户命令见 [完整指南](../../docs/benchmark.md)、[partial指南](../../docs/partial_benchmark.md)和[预检指南](../../docs/injection_precheck.md)。

## 实现与身份

- [共享目录](../../dscg/benchmark_catalog.py)在执行时获取验证过的冻结后端描述，所有入口按实际安装来源/字节选择。移除AgentDyn专属导入快照，不信任conda名称或共同的agentdojo0.1.35版本号。CLI帮助与未知后端历史浏览仍可用；执行在模型构造前拒绝未知来源、提交、增删或修改源码。
- [AgentDojo锁](../../config/agentdojo.lock.json)绑定官方PyPI0.1.35 wheel，SHA256为`364bea4219716b716bf639f504d195943f7f6a5535d312ca41d7098704a2affd`，以及112个源码/数据文件。revision用`pypi:agentdojo==0.1.35`，不虚构Git提交。
- 本机旧ipi仅openai_llm.py一处不同于官方包：system消息从developer角色改为system。此确切文件哈希作为`reviewed-local-system-role-v1`变体列入锁定，实际实现身份与official-release不同；没有修改该文件。官方wheel解包后也通过完整字节校验，任务/目录哈希与本机变体相同，整体实现哈希不同，不能据此自动配对。其他未知补丁不接受。
- AgentDyn保持原提交`5353cf7615b135cace8d07c8f12dac53a16b6db3`和1374文件锁。两套锁、发行/提交、package_version、runtime_variant、source_kind及任务/环境/攻击/工具组件身份进入新运行、名单、summary与导出。
- 风险配置按显式参数→环境覆盖→基准专用local→可归属通用local→对应内置目录选择。当前tools.local与AgentDojo审核目录语义相同，在AgentDyn提示跳过并自动用其内置目录，不覆写文件、不合并分类。未知自定义通用目录报错；显式/专用local可用于自定义宿主。生成器默认输出基准专用local，并保护两份内置目录和通用文件。选择的来源、路径和提示在CLI、绑定与网页可见。
- 新CLI/screen目录为`<model>_<benchmark_id>_<name>`，网页ID包含实际后端。缓存和cohort要求当前后端/源码/配置身份精确一致。旧数据只读，不补造身份、跨基准配对或合并分母；历史导出保留发行和runtimevariant字段。
- 网页场景、攻击、数量、标签及工具路径随进程环境变化。切换终端环境不会改变旧服务，须重启；并行运行可在两个环境用不同PORT启动。模型、三层防御、路由/重试默认不变，没有新增投影、免审、handler/参数/对象授权。
- 两套基准均保留原生工具循环与评分。原始错误/标签不改；派生效用/安全指标排除运行错误，计划/总量、有效分母、错误和Token分别保留。原生接受的错误缓存不自动重试。

## 验证

代码起始revision：`2a2b17ce1275b9c8372814935989df5e6d9161e7`；起始已有AgentDyn工程未提交改动。本轮沿用workshop分支，交付仍为未提交工作树。起始文件/结果保护清单和每个阶段日志存于 [本次产物目录](../artifacts/20261018_dual_benchmark/)，当前文件哈希见[交付清单](./dual_benchmark_20261018_manifest.json)。

| 实际命令 | 结果 | 任务产物目录内文件 |
| --- | --- | --- |
| `conda run -n ipi python -m pip download --no-deps --only-binary=:all: --dest workshop/artifacts/20261018_dual_benchmark/wheels agentdojo==0.1.35` | 网络受限首次失败；允许下载重试退出0，无安装动作 | wheel_download.log、wheel_download_retry.log、wheels/ |
| `conda run -n ipi python -B -m dscg.benchmark_catalog` | 0，97用户/35目标及reviewed-local-system-role-v1 | agentdojo_catalog_final.json |
| `conda run -n ipi-agentdyn python -B -m dscg.benchmark_catalog` | 0，60用户/28目标及pinned-git | agentdyn_catalog_final.json |
| `conda run -n ipi python -B -m experiments.run_benchmark --write-task-manifest workshop/artifacts/20261018_dual_benchmark/full_dojo.json` | 0，97/35 | full_dojo.json、full_dojo.log |
| `conda run -n ipi-agentdyn python -B -m experiments.run_benchmark --write-task-manifest workshop/artifacts/20261018_dual_benchmark/full_dyn.json` | 0，60/28 | full_dyn.json、full_dyn.log |
| `conda run -n ipi python -B -m experiments.run_partial_benchmark --write-task-manifest workshop/artifacts/20261018_dual_benchmark/partial_dojo.json` | 0，12/12前缀 | partial_dojo.json、partial_dojo.log |
| `conda run -n ipi-agentdyn python -B -m experiments.run_partial_benchmark --write-task-manifest workshop/artifacts/20261018_dual_benchmark/partial_dyn.json` | 0，9/9前缀 | partial_dyn.json、partial_dyn.log |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0，运行466项，OK；另明确跳过另一后端专属native类 | python_dojo_final.log |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 0，运行470项，OK；另明确跳过另一后端专属native类 | python_dyn_final.log |
| `node --test tests/*.cjs` | 0，41/41 | node_final.log |
| `conda run -n ipi python -B workshop/artifacts/20261018_dual_benchmark/canonical_release_probe.py` | 0，官方wheel和本机变体分别校验、不同实现身份 | canonical_release_probe_final.json |
| `python -B workshop/artifacts/20261018_dual_benchmark/verify_delivery.py` | 0，保护、目录与文档检查 | delivery_checks.json |
| `git diff --check` | 0 | diff_check.log |

两套完整回归各覆盖后端目录、错误来源、授权/工具目录、clean/full/partial/native baseline/DSCG、typical/explicit/all、预检/cohort、新绑定续跑、配置冲突、错误分母和Token；定向runner150项/环境、网页Python47项/环境和metadata64项跨环境检查另有阶段日志，不与全套重复累计。

真实原生检查采用确定性脚本和宿主写定的审计结果，无模型请求。AgentDojo覆盖四场景各1个正常任务、1个目标正例及空操作负例、未授权真实工具阻断（3个测试方法，四场景循环）。AgentDyn保留7个方法，覆盖三场景正常任务、直接目标正/负状态、注入邮件返回、实际工具反馈OTP、网页点击下载副作用、拒绝/abstain/无效元数据、CLI9个及网页1个原生捕获错误的派生排除。直接目标脚本只验证管线和oracle接线，不是间接攻击效果。

网页使用实际两环境Flask/API探针和Node检查；没有图形浏览器人工复验，也没有付费服务鉴权或真实模型调用。切换环境后的有效目录和namespace、错误后端拒绝/历史可读均有记录。完整回归仅按后端跳过不适用native类，不跳过失败场景或以改标准答案追分。

## 独立审查、保护和限制

独立新上下文代码审查没有Critical或Important缺陷；定向catalog、runner和两套native检查通过。唯一Minor暂缓：失败汇总逐例重复核验后端身份。实测AgentDyn暖调用约0.113秒，若1680例均生成失败记录，额外约189秒；不改变分数、模型调用或Token。后续可在单次报告调用内复用已解析身份，不在导入时固定后端。文档未纳入代码审查，另做本地链接与保护核验。

保护核对6674个已有results/download文件的原大小/修改时间及集合；旧工具配置、两份审核风险目录、两个环境源码、模型/防御核心、旧兼容映射和既有阶段报告不变。当前指南原字节先存original_docs。既有缺失plan.md/report材料引用保持原状态并在检查中单列，不重建用户删除的文件。

本轮未迁移旧缓存/cohort，也未解锁任何研究路线。原生predicate和参考调用质量、服务器模型协议/修订、TSR/ASR、攻击强度、成本与独立终态/E0仍需后续真实实验；I3历史partial和I2 locked状态不变。两环境定义不是完整传递依赖锁。

下一步：服务器切换所需环境并自检，用相同命令和新name执行该基准的baseline/DSCG clean对照，再生成当前基准预检名单并开展匹配攻击。两个后端分别报告，不混用历史名单或任务分母。
