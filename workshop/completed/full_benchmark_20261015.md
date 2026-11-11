# 全量 benchmark 入口同步与测试指南

日期：2026-10-15。用户要求核对完整入口相对 partial 的遗漏，并说明当前框架与无防御 baseline 的全量测试方式。本阶段是 runner/文档工程，不修改防御机制、默认审计策略或正式研究路线。

## 已完成

- 旧完整入口独立复制执行逻辑，固定 important_instructions，CLI 没有 baseline/clean/force-rerun/结果根覆盖，也未接入当前控制、配置绑定和紧凑报告。现将其改为共享 runner 的完整范围入口，保留旧 Python 位置参数；当前框架、模型、攻击、报告与 partial 共用。
- full 选择四个 v1.2 suite 的全部注册任务；partial 继续前 3 个用户/注入任务。DoS 两者均遵循每用户首个注入 ID 一次；clean 只运行用户任务。
- full 支持 `--baseline`、`--clean`、`--attack typical/all/具体名称`、`--force-rerun`、模型/输出路径、当前 L1/L2/L3 控制及离线任务清单导出。默认攻击由旧单攻击改为与 partial 相同的 typical；正式命令显式写出选择，避免混淆工作量。
- 原生 baseline 不加载防御元数据/安全客户端；当前 DSCG 默认 projected、工具视图/委托开启、语义审计开启、router off、retry 0、completion false。
- `task_scope`、全部 ID 和完整入口源码进入配置/来源绑定，partial 清单不能缩小 full，且导入清单先于模型构造核查。新结果布局是 `model_run/attack/suite`；旧结果不迁移、不作为新布局缓存。
- 修复已绑定运行的配置冲突被普通攻击异常路径吞掉后覆盖根摘要的问题：现在直接返回失败并保留旧报告。未绑定旧场景摘要仍沿用拒绝复用/记录错误的既有路径；不把它冒充匹配缓存，也不读取其旧指标来补本轮结果。
- 新增 [全量指南](../../docs/benchmark.md)，同步 README、evaluation、模型配置入口及 agent 输出约定；指南包含 clean/typical/all 两组命令、规模、续跑和指标/成本核对。

## 验证与证据

源码基准 revision 为 `2dcc3d18af59de0136286d1c7090dba7624f6f8f`，branch workshop；工作树已有 L1、文档和 Dashboard 修改，全部保留。本阶段改动/原字节与当前哈希在 `workshop/archive/full_benchmark_20261015/`，日志、离线导出与校验记录在 `workshop/artifacts/20261015_full_benchmark/`。

| 验证 | 结果与实际含义 |
| --- | --- |
| 新 full 入口测试初始 RED | 12 项：1 failure、11 errors，暴露缺失的 CLI/参数、范围与来源绑定。 |
| 第一阶段 GREEN | 增补完整原生日志/侧车/续跑和未知安全结果检查后 14/14。 |
| 缓存/清单补充 RED | 15 项中的 2 failures：旧根报告被覆盖、partial 清单未在模型构造前拒绝。 |
| 完整回归首次 | 318 项中 1 failure：未绑定旧摘要的错误报告契约被过早退出改变；保留旧 rejection/reporting 路径后修正。 |
| 最终完整离线回归 | **318/318，exit 0**，其中 15 项 full 入口检查；这是离线工程检查，不是模型防御率。 |
| 完整/partial CLI | full help 和各自清单离线导出 exit 0，完整 ID 与注册目录一致，partial 仍各取前 3。 |
| 原生日志与缓存 | full Slack 的 105 个计分任务加 5 个预检由 stub 执行；重复调用复用缓存，force-rerun 再执行；模型、真实工具与评分均未执行。 |

精确验证命令（cwd 为 DSCG，TMPDIR 仅隔离测试临时文件）：

```bash
TMPDIR="$PWD/workshop/artifacts/20261015_full_benchmark/tmp" conda run -n ipi python -m unittest discover -s tests -p test_full_benchmark.py -v > workshop/artifacts/20261015_full_benchmark/red.log 2>&1
TMPDIR="$PWD/workshop/artifacts/20261015_full_benchmark/tmp" conda run -n ipi python -m unittest discover -s tests -p 'test_partial*.py' -v > workshop/artifacts/20261015_full_benchmark/partial_controls.log 2>&1
TMPDIR="$PWD/workshop/artifacts/20261015_full_benchmark/tmp" conda run -n ipi python -m unittest discover -s tests -v > workshop/artifacts/20261015_full_benchmark/offline_green.log 2>&1
conda run -n ipi python -m experiments.run_benchmark --help > workshop/artifacts/20261015_full_benchmark/full_help.txt 2>&1
conda run -n ipi python -m experiments.run_benchmark --write-task-manifest workshop/artifacts/20261015_full_benchmark/full_tasks.json > workshop/artifacts/20261015_full_benchmark/full_manifest_export.log 2>&1
conda run -n ipi python -m experiments.run_partial_benchmark --write-task-manifest workshop/artifacts/20261015_full_benchmark/partial_tasks.json > workshop/artifacts/20261015_full_benchmark/partial_manifest_export.log 2>&1
```

中间 `green.log`、`full_controls.log`、`cache_red.log`、`offline_final.log` 保留各阶段输出，不覆盖为新结果；最终状态以 `offline_green.log` 及本阶段最终校验记录为准。首条 RED exit 1，其余上列命令 exit 0。

## 规模与限制

只读目录统计为 97 个用户任务、35 个注入任务、每种目标型攻击 949 个组合；typical 每组计划 3,796，all 当前 11 种目标型与 5 种 DoS 共计划 10,924，clean 为 97。计划数不是有效分母/API 调用数，目标型还有未计分注入能力预检。所有这些是目录/调度检查，真实模型调用和新增真实 benchmark rollout 均为 0；未开始用户的正式全量运行。

使用共享紧凑报告/缓存成本约定不代表成本已经可比；续跑可混合缓存与新调用，usage 缺失仍未知。框架工具级边界、读取 deny 例外、E0 pending、I3 partial 及锁定/关闭路线均不改变。

下一步：用户固定配置，以新运行名称执行指南中的 baseline/DSCG 全量 clean 与同攻击集对照，核对实际任务键、有效分母、独立终态和总 Tokens。
