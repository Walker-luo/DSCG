# Partial 场景选择

日期：2026-10-17。基准 revision：`9f385a3433f6d09bb7c9b278258ecc43f34e62c8`，本次修改尚未提交。

`experiments.run_partial_benchmark --suites travel banking slack` 在优化阶段跳过 workspace。默认四场景、每场景注册顺序前3个用户/注入任务、攻击选择和原生评分不变。使用示例见 [评测指南](../../docs/evaluation.md#对照与输出)。完整 full / screened 测量仍使用原入口，full CLI 不新增缩减场景选项。

启动输出与 attack_manifest.suites 记录选择，partial 根目录 suite_manifest.json 绑定完整场景列表；同名改用不相交集合也在执行前拒绝，旧报告保持原样。读取任务清单仍按显式选择执行，离线导出只含所选场景。非法、空或重复名称在模型构造前拒绝。

共享 runner 字节变化会影响预检源码绑定，因此保留原始17文件兼容映射，并额外记录基准revision的完整20文件哈希集合。只允许这两组明确已知来源迁移到当前固定目标哈希；模型、任务、GOAL、评分、筛选规则和防御代码仍须匹配。旧manifest、attempt、cohort不改写。新攻击测量继续使用新name。

## 验证

工程产物根为 `workshop/artifacts/20261017_partial_suites/`。`initial_state.json` 和 originals 保存修改前字节/哈希；`validation.json` 记录精确命令、退出码、工作树和产物哈希。

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 43/43；三场景计分、clean、导出、范围绑定及既有回归 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_injection_precheck.py -v` | 0 | 28/28；已知旧状态补测且不重复完成目标，未知代码/证据变化仍拒绝 |
| `conda run -n ipi python -B -m unittest discover -s tests -p test_full_benchmark.py -v` | 0 | 15/15；full原有范围/完整性行为 |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 0 | 375/375 |
| `conda run -n ipi python -B -m experiments.run_partial_benchmark --help` | 0 | 显示partial场景选择用法 |
| `git diff --check` | 0 | 无空白错误 |

RED→GREEN日志保留初始缺少CLI/无效集合校验，以及旧统一入口预检状态的源码绑定冲突；外部模型工厂、攻击构造和原生执行使用离线模拟。防御源码哈希保持不变。

三场景×每场景3用户×3注入×4典型攻击，计划108条计分rollout；同范围clean为9用户。省略workspace相对默认144条少36条（25%），不是实际Tokens/费用节省率。原生预检仍额外运行，planned不等于有效计分分母，不能外推到workspace或完整评测。

新增真实模型请求0，真实benchmark样本0。E0 pending、I3 partial、I2 locked及closed路线不变。下一步：用户在服务器使用新的匹配baseline/DSCG名称和相同三场景列表进行优化对照。
