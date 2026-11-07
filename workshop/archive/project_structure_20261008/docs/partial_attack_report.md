# Partial benchmark 攻击选择入口

2026-10-07 的工程改动：为 `experiments.run_partial_benchmark` 添加 `--attack`，默认 `all`，支持空格分隔的多个名称和重复选项。该改动只扩展攻击执行入口，不增加防御机制，也不修改 AgentDojo 原始安全判定。

## 使用

```bash
# 无防御 baseline，默认全部自动攻击
conda run -n ipi python -m experiments.run_partial_benchmark \
  --baseline --force-rerun --name baseline-all-20261007

# DSCG，相同攻击矩阵和任务选择
conda run -n ipi python -m experiments.run_partial_benchmark \
  --force-rerun --name dscg-all-20261007

# 指定攻击；单攻击沿用旧输出路径
conda run -n ipi python -m experiments.run_partial_benchmark \
  --baseline --attack tool_knowledge --name baseline-tool-20261007
```

以上模型评测命令未在此次实现中执行。默认从当前安装的 AgentDojo registry 解析攻击；当前注册 17 种，其中 `manual` 要求逐条人工输入，默认排除，可显式指定。当前 16 种自动攻击为：

```text
captcha_dos, direct, dos, felony_dos, ignore_previous,
important_instructions, important_instructions_no_model_name,
important_instructions_no_names, important_instructions_no_user_name,
important_instructions_wrong_model_name, important_instructions_wrong_user_name,
injecagent, offensive_email_dos, swearwords_dos, system_message, tool_knowledge
```

保留用户调整后的选择：v1.2 四套件，每套件前 3 个用户任务；目标型攻击的 3 个注入任务按 seed 7 做 SHA-256 排序。11 种目标型攻击共计划 396 条，5 种 DoS 共计划 60 条，总计 456 条攻击评测；AgentDojo 对目标型攻击还会做注入任务能力预检。

DoS 每用户只使用第一个注册的注入任务，遵循上游 `security = not utility`。报告记录该实际 ID、`attack_kind`、`security_definition` 和 `planned_tasks`，不把 DoS 的任务失败率与目标型攻击成功率混成一个 ASR。

多攻击分别保存到 `<model_id>_<name>__<attack>/<suite>/`；基础 `<model_id>_<name>/` 保存 `attack_manifest.json` 和按攻击拼接的 `all_report.txt`。单攻击保留历史路径。配置错误直接失败；其他攻击运行错误记为 error、保留已有数据、继续其他攻击并以 1 退出，不生成零 ASR 来替代失败。全部执行完成退出 0，仅表示入口执行完成。

## 验证

命令均在 `/Users/luo/Desktop/AgentDefence/DSCG` 执行：

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -p 'test_partial*.py' -v` | 0 | 14 项相关测试通过（加入真实载荷生成测试前）；红绿验证已完成 |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 126/126 通过，包含最终 15 项 partial 测试 |
| `conda run -n ipi python -m experiments.run_partial_benchmark --help` | 0 | 帮助列出 `--attack` 和默认 all |
| `git diff --check` | 0 | 工作树补丁格式检查通过 |

离线测试使用真实 registry、真实套件和 ground-truth injection reachability，成功生成 456/456 份载荷，无错误或跳过。它不调用主模型或安全模型；格式检查时使用已知模型名称 `gpt-4o-2024-05-13`。另用 mock benchmark 验证两种防御配置下全部 16 种攻击的任务 ID、报告隔离、DoS 分母、失败记录，以及单攻击路径兼容。

旧 baseline 回归的期望仍是 seed 20260927、2×2，与用户已修改的 seed 7、3×3 不符。此次同步测试期望与文档，保留现有实现选择，没有恢复旧抽样或改写历史结果。

只读代码审查没有未解决的问题。审查发现旧的无攻击 Python 分支向上游传入不存在的 `injection_tasks` 参数；先用 `autospec=True` 复现失败，再删除该参数后回归通过，避免普通 mock 掩盖接口错误。

日志、帮助和代码状态在 [`../examples/results/partial_attacks/20261007_cli/`](../examples/results/partial_attacks/20261007_cli/)。基准 revision 是 `7b214988a6a072a7659534220da7e4fd06b3f4e2`；无新 commit，实现处于工作树。`code_revision.json` 记录实现文件哈希，`artifacts.sha256` 固定产物内容。

## 限制和下一步

- 本次真实模型评测样本为 0；456 是离线载荷检查数和当前运行计划数，不是有效安全结果分母。
- 全部攻击是安装版本中注册的自动模板及 DoS，不包含未安装的自适应优化器，也不把交互式 manual 计入自动覆盖。
- 仍使用 AgentDojo 原始 predicate：travel `injection_task_6` 的酒店名子串判定会把拒绝中的引用算成功；本次未改判定器。DoS 本身也不能区分原有任务能力不足与攻击导致的失败。
- CLI 回归通过不等于 E0 payload/宿主 oracle/trace 验收通过，不解锁 I2，也不证明 DSCG 有额外安全收益。
- 复用缓存时 token tracker 仅记录本次调用开销；需要真实可比的运行开销时使用新名称和 `--force-rerun`。

下一步：使用新运行名称执行同一任务矩阵的 baseline/DSCG，再完成 E0 对原始 predicate、payload 投递和有效分母的审计。
