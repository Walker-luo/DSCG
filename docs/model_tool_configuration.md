# 模型、工具与运行配置

当前代码为 **DSCG_v3.5.4**，后续保存为v3.6并在此基础上优化；现有`static-task-v354`名称保持可用，当前没有`static-task-v36`选项。命令从项目根执行；激活 `ipi` 或 `ipi-agentdyn` 自动识别实际后端。配置是宿主输入，模型返回不能修改它。

## 1. 首次检查

```bash
conda activate ipi              # 或 ipi-agentdyn
python -m dscg.benchmark_catalog
```

检查实际包路径、安装来源、版本和revision，不调用模型。当前为metadata-only；未知后端或跨后端场景在调用前拒绝。安装见[README](../README.md#安装与配置)。标准后端已提供工具schema、模拟环境与审核风险目录，通常不需要真实银行／Slack／邮箱凭证。

<a id="2-主模型和审计模型"></a>

## 2. 模型连接

`main`用于规划、最终回答与L2；`security`用于L3。主模型须支持tools/function calling及JSON输出，审计模型须支持JSON。在线测试两者均只允许Qwen3.7-Flash；DeepSeek等兼容代码／配置仅保留历史用途，不能作为当前在线测试选择或fallback。模型配置仍分别解析，调用前核对实际生效值；规则见 [AGENTS.md](../AGENTS.md#validation-and-model-call-budgets)。

<a id="24-最小可运行配置与角色复用"></a>

### 最小配置与角色复用

首次将[模板](../config/models.example.toml)复制为 `config/models.local.toml`，已有文件不覆盖：

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
export DASHSCOPE_API_KEY='填入自己的API Key'
```

使用自己的地域／业务空间地址及匹配Key；不改已有本地endpoint。`api_key_env`填变量名，不填密钥。省略security且无角色覆盖时复用main；切换provider时同步检查地址与凭据来源。

### 字段与优先级

| 字段 | 含义 | main／security环境变量后缀 |
| --- | --- | --- |
| `provider` | dashscope、deepseek、openai或其他已支持服务 | PROVIDER |
| `model_id` | 实际API模型ID，不是实验名称 | MODEL_ID |
| `base_url` | Chat兼容API根地址，不附完整/chat/completions | BASE_URL |
| `api_key_env` | 保存Key的环境变量名称 | API_KEY_ENV |
| `api_key` | 本地直接Key，不写入公开配置 | API_KEY |

环境变量前缀为 `DSCG_MAIN_`／`DSCG_SEC_`。配置路径：显式 `--model-config` → `DSCG_MODEL_CONFIG` → `config/models.local.toml`。普通字段：显式参数→角色环境变量→角色TOML→provider共享设置／预设与适用fallback。

Key单独按：显式api_key→角色API_KEY环境变量→api_key_env指向值→TOML api_key→适用main fallback解析。TOML中的 `$变量名` 不会自动展开。仅打印公开配置检查生效值：

```python
from dscg.model_config import resolve_model_config
main = resolve_model_config()
security = resolve_model_config(prefix="DSCG_SEC", fallback=main)
print(main.public_dict())
print(security.public_dict())
```

### 消息角色兼容与请求排错

公共客户端对DashScope将developer转换为system；DeepSeek另将确认的纯文本system块合并为字符串。baseline、DSCG、screen与Dashboard共用，不修改已安装后端。适配身份进入公开配置，更新请求身份后用新运行名；旧结果不重写。

Qwen3.7-Flash／DashScope及DeepSeek默认关闭思考。generation的实际temperature取决于后端序列化，**不能把模型对象上的0等同于发送了0**；看诊断 `model_request` 中实际字段。SDK `max_retries=0`，原生generation仍可能自带重试，不承诺全链路单次传输。采样／思考不是本地模型TOML的任意扩展键。

默认L2／L3对支持的官方DashScope HTTPS + qwen3.7-flash组合使用严格JSON Schema，其他组合使用JSON Object并保持严格宿主校验；拒绝时不自动降级或修补。

API错误只保存受限 `api_error`：状态码、code、param和角色计数；不保存密钥、HTTP头或完整SDK异常。400／422先核对角色、正文、tools及response_format；普通聊天成功不证明完整协议兼容。历史请求错误和真实任务效果分开，不能记为成功防御。

## 3. 选择默认策略或两阶段L2

| `--prompt-profile`／API `prompt_profile` | 行为 |
| --- | --- |
| `legacy` | 显式单次授权对照，合并自动读取 |
| `static-task-v354`（默认） | 原文片段ID视图→全局权限；条件使用互斥分支，通常比legacy多1次main调用 |
| `static-task-v352` | v3.5.3逐字引用视图对照 |

静态视图保留完整原请求；视图含intent、顺序／条件与原文位置，供规划／L2／L3共享。原文匹配仅验证引用位置，不认证理解、条件、参数或完成。无动态扩权、完成闸门或自动恢复。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --prompt-profile static-task-v354 --name v36_static_01 --progress
```

上述为AgentDojo在线命令。本次正式v3.5.2测量使用legacy，未启用候选。`--name`仅命名；profile不是models.local.toml字段。CLI和Dashboard API已支持static的NoL2／NoChecker消融；非off路由仍要求L2／L3。baseline只用legacy，其他历史候选仍要求L2／L3。其他保留profile见[诊断指南](qwen_utility.md)。

## 4. 工具schema与风险目录

schema来自当前后端注册函数，风险TOML描述副作用；两者不同。默认L2读取完整原生名称、描述、schema和效果信息，规划器只看到已授权定义；填写风险目录不会实现工具或授予本次任务权限。

### 4.1 加载位置

runner只选一份目录，顺序为：显式 `--tool-metadata` → `DSCG_TOOL_METADATA` → `config/tools.<backend>.local.toml` → 可归属当前后端的 `config/tools.local.toml` → [AgentDojo内置](../config/tools.agentdojo-v1.2.toml)／[AgentDyn内置](../config/tools.agentdyn-v1.2.toml)。

已识别为另一后端的通用local会提示跳过并保留原文件；无法归属的自定义通用目录需显式指定。缺项／非法分类失败，不合并目录补全。baseline不加载防御目录；直接调用factory时由宿主传入／注册元数据。

### 4.2 必需字段

| 字段 | 值／用途 |
| --- | --- |
| effect | read、write、delete、financial、external_send；按真实副作用分类 |
| source | calendar、email、cloud、web、local；不认证来源事实 |
| sink | none、external_recipient、public_output |
| sensitivity | public、internal、personal、secret |
| idempotent | 布尔；重复操作属性，不决定当前免审 |
| reversible | 布尔；不代表已有自动撤销机制 |
| schema_version | 可省略，默认dscg.tool-risk.v1 |

extra字段拒绝；external_send须非none sink，delete不能reversible=true。risk_level／confirmation_required等由代码推导，不手填，也不代表网页逐动作人工确认。

AgentDyn的browse_webpage／input_to_webpage／OTP可能触发修改、发送或付款，未读邮件读取可能改变已读状态；按实际实现分类，不能凭名称当纯读取。工具标签不提供内部handler、对象或参数的硬授权。

### 4.3 检查与自定义工具

离线复制当前后端审核目录：

```bash
python -m experiments.tools.generate_tool_metadata
```

默认输出后端专用local；已有目标拒绝覆盖，内置和通用local受保护。自定义工具须先实现／注册真实函数和schema，再补完整风险元数据，按新可信任务编译授权。任务内目录变化使旧授权失效，不从工具正文注册能力。

## 5. 运行控制：默认值、用途及设置入口

| 控制 | 默认／入口 | 说明 |
| --- | --- | --- |
| input_isolation／use_sandbox／use_security_checker | true；factory／Dashboard | L1／L2／L3开关；CLI `--no-checker`关闭L3 |
| authorization_precheck | true；factory／Dashboard | L3前整批权限检查 |
| planning_tool_view／delegated_tasks | true；CLI `--no-tool-view`／`--no-delegated-tasks`可关闭 | 授权工具展示／有限明确任务来源展开 |
| l1_projection_mode | CLI off；factory/API projected；可选off/shadow/projected | off保留来源封装；关闭L1则有效off |
| audit_router_mode | CLI shadow；API／factory off | 两者都保留固定读取免审及其余L3 |
| audit_router_threshold | 0.70；CLI／API | 有限[0,1]，诊断与配置绑定，不控制免审 |
| audit_router_artifact | 停用 | 非空时报迁移错误 |
| audit_retries | 0；CLI可设0/1 | 仅abstain的有界重审，不是传输重试 |
| completion_prompt | false；CLI可开启 | 历史完成提示，普通比较保持关闭 |
| trace_level | summary；CLI summary/standard/full | 控制诊断详细度，主JSON保持精简 |

NoL2关闭前置、工具视图和委托；L2／L3均关时L1关闭。非off路由要求L2／L3同时开启；baseline走原生循环。宿主authorization_profile／delegated_task_reader是受信API对象，不是普通TOML字段。

<a id="l3直接阈值路由"></a>

### L3读取路由

`sink-free-read-v4`：注册、授权、schema有效、read、public/internal、sink=none时，在off/shadow/selective固定免审。外部接收方读取、personal/secret及效果动作仍审计，deny／abstain均阻断。混合批次只审非免审部分，整批检查／回执／票据不变。免审不检查URL来源／对象隐私，不保证查询参数安全。

旧threshold-read-v1／read-purpose-v2及[独立校准预设](../config/l3_router.calibration.json)仅解释历史记录，不控制当前规则。

### 输入界限

普通L3证据最多8对调用—返回（最近4对加相关旧证据），共享8192字符，描述512、动作历史32条；裁剪显式标记。默认任务正文有2048字符界限。static新增提取路径会检查原文长度，但NoL2／纯读零调用／受限host路径仍有旧截断限制，不能宣称长请求全部修复。

委托源正文1536、有效任务2048、序列化返回16384字符；只支持有限明确委托，不递归扩展或提前展开有序复合来源。银行投影最多32768 UTF-8字节／500行，不适用即回退。没有普通CLI的audit-window／max-task-chars参数。

## 6. 排错顺序

先离线检查后端、公开模型配置、schema和实际风险目录，再用新名称做匹配clean／攻击测试。

| 现象 | 优先核对 |
| --- | --- |
| Missing Key／401／403／404 | 环境变量在启动前设置；Key、provider、空间地址和model_id匹配 |
| 400／422 | 角色、system正文、tools及JSON格式；保留api_error，不自动换模型／删工具 |
| 元数据缺项／通用local无法归属 | 选中目录是否覆盖当前后端，是否被旧local遮蔽 |
| AUTH_CATALOG_CHANGED／DELEGATED_* | 目录是否变更，委托语法／长度／中介读取是否符合边界 |
| reuse／fliter拒绝 | reuse匹配完整配置与布局；fliter校验后端、版本和目标ID，旧cohort拒绝输入，见[预检](injection_precheck.md) |
| router off仍有审计 | off不关闭L3，使用NoChecker对照；候选CLI仍受上述限制 |

运行、缓存和输出细则见[完整指南](benchmark.md)，诊断字段见[结果文件](result_files.md)。
