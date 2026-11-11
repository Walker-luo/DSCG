# Injection 预检：单次筛选与紧凑输出

2026-10-24完成，证据沿用10月23日开始的 `workshop/artifacts/20261023_screen_single_pass/`。用户要求每个injection task不重复测试，单次未通过即省略，并简化cohort之外的输出。原命令直接生效，无新增参数。

## 行为

- 每目标只执行一次完整无防御GOAL轨迹；轨迹可包含多个模型请求和工具动作，不等于一次HTTP请求。
- 成功保留；原生失败排除；API/上下文错误、中断或不可用记录标记error并跳过，不当成有效失败。处理完目标仍冻结仅含成功目标的cohort；有error退出1，否则退出0。已冻结error名单续跑仍返回1，不再发请求。
- 续跑只处理未开始的目标。已有失败/错误/中断不补测；已完成但缺包装记录的原生轨迹恢复记账。历史复用按路径排序取首条兼容记录，之后的成功不覆盖首次失败。
- 新RULE绑定单次筛选语义。旧已冻结“两次失败”cohort按原规则验证，原文件不重写；旧未完成screen在其他配置一致时允许转为单次规则，按首条尝试判定，原manifest/attempt不变，转换另记compatibility。
- status.json只保留计数、规则、成本和复用拒绝原因计数；summary.md每场景一行。完整decisions/逐次证据只在cohort、attempts和原始轨迹中保留，旧输出不删除、不搬移。

测量读取冻结cohort的轻量校验、完整用户任务/目标选择、攻击测量自己的原生GOAL预检、原生评分和错误分母均未改。主/审计模型、默认DSCG_v3.4及其他候选、防御与票据流程不变。直接GOAL失败不证明间接攻击不可成功，单次筛选不构成安全结论。

## 使用

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_single_01
```

未完成任务继续使用原name；需重测已完成/失败目标时使用新name。旧冻结名单不自动按新规则重解释。完整说明见[预检指南](../../docs/injection_precheck.md)。

## 验证

基点 `7e4c66c`（完整SHA在manifest/before.json）；初始工作树干净，未提交本轮改动。期间出现无关的未跟踪 `3.4-3.5.md`，未触碰。没有付费模型调用或正式实验；所有验证输出在上述artifact根。

| 命令 | 退出码与结果 |
| --- | --- |
| `conda run -n ipi python -B workshop/artifacts/20261023_screen_single_pass/run_offline_tests.py --pattern test_injection_precheck.py` | RED：3失败/1错误，证明重复尝试与重复报告；GREEN最终38/38，socket尝试0 |
| 同一命令改为 `-n ipi-agentdyn` | 最终38/38，socket尝试0 |
| `conda run --no-capture-output -n ipi python -B -u workshop/artifacts/20261023_screen_single_pass/run_offline_tests.py` | exit1：698项，23失败、5错误、10跳过，socket尝试0；ipi_full_final.log |
| `conda run --no-capture-output -n ipi python -B -u workshop/artifacts/20261023_screen_single_pass/baseline_failures.py` | 验证脚本exit0：原25个失败测试方法均用修改前的两份预检模块在内存中复现，23失败/5错误；不是测试通过，也没有改回磁盘源码 |
| `conda run -n ipi python -B workshop/artifacts/20261023_screen_single_pass/verify_delivery.py` | exit1：选择规则/专项/全库失败复核通过，但results/download出现变更、新增和删除，保护校验不宣称全不变；validation.json |
| `git diff --check` | exit0 |

专项用例覆盖首次失败后原本可成功也不复测、错误/中断续跑、首次历史失败不被后续成功替换、旧规则冻结名单/未完成运行、原生轨迹恢复、哈希被改拒绝、空场景、cohort测量入口和原始评分范围。错误记录现也校验已声明的trace/manifest哈希；复核建议已通过额外RED→GREEN用例落实。

全库失败涉及已有审计、委托、I3、版本/协议预期等测试，完整名称及基线复现见[baseline_failure_validation.json](../artifacts/20261023_screen_single_pass/baseline_failure_validation.json)。本轮不修改这些防御模块，不宣称全库回归通过、修复I3或通过研究闸门。没有网页改动，未跑Node；AgentDyn只运行预检专项，未运行其全库回归。

最初全量启动器缺少 `__main__` 保护，spawn子进程重复发现测试，已中断exit130；日志保留ipi_full.log。修复仅在本轮artifact启动器中，保护网络连接并允许正常测试导入，然后重新完成上述全库检查；不能把首次中断记作通过。

修改前快照覆盖17,040份results/download文件。校验期间观察到历史summary、导出目录及.DS_Store变化/删除，并新增v3.5结果与导出；来源未核定，不能宣称所有用户文件未变。差异仅记录于[concurrent_result_changes](../artifacts/20261023_screen_single_pass/concurrent_result_changes.json)及validation；没有恢复、删除或覆盖这些变化，也未将新增结果算成本轮工程效果。

本轮模型请求0、正式计分样本0；[validation](../artifacts/20261023_screen_single_pass/validation.json)与[manifest](../artifacts/20261023_screen_single_pass/manifest.json)保存命令、完整SHA和日志哈希。下一步由测试者按原命令运行新的screen，查看成功目标列表；本轮不会消耗任何已关闭campaign的剩余预算。E0 pending、I3 partial、I2 locked不变。
