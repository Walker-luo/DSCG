# v3.7 模型、工具与运行配置

当前默认 `static-task-v354 / DSCG_v3.7`。配置由宿主提供，模型返回不能修改。防御机制与层间数据流见 [架构说明](architecture.md)。

## 首次检查

```bash
conda activate ipi
python -m dscg.benchmark_catalog
```

工作站 AgentDojo 环境为 ipi，测试服务器为 DSCG。后端按实际包路径、安装来源、版本和 revision 识别，当前检查为 metadata-only。新测量以 AgentDojo 为范围，未知后端或跨后端场景在模型调用前拒绝。安装见 [README](../README.md#安装与配置)。

<a id="2-主模型和审计模型"></a>

## 模型连接与角色

`main` 用于主模型规划、L2 两阶段编译和最终回答；`security` 用于 L3。main 需要 tools/function calling 与 JSON 输出能力，security 需要 JSON 输出能力。日常在线验证统一为真实 qwen3.7-flash，其他模型需当轮明确授权。

<a id="24-最小可运行配置与角色复用"></a>

首次参考 [模板](../config/models.example.toml) 创建 `config/models.local.toml`，已有本地配置继续使用。

```toml
[main]
provider = "dashscope"
model_id = "qwen3.7-flash"

[security]
provider = "dashscope"
model_id = "qwen3.7-flash"

[providers.dashscope]
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"
```

```bash
export DASHSCOPE_API_KEY='填入自己的 API Key'
```

地址与 Key 须匹配实际地域和业务空间。`api_key_env` 填环境变量名，省略 security 且无角色覆盖时可复用 main 配置。

配置路径按 `--model-config` → `DSCG_MODEL_CONFIG` → `config/models.local.toml` 选择。字段按显式参数 → `DSCG_MAIN_*`／`DSCG_SEC_*` 角色变量 → 角色 TOML → provider 共享设置及适用 fallback 解析，常用后缀为 MODEL_ID／PROVIDER／BASE_URL／API_KEY_ENV。

Key 按显式 api_key → 角色 API_KEY → api_key_env 指向值 → TOML api_key → 适用 main fallback 解析。TOML 中的 `$变量名` 不自动展开。仅输出公开配置来核对生效设置。

```python
from dscg.model_config import resolve_model_config
main = resolve_model_config()
security = resolve_model_config(prefix="DSCG_SEC", fallback=main)
print(main.public_dict())
print(security.public_dict())
```

### 请求兼容与诊断

DashScope 角色适配由公共客户端完成，baseline、screen、防御与 Dashboard 共用。思考和采样以 `dscg/model_config.py` 的适配及实际 `model_request` 记录为准；模型对象上的 temperature=0 不等于请求发送了 0。SDK max_retries=0，原生生成仍可能内部重试。

受支持的官方 DashScope 模型组合对 L2／L3 使用严格 JSON Schema，具体集合见 `DASHSCOPE_STRICT_SCHEMA_MODEL_IDS`；其他组合使用 JSON Object 并由宿主严格校验。接口拒绝时不自动降级或修补协议。API 错误只记录状态码、code、param 和角色计数，不保存凭证或完整 SDK 异常。

## 默认策略与辅助视图

`static-task-v354` 默认先提取原文片段 ID 静态视图，再编译全局工具权限。视图供主模型、L2 和 L3 共享，原始请求保留。模型名称和运行名称都不能选择策略。普通测试无需传 `--prompt-profile`。

`legacy` 仅作为显式单次授权对照，baseline 默认使用该配置并走原生循环。静态视图、工具授权与具体调用审计的区别见 [架构](architecture.md#l2-将完整可信任务编译为工具权限)。

## 工具 schema 与风险目录

工具名称、描述和参数 schema 来自实际后端注册函数；风险目录补充 effect／source／sink／sensitivity。它们解释工具能力，L2 另行决定本次任务的工具权限。

目录按 `--tool-metadata` → `DSCG_TOOL_METADATA` → `config/tools.<backend>.local.toml` → 可归属当前后端的通用 local → 后端内置目录选择。默认 AgentDojo 使用 [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml)。另一后端的通用 local 被跳过；归属不明的自定义目录需显式指定，缺项或非法分类在 runner 校验时失败。

| 字段 | 取值／作用 |
| --- | --- |
| effect | read、write、delete、financial、external_send，按实际副作用分类 |
| source | calendar、email、cloud、web、local |
| sink | none、external_recipient、public_output |
| sensitivity | public、internal、personal、secret |
| idempotent／reversible | 布尔，描述工具属性 |
| schema_version | 可省略，默认 dscg.tool-risk.v1 |

额外字段拒绝，external_send 须有非 none sink，delete 不能 reversible=true。risk_level／confirmation_required 由代码推导，不代表额外人工确认。名称像“读取”的工具也可能改变状态，须核对原生实现。标签不提供对象或参数级硬授权。

`python -m experiments.tools.generate_tool_metadata` 可离线生成当前后端专用 local，已有文件拒绝覆盖。自定义工具须先有真实注册函数和 schema，再补完整元数据；任务内目录变化使旧授权失效。直接调用 factory 的宿主须传入或注册元数据。

## 消融与默认值

| 控制 | 默认／入口 | 作用 |
| --- | --- | --- |
| input_isolation | true；factory/API | L1 规划视图隔离 |
| use_sandbox／authorization_precheck | true；CLI `--no-sandbox` 可关闭 | L2 编译和候选整批检查 |
| use_security_checker | true；CLI `--no-checker` 可关闭 | L3 语义审计 |
| planning_tool_view／delegated_tasks | true；CLI `--no-tool-view`／`--no-delegated-tasks` | 授权工具展示／有限明确委托 |
| l1_projection_mode | CLI off，factory/API projected | off 仍封装来源；shadow 仅记录投影机会 |
| audit_router_mode | CLI shadow，factory/API off | 两者均保留固定读取免审和其他 L3 审计 |
| audit_router_threshold | 0.70，范围 [0,1] | 诊断与身份绑定，不控制固定免审 |
| audit_retries | 0；CLI 可设 0/1 | 对 abstain 的有界重审，默认不重审 |
| completion_prompt | false | 额外完成提示，普通对比保持默认 |
| trace_level | summary；可选 standard/full | 诊断详细度 |
| authorization_input | v3；`DSCG_AUTHORIZATION_INPUT=v2` 作输入消融 | L2 紧凑工具输入 |
| audit_presentation | v3；`DSCG_AUDIT_PRESENTATION=v2` 作输入消融 | L3 单次证据呈现与参数字符上限 |

NoL2 还关闭授权工具视图和委托处理，要求 `--audit-router-mode off`。NoL3 默认 router off；两层均关时 L1 关闭。非 off 路由要求 L2 和 L3 均开启。NoL2 当前存在元数据加载缺失，尚未修复，见 [当前问题](framework_updates.md)。

<a id="l3直接阈值路由"></a>

## L3 读取路由

`sink-free-read-v4` 要求注册、授权、schema 有效、read、public/internal 和 sink=none。私人／秘密读取、有外部接收方的读取及效果动作仍审计，deny／abstain 阻断。混合批次只审计非免审部分，Monitor 保留整批绑定。router off 仍运行 L3，旧 artifact 参数已停用。

证据预算、长请求与委托来源界限见 [架构](architecture.md)。常规请求存在 2048 字符界限；默认 static 提取会检查长度，NoL2／纯读零调用／受限 host 路径仍有旧截断边界，不能据此宣称所有长任务得到完整处理。

## 排错

401／403／404 先核对实际模型、provider、空间地址和凭据来源。400／422 核对角色、tools 和 response_format。AUTH_CATALOG_CHANGED 核对任务内目录变化，DELEGATED_* 核对语法、长度与中介读取。reuse／fliter 拒绝应核对实际绑定，详见 [测试](benchmark.md)、[筛选](injection_precheck.md) 和 [结果文件](result_files.md)。
