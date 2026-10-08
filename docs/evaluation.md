# 评测指南

以下命令从 `DSCG/` 执行，默认 `ipi` 已激活。普通对照无需导入外部任务清单。

## 模型与工具配置

使用 [config/models.example.toml](../config/models.example.toml) 创建被 Git 忽略的 `config/models.local.toml`，配置 `[main]` 和 `[security]` 的 provider、model_id、api_key_env，可选 base_url。省略 `[security]` 时复用主模型。配置优先级为函数参数 > `DSCG_MAIN_*` / `DSCG_SEC_*` 环境变量 > 本地 TOML > Provider 默认值；`DSCG_MODEL_CONFIG` 可覆盖路径。

当前 AgentDojo 适配层不保留 DeepSeek reasoning_content，项目使用 reasoning_effort="none"；重建环境时仍需核对消息角色兼容性。实现见 [model_config.py](../dscg/model_config.py)。

工具风险元数据缺省回退到内置 [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml)。显式路径、`DSCG_TOOL_METADATA` 和已有本地配置优先；未知或无效工具保持 critical。`python -m experiments.generate_tool_metadata` 可生成本地目录，默认不覆盖已有文件。

## 对照与输出

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun --name baseline_compare_01
python -m experiments.run_partial_benchmark --force-rerun --name workshop_compare_01
```

baseline 使用原生 AgentDojo 工具循环，不使用 DSCG、安全模型或 AgentDojo 防御。两组均为 v1.2 四场景，各取注册顺序前 3 个用户任务和前 3 个注入任务；记录中的 seed:7 不参与当前前缀子集选择。核对各场景 `summary.json` 的 task_selection，不能只凭场景或攻击筛选认为已配对。

用户正式结果为 `results/partial_benchmark/<model_id>_<name>/<attack>/<suite>/`，其中保存原始任务 JSON、summary、CSV 和报告；full 侧车与任务 JSON 同目录。运行根保存 attack_manifest.json 和 all_report.txt，每攻击目录另有跨场景报告。旧目录保留，不读作新布局缓存。

修改配置后使用新运行名称；`--force-rerun` 不绕过 manifest 的配置绑定。攻击异常记录为 error，继续其他攻击后退出 1；成功完成退出 0，但不表示安全性或 E0 验收通过。

Agent 临时模型评测必须显式覆盖输出，例如：

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun \
  --name agent_probe_01 \
  --results-dir workshop/artifacts/20261008_agent_probe/partial_benchmark
```

每次使用新的任务目录和运行名称；模型评测需要配置 Key。

## 攻击选择

默认 typical 为 4 种目标型攻击，共计划 144 条攻击评测，另有注入能力预检；all 为当前 16 种自动攻击，共计划 456 条。计划数不等于有效样本分母。预设不能与具体名称混用；missing typical 攻击会报错，manual 不可选。

```bash
python -m experiments.run_partial_benchmark --baseline --attack tool_knowledge --name baseline_tools_01
python -m experiments.run_partial_benchmark --attack tool_knowledge injecagent --name dscg_two_attacks_01
python -m experiments.run_partial_benchmark --baseline --attack all --name baseline_all_01
```

DoS 显式选择或 all 才运行，按 AgentDojo 原生规则每个用户使用首个注册注入任务一次，成功按任务失败计分；不得与目标型 ASR 合并。典型集仅控制工作量，变体不代表独立发表方法。

可选攻击（当前 AgentDojo 安装版本）：

这些攻击均有 AgentDojo 官方实现。[AgentDojo 发表于 NeurIPS 2024 Datasets and Benchmarks][agentdojo-publication]，[InjecAgent 发表于 ACL Findings 2024][injecagent-paper]。表中区分论文实验与 AgentDojo 官方模板；16 个名称包含消融变体，并非 16 种独立发表的方法。`system_message` 和 `tool_knowledge` 在此仅标为 AgentDojo 官方实现。

| `--attack` 值 | 简要说明 | 类型 | 来源 |
| --- | --- | --- | --- |
| `typical` | 默认运行上述 4 种典型目标型攻击 | 批量选择 | 本项目选择器 |
| `all` | 显式运行全部 16 种自动攻击 | 批量选择 | 本项目选择器 |
| `direct` | 用 `TODO` 直接要求执行攻击目标 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `ignore_previous` | 要求忽略原指令，改做攻击任务 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `system_message` | 用系统消息标记伪装指令来源 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `injecagent` | 用 `IMPORTANT` 和“忽略之前指令”强调攻击目标 | 目标型 | [InjecAgent][injecagent-paper]、[AgentDojo 官方适配][agentdojo-baseline] |
| `important_instructions` | 冒充用户，声称必须先完成攻击目标才能做原任务 | 目标型 | [AgentDojo §4.1–4.2][agentdojo-paper] |
| `important_instructions_no_user_name` | 上述模板中，用泛称代替真实用户名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_model_name` | 上述模板中，用泛称代替真实模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_names` | 同时用泛称代替用户名和模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_user_name` | 换成错误用户名，测试身份线索的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_model_name` | 换成错误模型名，测试模型称呼的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `tool_knowledge` | 在重要指令模板中补充工具调用顺序和参数占位符 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `dos` | 要求立即停止当前任务，输出指定文本 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `swearwords_dos` | 用辱骂内容诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `captcha_dos` | 声称须先解决验证码，否则停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `offensive_email_dos` | 要求发送威胁性消息，诱使模型拒绝并中断任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `felony_dos` | 声称处理当前内容违法，诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |

[agentdojo-publication]: https://papers.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
[agentdojo-paper]: https://arxiv.org/html/2406.13352v2
[injecagent-paper]: https://aclanthology.org/2024.findings-acl.624/
[agentdojo-baseline]: https://agentdojo.spylab.ai/api/attacks/baseline_attacks/
[agentdojo-variants]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/important_instructions_attacks.py
[agentdojo-dos]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/dos_attacks.py

## 可选控制与日志

| 参数 | 用途 |
| --- | --- |
| `--name NAME` | 区分运行，保留历史结果 |
| `--baseline` | 匹配子集的原生无防御控制 |
| `--attack NAME [NAME ...]` | 具体攻击，可重复该选项；默认 typical，all 显式运行全部 |
| `--force-rerun` | 重跑任务；也可设 DSCG_FORCE_RERUN=1 |
| `--clean` | 相同用户任务的无攻击效用控制；使用独立运行名称 |
| `--no-checker` | 关闭语义审计，保留工具授权、Monitor、ticket |
| `--trace-level summary/standard/full` | 默认 summary；standard 简化逐条记录；full 详细诊断和压缩侧车，增加写入成本 |
| `--include-extra-info` | full 的兼容快捷开关 |
| `--model-config PATH`、`--tool-metadata PATH` | 覆盖本地模型配置、工具元数据 |
| `--results-dir DIR` | partial 输出根目录；agent 必须指定 workshop/artifacts 下的新目录 |

当前优化没有新增必需参数。`audit_retries=0`、`completion_prompt=false` 保持默认；历史可选补救不叠加到当前框架。

full tracing 不改变防御逻辑。用户此前中断的 full 运行没有确认根因，不能据此认定日志 bug。日常对比用 summary，具体排错才使用 full。

用户完整评测入口为 `python -m experiments.run_benchmark --name full_compare_01`：全部任务、固定 important_instructions、默认输出 `results/benchmarks/`。该入口目前没有 `--results-dir`；agent 不应直接用它生成临时测试，需先具备显式隔离输出的入口。没有新增环境变量或自动重定向行为。

## 指标与证据

同时报告 TSR、AgentDojo 原生 ASR、总 Token 与全部有效/错误/跳过分母，预检成本单列或明确包含。输出文本 predicate 的误报仍需独立 E0 审计，保留原始结果；历史 smoke 或单轮小样本不能支持通用防御结论。

当前 I3 为 partial（有效24，范围缺口8，工具边界缺口0），E0 合成自检并未证明真实 harness 通过；I2 与三层机制尚未解锁。离线命令见[项目 README](../README.md)，详细证据见 [I3 报告](./i3_p0_stress_report.md)与 [V2 后续报告](../workshop/framework_v2_followup_report.md)。
