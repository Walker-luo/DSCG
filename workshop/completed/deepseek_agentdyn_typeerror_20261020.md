# DeepSeek Flash / AgentDyn TypeError 定位与修复（2026-10-20）

基于 `0235fbf5b6af22e4fd88c8d02f9d4e25a713c533` 的工作树修复。原用户目录 `results/partial_benchmark/agentdyn/deepseek-flash_test/` 有 27 个文件、9 个分组 `TypeError`，没有计分轨迹。修复前后该目录的路径加文件 SHA256 聚合均为 `a59815b822a72d1fbc23422caa07643ea491065e8f727f270cac8ab4fd053d8f`；未重跑或修改该目录。

## 诊断与原因

使用新的 `workshop/artifacts/20261020_deepseek_agentdyn_typeerror/shopping_two_goals.json`，只选 shopping 的 `user_task_0` 和 `injection_task_0/1`。诊断入口用原 runner、`--progress`、本地 DeepSeek 配置与原生 GOAL 预检，并在调用计分函数前抛出停止标记。命令：

```bash
PYTHONPATH=. /opt/miniconda3/envs/ipi-agentdyn/bin/python -B \
  workshop/artifacts/20261020_deepseek_agentdyn_typeerror/probe_goal_preflight.py
```

退出码 0 表示诊断脚本取得预期证据，不表示 benchmark 成功。实际 GOAL 成功 0、异常 1、计分派发 0；组错误仍是 `TypeError`。安全堆栈定位于 `dscg/pipelines/defended.py:2183`：任务结束的 Token 汇总对 `last_api_error` 字典做减法，产生 `dict - int`，掩盖原来的授权模型请求失败。原 9 组未保存堆栈，不能证明它们全部有同一底层错误；本次最小复现证实这一路径足以造成相同症状。修复前原始服务错误内容未保存，不能从这批结果确定其 HTTP 状态或归因于 DeepSeek 服务。此任务不修改请求角色、重试或授权失败时的 fail-closed 行为。

成本汇总现在仅对数值计数器做差；本任务新增的受限 `last_api_error` 诊断单独保存。离线测试先观察到原始 `RuntimeError` 被 `TypeError` 替换，再验证修复后原异常保留、计数为 1 次调用/1 次失败，诊断不含模拟私密文本。组级错误新增阶段、任务 ID 和最多 8 个代码位置，不保存异常字符串、源码行、局部变量、请求或响应。

另在真实 AgentDyn 套件的离线缓存比较中发现，安装包的 `TaskResults` 未完成 Pydantic 类型构建，读取有效缓存会报 `PydanticUserError`。主机侧在运行原生任务前提供 `FunctionCall` 类型并仅在未完成时调用 `model_rebuild`；不编辑 conda 包，也不改变原生加载器或评分。

## 验证与限制

离线测试使用 AgentDyn/AgentDojo 的真实 suite、原生任务函数和模拟回答，对比开启/关闭进度时的任务结果、调用数与缓存命中。完整命令与记录：

| 命令 | 结果 |
| --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 退出 0；562 tests，skipped 1 |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 退出 0；566 tests，skipped 1 |
| bundled Node `--test tests/*.cjs` | 退出 0；47/47 |
| AgentDyn 两个 benchmark 入口 `--help` | 均退出 0 |
| `git diff --check` | 退出 0 |

日志、诊断运行、任务清单、脚本及文件哈希在 [`validation.json`](../artifacts/20261020_deepseek_agentdyn_typeerror/validation.json)。此次仅一次最小在线定位；没有在修复后再次调用付费模型，因此尚不能宣称 DeepSeek/AgentDyn 真实测量通过，也不能把原始 9 个错误当作有效 ASR/TSR 样本。

下一步：在服务器同步修复后用**新运行名**先跑一个 shopping 的小范围任务，查看原始轨迹的受限 `last_api_error` 和计分状态；如果服务错误仍存在，依据状态码和参数定位请求问题，再扩大到全量 partial。
