# 模型与工具配置

## 环境与后端

从 BaseIntent 根目录执行。AgentDojo 使用 `conda activate ipi`，AgentDyn 使用 `conda activate ipi-agentdyn`；环境定义分别见 [environment.yml](../environment.yml) 和 [environment-agentdyn.yml](../environment-agentdyn.yml)。

```bash
python -m baseintent.benchmark_catalog
```

此检查不调用模型。实际后端以导入路径、安装来源、版本和 revision 识别：AgentDojo 0.1.35 / suite v1.2，AgentDyn v1.2 固定 revision `5353cf7615b135cace8d07c8f12dac53a16b6db3`。两者可能声明同一发行版本，不能只凭环境名判断。当前校验是 `metadata_only`、`runtime_variant=unverified`，不扫描运行时源码，也不认证远端服务。

<a id="24-最小可运行配置与角色复用"></a>

## 模型配置

保留已有 `config/models.local.toml`；首次使用可复制 [models.example.toml](../config/models.example.toml)，填写实际服务配置。凭证只保存在忽略的本地文件或环境变量中，不写公开结果。示意：

```toml
[main]
provider = "dashscope"
model_id = "qwen3.7-flash"

[security]
provider = "dashscope"
model_id = "qwen3.7-flash"
```

服务地址和 `api_key_env` 按模板的 provider 段配置；`api_key_env` 填变量名，`api_key` 才填凭证。默认主模型/安全模型使用 Qwen3.7-Flash 并关闭思考，已有显式服务配置仍生效；未配置独立安全端时可复用主端。

各字段一般按显式 API 参数 → 对应角色环境变量 → TOML 角色配置 → provider 配置/预设 → 兼容默认值解析。CLI 可用 `--model-config PATH` 指定文件，默认 `config/models.local.toml`，也可用 `BASEINTENT_MODEL_CONFIG`。

| 当前变量 | 用途 |
| --- | --- |
| `BASEINTENT_MAIN_MODEL_ID/PROVIDER/BASE_URL/API_KEY/API_KEY_ENV` | 主模型、L2 与语义 progress |
| `BASEINTENT_SEC_MODEL_ID/PROVIDER/BASE_URL/API_KEY/API_KEY_ENV` | L3 审计模型 |
| `BASEINTENT_TOOL_METADATA` | 显式风险目录 |
| `BASEINTENT_TRACE_LEVEL` | summary / standard / full |
| `BASEINTENT_FORCE_RERUN` | 显式强制重跑；`--reuse` 覆盖它 |

原 `DSCG_*` 变量仅作已弃用的兼容回退；新旧同值可并存，异值明确报错。`DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY` 等 provider 凭证变量保持原名。完整重命名边界见[迁移](migration.md)。

## 消息角色兼容与请求排错

共享客户端适配 DashScope/Qwen 的 developer→system；DeepSeek 还把纯文本系统块合并为字符串。baseline、筛选、BaseIntent 和 Dashboard 共用，不修改安装的后端包。实际请求格式、适配身份和出站采样设置进入公开配置，不能假定原生 temperature=0 已发送。

官方 DashScope HTTPS 上支持的 Qwen 组合可使用严格 JSON Schema；其他组合使用 JSON Object 加严格宿主校验。服务拒绝 Schema 时直接报告，不自动降级或修补。400/422 先核对实际模型/provider/端点、角色适配与保存的安全错误字段；超时和连接错误单列，不改成防御成功或另换模型求通过。

<a id="41-加载位置"></a>

## 工具目录

原生名称、描述、参数 schema 与 callable 决定真实可执行接口；TOML 风险目录只描述 effect/sensitivity 等元数据，不替代 schema，也不授予本任务权限。

解析顺序：显式 `--tool-metadata` / API 路径 → `BASEINTENT_TOOL_METADATA` → `config/tools.<backend>.local.toml` → 可完整识别且属于当前后端的 `config/tools.local.toml` → 当前后端内置审核目录。跨后端的已识别通用副本会提示跳过，未知自定义通用目录报错。目录缺项或不兼容在模型调用前失败，不合并分类、不覆盖本地配置。原生 baseline 不加载防御风险目录。

内置目录：[AgentDojo](../config/tools.agentdojo-v1.2.toml)、[AgentDyn](../config/tools.agentdyn-v1.2.toml)。AgentDyn 网页 handler 可能发送、付款或改文件，OTP 可能执行排队动作；不能从工具名称推断只读。

## 运行控制

| 选项 | 默认 / 作用 |
| --- | --- |
| `--prompt-profile legacy` | 当前 BaseIntent 流程；历史显式 profile 保持原义 |
| `--l1-projection-mode projected` | 有界投影；可选 off/shadow |
| `--audit-router-mode` | 防御 CLI shadow；baseline/NoChecker off；API/factory off |
| `--audit-router-threshold 0.70` | 诊断与配置绑定，不调节固定免审 |
| `--audit-retries 0` | 默认无语义重审；显式支持 0/1 |
| `--trace-level summary` | standard/full 增加诊断细节，不改变原生评分 |
| `--no-checker` | 保留 L2/进度与执行监控，关闭语义动作审计 |
| `--no-tool-view` | 规划展示完整目录，保留执行授权检查 |
| `--no-delegated-tasks` | 关闭明确任务来源展开 |
| `--completion-prompt` | 显式启用通用完成提示；默认关闭 |

### L3读取路由

注册、已授权、schema 有效的 `effect=read` 且 public/internal 工具，在 off/shadow/selective 全部固定免审；不按 sink、URL 来源、查询串、内网形式或对象隐私过滤。personal/secret 和效果性动作仍审计。router off 不表示关闭 L3，shadow 也不会额外审计固定免审读取；阈值不改变此范围。非空旧 `--audit-router-artifact` 已停用并拒绝。详见[框架](framework.md)。

full/partial/cohort 多攻击按独立 attack 进程运行，内部顺序保持；clean、单攻击、screen 顺序执行，无新增并发参数。Python API 调用应放在 `if __name__ == "__main__":` 保护内。新策略或有效配置使用新名称；不得用重命名迁移旧缓存或冻结名单。
