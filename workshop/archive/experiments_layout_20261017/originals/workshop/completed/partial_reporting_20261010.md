# Partial 结果摘要与失败片段（2026-10-10）

状态：工程实现完成。用户请求完善 `experiments/run_partial_benchmark.py` 的保存流程，并确认“失效案例”指 TSR=false 与 ASR=true；缺失指标/运行错误单列。本阶段只改报告，不增加防御机制、模型调用或原生重评分。

## 实现

- 每次运行目录下新增 `summary.md`，按 attack × 场景列出 TSR、原生 ASR、防御成功率、成功数/分母、完成/计划任务数、主/审计/合计 Token、成本统计范围，以及失败案例的原始路径、详情行号。
- 新增 `failure_cases.jsonl`，每行一个案例，支持同时/单独标记 TSR 失败与 ASR 成功；缺失/非布尔安全结果、缺失计划任务、任务错误和运行异常分别标记。
- 仅读取需报告案例的原生 JSON。每例最多 6 个片段、每片最多 800 字符，保留 JSON pointer、字符范围及截断标记；任务描述/攻击目标各最多 400 字符。优先选错误、最后的助手文本、最近工具调用和精确注入匹配的工具返回，不复制完整案例。
- 不覆盖原生任务 JSON；原有场景 JSON/TXT/CSV 和合并 TXT 保留。正常缓存读取也生成新报告，空失败集产生空 JSONL。异常保留本次已完成场景，不读未完成场景的残留旧统计。DoS 和无攻击的分母/含义继续单独展示。

实现：[partial_reporting.py](../../experiments/partial_reporting.py)、[runner](../../experiments/run_partial_benchmark.py)；使用说明：[评测指南](../../docs/benchmark.md#结果文件)。

## 验证

所有产物位于 `workshop/artifacts/20261010_partial_reporting/`；代码基线 `7f16f19a33045a9c055230534d87b9e408a74649`，实现留在工作树，最终源码/日志哈希与完整工作树状态见该目录的 `evidence.json`。保留会话开始时的其他本地改动及 `System_TODO.md` 删除。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -p test_partial_reporting.py -v` | 1 | RED：8 个测试均因新增报告不存在而失败，日志 `red.log` |
| 同上（首轮实现） | 1 | 7/8 通过；clean fixture 写死任务 ID 与注册前缀不符，改为读取实际注册 ID，日志 `green.log` |
| `conda run -n ipi python -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 35/35（含 10 个新增报告测试），日志 `partial_tests.log` |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 179/179，日志 `regression.log` |
| `conda run -n ipi python workshop/artifacts/20261010_partial_reporting/generate_preview.py preview_01` | 0 | 4 行场景、36 个合成结果、12 个失败案例，0 模型调用；日志 `preview_01.log` |
| `conda run -n ipi python workshop/artifacts/20261010_partial_reporting/validate_preview.py offline-preview_preview_01` | 0 | 检查行号、路径、片段边界、原始结构分离及原生 JSON 哈希，日志 `preview_validation.log` |
| `git diff --check` | 0 | `diff_check.log` |

合成预览：[summary.md](../artifacts/20261010_partial_reporting/partial_benchmark/offline-preview_preview_01/summary.md)、[failure_cases.jsonl](../artifacts/20261010_partial_reporting/partial_benchmark/offline-preview_preview_01/failure_cases.jsonl)。合成标签用于测试格式，不是新的真实 benchmark 样本或防御率。

## 限制与下一步

片段只是观测线索，不能独立证明导致失败的步骤、payload 送达或恶意动作执行；精确匹配失败时不猜测注入片段。截断可能省略上下文。强制终止可能还未生成运行级文件；未完成场景只显示运行错误/N/A，不能把部分执行伪装成完整指标。历史目录不自动补写，原生配置绑定继续生效。

真实 E0、I3 partial、I2 锁定及关闭路线不变。本阶段不运行真实模型/benchmark、不回写用户 `results/` 或 `download/`。下一步：在用户下一次正式 partial 运行中核对失败索引与原始轨迹，继续独立审查原生输出 predicate 的误报。
