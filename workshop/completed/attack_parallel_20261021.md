# 默认按 Attack 并行测试（2026-10-21）

full、partial及cohort测量默认按attack启动独立spawn进程；每个attack内部仍顺序执行所选场景、原生GOAL预检及计分任务。typical最多同时执行3种攻击；all同时执行全部选定攻击，没有额外并发上限。单attack、clean和screen保持顺序执行；CLI/Python API不新增并发参数。

主进程在任何模型请求前检查完整范围及已有绑定，持有运行锁后调度；冻结名单只读/校验一次，向子进程传递内存名单及只读绑定。pipeline、日志状态和Token tracker由各进程独立创建，子进程只写各自attack目录，主进程统一转发日志、渲染Rich进度及写根报告。分组异常继续执行其他场景，进程异常退出记录未完成组，不生成评分样本；中断先回收全部子进程再生成部分报告。

并行模式、进程数/PID及实际wall_seconds仅属于execution记录，不改变缓存身份。原生评分、计划/有效分母、预检次数、原始轨迹路径及缓存成本口径不变。配置匹配的旧顺序实验可以用原参数和name加reuse恢复；原绑定不改写。

## 验证

证据目录：[20261021_attack_parallel](../artifacts/20261021_attack_parallel/)。开始时commit为99d2117647d0e3b0ed8b5ad038891df7eb790013；原工作区已有任务对齐/效用诊断改动，本任务保留这些改动，未提交commit。before.json保存初始状态及原文哈希，originals/保存修改前字节。

| 检查 | 实际命令与结果 |
| --- | --- |
| AgentDojo完整离线回归 | `conda run -n ipi python -B -m unittest discover -s tests -v`；退出0，642 tests，10 skipped |
| AgentDyn完整离线回归 | `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v`；退出0，646 tests，1 skipped |
| Node | `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs`；退出0，47/47通过 |
| CLI | 两环境各执行full/partial的`--help`，退出0；无新增并发参数 |
| 文档/差异 | `python workshop/artifacts/20261021_attack_parallel/validate_delivery.py`与`git diff --check`；退出0，248处链接无新增错误，4处原有report/report.md链接缺失；383份原预检文件哈希不变 |

最终全套日志为ipi_accepted.log和agentdyn_accepted.log。

真实spawn测试用屏障确认3个attack的执行区间重叠、各自两场景在同一子进程内顺序运行。覆盖分组错误、启动失败、进程异常退出、管道断开、unsupported、运行锁及执行中/进程刚启动时的中断回收；原生离线集成覆盖两环境、full/partial、baseline/DSCG、progress开关、clean、DoS、冻结名单、空场景、配置冲突与缓存续跑。子进程fixture明确拒绝重新打开cohort及原证据。交互终端测试确认共用一个Rich渲染器，错误条冻结耗时；重定向保持纯文本。

原有mock bookkeeping测试显式使用顺序调度fixture；真实spawn验证位于独立集成测试，未依赖父进程mock跨进程继承。专门复核进程生命周期、只读绑定、根报告归属及Token口径。独立review agent因账户额度限制未能执行，已记录在ledger.md；本次采用人工连接代码复核，不能声称独立复核通过。

## 可复核的原生离线对照

`demonstrate.py`在两个环境分别运行原生循环和缓存，使用合成pipeline及每任务25ms人工延时，无网络/真实模型。结果与原始fixture轨迹保存在native_evidence/及demonstration_agentdojo.json、demonstration_agentdyn.json。

| 后端 | 顺序/并行计分样本 | 效用通过数 | 合成Token | 顺序/并行墙钟秒 | reuse新增任务执行 |
| --- | --- | --- | --- | --- | --- |
| AgentDojo | 36/36 | 24/24 | 528/528 | 1.546/1.691 | 0 |
| AgentDyn | 36/36 | 24/24 | 528/528 | 1.524/1.737 | 0 |

两后端各48条原生fixture轨迹在reuse前后保持原字节。这里单任务很短，spawn启动开销超过节省时间，因此本样本并行墙钟更长；它验证隔离、顺序、评分及成本一致性，不证明真实服务加速，也不代表防御效果。真实模型请求通常耗时更长，但实际收益及限流需用户服务器测量确认。没有新增重试、限流策略或官方Batch折扣。

下一步：服务器更新代码后重新执行现有命令即可使用attack并行；正在运行的进程不自动切换。只需一种攻击时仍按原方式指定attack，all会同时启动全部选定攻击。
