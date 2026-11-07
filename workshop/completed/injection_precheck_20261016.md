# Injection 目标预检与筛选测量实施记录

日期：2026-10-16。状态：独立入口、离线回归与兼容性核查完成；服务器真实预检/筛选攻击测量尚未执行。

## 实现

用户批准新增独立预检文件，先直接请求 injection GOAL，复用兼容记录并复测有效失败，再冻结目标名单测 baseline。实现为 [独立脚本](../../experiments/run_injection_precheck.py)，使用方式见 [用户指南](../../docs/injection_precheck.md)，用例见 [测试](../../tests/test_injection_precheck.py)。

- `screen` 复用现有 baseline 工厂和原生无注入任务执行。任一有效成功保留；两次有效失败排除；错误不计失败。扫描全部兼容历史预检，成功优先，重复文件哈希不重复计数。
- 绑定检查先于新客户端构造；尝试独立保存，保留原始引用/hash。根据预写绑定恢复中断前已完成的原生结果，无 usage 时成本未知。同名源码/配置变化拒绝执行。
- 全部目标完成判定后独占创建 `cohort.json`，使用前复核完整用户集合、筛选规则和原生证据。`benchmark` 复用共享 runner 自定义清单能力，不改默认选择规则或防御源码。空场景跳过，全空/未决/DoS 拒绝执行。
- 结果附冻结名单、原始/保留分母、计划组合和预检报告；原生攻击预检仍执行。其独立 Token 成本为 null，共享总成本已包含该开销。DSCG/shadow/full 使用同一名单。

## 验证

基准 revision：`db66f2679240460d8ca8402507bdd311e38aa292`；交付工作树 dirty（脚本、测试、文档和索引/交接更新）。精确命令、退出码、文件哈希和工作树状态见 `workshop/artifacts/20261016_injection_precheck/validation.json`。原始产物默认忽略，未分发时须另行复核。

| 命令/检查 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_injection_precheck.py -v` | 0 | 16/16；原生 TraceLogger、模拟任务、复用/复测/错误/恢复/绑定/空场景/DoS及共享 runner 范围 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 358/358 |
| `conda run -n ipi python -B -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 38/38 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_full_benchmark.py -v` | 0 | 15/15 |
| `conda run -n ipi python -B -m experiments.run_injection_precheck --help`（及 `screen --help`、`benchmark --help`） | 0 | 三入口只显示帮助，不构造模型客户端 |

TDD 原始记录：`red.log` 是新入口缺失的 9 项失败；`red_02.log` 复现较晚目录已有成功被忽略；`red_03.log` 复现完成原生结果后 wrapper 记账中断；`red_04.log` 验证缺少独立预检报告。后续 `green_06.log` 为 16/16。独立代码审查提出的历史成功优先问题已修复，再审无重要遗留项。

只读检查现有 `results/benchmarks/deepseek-flash_baseline/`：四场景注册目标 35 个，兼容历史记录 14 条，均在 workspace，native utility 通过 10、失败 4（3/4/5/8）。这是读取旧结果，不是新模型样本；四个失败尚未被本阶段复测或冻结剔除。目录原有 280 个文件的哈希保存在 `historical_compatibility.json`，结束时重新核对。

新检查产物均在 `workshop/artifacts/20261016_injection_precheck/`。修改前的 README、指南索引、全量指南、AGENTS 和 workshop 索引原始字节在 `workshop/archive/injection_precheck_20261016/originals/`，映射见 `document_originals.json`。

## 限制与下一步

筛选结果只描述“本轮 baseline 直接目标预检通过子集”。直接拒绝可能被间接攻击绕过，复制/排版或原生评分差异也可能导致失败，不能统称模型不会做；保留 native 标签，另作独立轨迹/终态复核。历史 manifest 缺少独立环境哈希，模型服务实际修订未固定，复用可比性存在边界。

新增真实模型调用 0、真实 benchmark 样本 0；没有 E0 通过、I3 改善或 L3 部署阈值。正式研究 ready/locked/closed 状态不变。

下一步：在服务器用新 name 执行 `screen`，解决 error 并检查失败轨迹；名单冻结后，以同一名单运行新 baseline 与 DSCG/shadow，分别报告有效分母及完整成本限制。
