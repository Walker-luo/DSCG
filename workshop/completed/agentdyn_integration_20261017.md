# AgentDyn 全流程接入交付（2026-10-17）

状态：工程接入与离线验收完成。当前新实验只支持shopping、github、dailylife；原四场景结果保留。没有付费模型请求或真实模型全量实验，不宣称TSR、ASR、攻击强度改善或E0通过。

## 实现范围

- 新独立环境 `ipi-agentdyn`，原 `ipi` 保留。本机通过复制旧环境并仅在新环境安装固定fork验收；[environment-agentdyn.yml](../../environment-agentdyn.yml)提供服务器安装定义，但本轮没有另做从零解析全部传递依赖的安装。
- 固定仓库 `https://github.com/SaFo-Lab/AgentDyn`，提交 `5353cf7615b135cace8d07c8f12dac53a16b6db3`，原生发行版本agentdojo0.1.35、suitev1.2。[锁定记录](../../config/agentdyn.lock.json)核对Git来源/完整提交及1374个源码/数据文件，不仅依赖版本号。
- [共享目录](../../dscg/benchmark_catalog.py)供full、partial、预检、续跑和Dashboard使用；实际任务和攻击由固定后端注册表取得。full/partial/clean/native baseline、typical/explicit/all、cohort、自定义根目录与reuse继续可用。
- 新命名为CLI `<model>_agentdyn_<name>`、网页 `agentdyn_<时间>_<ID>`；保持原根目录和任务JSON布局。运行/名单协议v2与导出schema2绑定仓库、revision、native version、整体实现/目录及任务/环境/攻击/工具组件哈希；旧AgentDojo缓存、cohort和旧兼容映射不被当作AgentDyn使用。
- [新工具风险目录](../../config/tools.agentdyn-v1.2.toml)覆盖65个不同名称、100次场景注册。源码审查记录每次注册的场景、schema、函数/实现文件哈希；同名风险使用保守并集。浏览、表单、OTP续执行、下载、发票及邮件等按真实副作用分类。没有新增免审、handler授权或参数级机制。
- 新三个场景沿用完整L1来源封装，没有新投影profile。`read_file(path)`文本返回可用既有有限文件委托；有副作用的browse_webpage不能替代纯get_webpage的委托准备读取。L2/L3/Monitor/ticket及现有模型/默认配置保持。
- 网页三场景、注册攻击、数量、启动检查、进度、报告和有效配置已接线；历史按记录中的场景读取，未知身份不从相邻场景推定。不同身份/目录/任务选择不自动配对或合并分母。旧原始文件不迁移、不补造身份。

## 实际目录与分母

| 场景 | 用户任务 | 注入目标 | 注册工具 | 每目标型攻击组合 |
| --- | ---: | ---: | ---: | ---: |
| shopping | 20 | 9 | 39 | 180 |
| github | 20 | 9 | 34 | 180 |
| dailylife | 20 | 10 | 27 | 200 |
| 合计 | 60 | 28 | 100次注册 / 65个名称 | 560 |

full clean60，typical三攻击计划1680；partial原注册前3×3保留，clean9、typical81。原生攻击目标预检另计；以上不是API请求次数或有效标签分母。

## 审查发现与修复

独立新上下文审查提出4项Important，均已修复并补回归：

1. 网页clean向原生函数传了不支持的injection_tasks。改为精确原生签名，并显式传suite版本；严格签名测试先失败、后通过。
2. 原生捕获JSON/API错误时可返回utility=false/security=true，之前派生ASR仍纳入布尔值。真实原生离线复现9个错误被当作9个有效成功攻击；新增共享outcome投影读取原trace.error，错误派生标签为null、状态infrastructure_error。原生JSON/标签不改；total/planned、有效utility/security分母、错误数及Token分别保留。CLI存在任务错误退出1，接受的错误缓存不自动重试。报告、网页和导出同步。
3. 已知shopping与未知github在同目录时，历史身份可能从已知相邻场景传播。缺失场景身份现在保持未知，比较和热图不借运行级推定身份配对。
4. 历史白名单丢失四项组件哈希。现在历史与schema2导出保留tasks/environments/attacks/tools哈希，并保留有效分母和错误数。

旧报告原字节不改；新报告的错误分母语义有明确版本/目录边界，不直接同旧错误混入的指标比较。

## 验证与证据

起始代码revision为 `2a2b17ce1275b9c8372814935989df5e6d9161e7`，起始工作树干净；交付为当前workshop分支未提交修改，未推送、合并或创建PR。当前文件哈希由[交付清单](./agentdyn_integration_20261017_manifest.json)记录；原始日志/中间失败保持在[独立产物目录](../artifacts/20261017_agentdyn_integration/)。

| 实际命令 / 阶段 | 退出与结果 | 产物（相对任务产物目录） |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -v`（修改前） | 0，413/413 | baseline.log |
| `conda create --name ipi-agentdyn --clone ipi --offline --yes` | 0 | environment_clone.log |
| `TMPDIR="$PWD/workshop/artifacts/20261017_agentdyn_integration/tmp" conda run --no-capture-output -n ipi-agentdyn python -m pip install --force-reinstall --no-deps 'agentdojo @ git+https://github.com/SaFo-Lab/AgentDyn.git@5353cf7615b135cace8d07c8f12dac53a16b6db3'` | 0，固定Git安装 | agentdyn_install.log |
| `conda run -n ipi-agentdyn python -B -m dscg.benchmark_catalog` | 0，来源/字节/实际目录 | catalog_final.json |
| `conda run -n ipi-agentdyn python -B -m experiments.run_benchmark --write-task-manifest workshop/artifacts/20261017_agentdyn_integration/full_tasks_final.json` | 0，60用户/28目标 | full_tasks_final.json、full_tasks_final.log |
| `conda run -n ipi-agentdyn python -B -m experiments.run_partial_benchmark --write-task-manifest workshop/artifacts/20261017_agentdyn_integration/partial_tasks_final.json` | 0，9用户/9目标 | partial_tasks_final.json、partial_tasks_final.log |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 0，451/451，无跳过 | python_delivery_final.log |
| `node --test tests/*.cjs` | 0，39/39 | node_delivery_final.log |
| `conda run -n ipi python -B -m experiments.run_benchmark --baseline --clean --name rejected_original_ipi --results-dir workshop/artifacts/20261017_agentdyn_integration/wrong_backend` | 1，预期拒绝；未建模型/结果目录 | wrong_backend_final.log |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261017_agentdyn_integration/verify_delivery.py` | 0，保护/目录/链接核对 | delivery_checks.json |
| `git diff --check` | 0 | diff_check.log |

Python总数包括7个真实原生集成测试方法：[test_agentdyn_native.py](../../tests/test_agentdyn_native.py)。三场景分别运行正常任务、直接目标正/负终态、原生可注入邮件反馈；购物密码步骤从实际工具邮件获取随机OTP，不读取隐藏状态替代反馈。真实网页click触发下载，allow才改变文件状态，deny/abstain、无权限和无效元数据阻断。CLI9个、网页1个原生捕获错误被排除派生计分，原始错误与security=true保留。直接目标脚本是原生评分管线自检，不是间接攻击成功率。

其他流程测试覆盖clean/full/partial、注册攻击、预检/cohort、缓存续跑、配置冲突、Token和异常。网页使用Flask/API与Node检查及真实原生错误脚本；未用图形浏览器复验布局。独立审查错误复现、中间RED/GREEN、工具来源审查和阶段日志均保留，最终结果由交付日志为准。

## 保护与限制

- 保护检查核对6674个已有results/download文件的大小和修改时间；核心防御/模型源码、旧环境定义/目录哈希及旧本地工具配置保持。未覆盖凭据、原环境或用户实验结果。当前指南原字节先归档在本次产物docs_originals，完成阶段材料与旧证据未改写。原已缺失的plan.md、report/report.md引用作为既有文档缺口记录，没有重建用户删除的文件。
- 不增加任务ID、具体对象或标准答案规则；模型、安全模型和默认防御/重试/路由选择不变。
- 上游部分shopping/github目标的参考调用是占位内容或与GOAL不一致，shopping部分utility与自然语言数量也有差异。本轮保留上游任务/评分；tool_knowledge可能受参考调用质量影响。错误应单列，不能把原生predicate当成独立安全oracle。
- 通用网页工具仍是工具级边界，允许一个browse/OTP调用可能触发内部副作用；没有独立handler/参数授权。新环境的工具语义变化不等于增强防御。
- 安装源码锁不固定远端服务模型修订或完整传递依赖。真实TSR/ASR、攻击强度、成本、重复匹配和独立终态核查仍待服务器实验；本次不解锁I2、不宣告E0通过，I3历史partial状态不变。

下一步：按[当前全量指南](../../docs/benchmark.md)在服务器自检固定环境，再用新name做60个clean任务的同轮baseline/DSCG对照；检查错误与配对得失后做预检和匹配攻击。保持完整分母及原生轨迹，勿复用旧AgentDojo名单。
