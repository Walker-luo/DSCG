# 模型、工具与运行参数详解

本文供首次运行或更换模型/工具的测试者使用，对应当前three-layer-v3.1。所有命令从DSCG/执行，默认ipi已激活。模型配置和工具风险目录是宿主输入；模型返回、网页正文或工具错误不能改写它们。

## 1. 测试者需要准备哪些信息

| 信息 | 用途 | 从哪里获取 | 标准AgentDojo测试是否要自行准备 |
| --- | --- | --- | --- |
| 模型ID、API地址和API Key | 连接主模型及可选的独立审计模型 | 模型服务商控制台、模型列表与OpenAI兼容API文档 | 是；可以两种角色共用一个模型服务 |
| 工具名称、描述、输入参数schema和真实实现 | 让规划器知道如何调用工具；运行时校验参数并执行 | 已安装AgentDojo的suite.tools；自定义工具则来自宿主实现/接口定义 | 标准四场景已提供，不必手写参数表 |
| 工具风险元数据 | 让L2/L3识别读取、修改、外发与敏感性，选择检查路径 | 仓库内置审核目录；自定义工具需宿主按实际行为补充 | 默认内置，无需另下载或复制 |
| 用户任务、注入任务和初始模拟环境 | 定义任务事实、攻击目标和评分环境 | AgentDojo v1.2任务套件 | 默认已有；普通partial无需外部任务清单 |
| 宿主授权profile、任务文件reader、L3校准artifact | 有界授权扩展、文件适配或选择性审计 | 测试者有针对性地维护/验证 | 均可选；普通比较不要求提供 |

**工具参数schema与风险元数据是两份不同的信息。** `send_email`的参数schema说明收件人/标题/正文如何传入；风险元数据说明它会把数据发给外部接收者。填写风险TOML不会创建该工具，也不会实现邮箱连接。标准AgentDojo动作运行在模拟环境，通常不需要真实邮箱、Slack、网盘或银行凭证；换成真实服务的自定义工具时才由宿主负责接口和凭证。

## 2. 主模型和审计模型

### 2.1 两种角色及能力要求

- `[main]`：主模型规划/最终回答，以及L2任务开始时的授权编译。攻击评测还会有攻击生成/预检，按实际运行计费。
- `[security]`：L3当前动作语义审计，可以与main同模型/同服务，也可以独立配置。它不一定是小模型，不是需要训练的分类器。
- 主模型接口需要支持当前Chat Completions消息格式、tools/function calling，以及L2使用的JSON输出；审计接口需要支持JSON输出。仅有普通聊天可用并不能证明工具循环和授权/审计协议可用。
- 当前主规划、授权、审计使用temperature=0；DeepSeek设置reasoning_effort="none"，因为AgentDojo0.1.35不保留reasoning_content的完整工具回合。两项由源码设置，**不是**models.local.toml中的可调字段；仅写入temperature/max_tokens等额外键不会让流水线采用它们。

连接参数由 [model_config.py](../dscg/model_config.py)解析，授权/审计请求由 [defended.py](../dscg/pipelines/defended.py)构造。

### 2.2 models.local.toml字段

| 字段 | 含义与填写方法 | 对应环境变量 |
| --- | --- | --- |
| `provider` | 服务商标识，用于默认endpoint/Key变量和兼容设置，如deepseek、dashscope、openai、ollama；自定义兼容服务可显式用custom并填写base_url | DSCG_MAIN_PROVIDER / DSCG_SEC_PROVIDER |
| `model_id` | 服务API识别的模型ID，不是自行起的实验名称；从服务方模型列表复制并确认账号权限 | DSCG_MAIN_MODEL_ID / DSCG_SEC_MODEL_ID |
| `base_url` | OpenAI兼容API的根地址，应包含服务要求的v1/compatible-mode等路径；不填写网页聊天地址或完整/chat/completions地址 | DSCG_MAIN_BASE_URL / DSCG_SEC_BASE_URL |
| `api_key_env` | **保存Key的环境变量名称**，例如DEEPSEEK_API_KEY；不是Key本身，TOML不会替你设置环境变量 | DSCG_MAIN_API_KEY_ENV / DSCG_SEC_API_KEY_ENV |
| `api_key` | 实际Key；支持本地TOML或显式API输入，共享配置优先用api_key_env。public_dict不输出它 | DSCG_MAIN_API_KEY / DSCG_SEC_API_KEY |

常用预设在源码中：deepseek→DEEPSEEK_API_KEY、dashscope/qwen→DASHSCOPE_API_KEY、openai→OPENAI_API_KEY；另外支持moonshot/kimi、zhipu/glm、siliconflow、groq和ollama。预设只填默认连接，不保证每个模型都支持本流水线。ollama默认本地11434/v1且提供SDK所需占位Key；模型须已由测试者安装并具备相应能力，不会自动下载。

### 2.3 模型信息怎么获取

| 服务 | 获取步骤与官方说明 | 仓库默认连接示例 |
| --- | --- | --- |
| DeepSeek | 按[官方API认证说明](https://api-docs.deepseek.com/api/deepseek-api/)到控制台创建Key；从[Chat Completions参考](https://api-docs.deepseek.com/api/create-chat-completion/)核对model、tools与JSON支持 | provider=deepseek，base_url=https://api.deepseek.com；模板使用deepseek-flash，运行前确认账号可用 |
| 阿里云百炼/Qwen | 按[获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)选择地域/业务空间；按[首次调用文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)核对模型ID和OpenAI兼容地址 | provider=dashscope；模板qwen-plus、https://dashscope.aliyuncs.com/compatible-mode/v1；其他地域需按官方接入信息修改 |
| 其他兼容服务 | 从该服务官方API文档获取完整base_url、实际model_id与Key；不要只依据模型品牌猜endpoint | 显式填写provider/model_id/base_url和独立Key变量 |

百炼Key、模型和endpoint有地域/业务空间范围，不能混用；以[当前官方Key说明](https://help.aliyun.com/zh/model-studio/get-api-key)为准。官方链接核查于2026-10-13，模型可用性以后仍应由测试者确认。

### 2.4 最小可运行配置与角色复用

复制 [models.example.toml](../config/models.example.toml)到被Git忽略的config/models.local.toml，填写自己的连接信息。下面是单服务示例：

```toml
[main]
provider = "deepseek"
model_id = "deepseek-flash"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
```

```bash
export DEEPSEEK_API_KEY='填入自己的API Key'
```

省略security角色设置、且没有DSCG_SEC_*覆盖时，审计角色通过fallback复用主模型配置。**仓库模板本身包含独立的[security]：仅不填审计Key不会自动变成单模型。** 如果希望复用，应移除该段并检查现有SEC环境覆盖；不要清空其他实验仍需要的配置。

独立审计模型可追加：

```toml
[security]
provider = "dashscope"
model_id = "qwen-plus"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
api_key_env = "DASHSCOPE_API_KEY"
```

然后设置DASHSCOPE_API_KEY。换成不同provider/endpoint时不要沿用另一服务的Key。`[providers.<provider>]`可设置该provider共享的base_url/api_key_env/api_key默认值；main/security角色自己的设置更优先。security兼容别名sec/audit按源码顺序选用，普通配置建议统一写security。

### 2.5 配置优先级与实际生效检查

路径：显式config_path（partial CLI --model-config）→DSCG_MODEL_CONFIG→config/models.local.toml；相对路径按项目根解析。

model_id/provider/base_url/api_key_env等字段通常按：显式函数参数（网页填写值也作为参数）→对应角色DSCG_MAIN_*或DSCG_SEC_*→角色TOML→provider共享设置/预设及兼容默认值。secondary还会按相同模型等条件应用main fallback，因此不是把两段TOML简单拼接。

**实际Key的优先级另列**：显式api_key→角色DSCG_*_API_KEY→api_key_env指向的变量值→角色/provider TOML中的api_key→适用的main fallback；ollama最后可使用占位Key。配置文件内写"$DEEPSEEK_API_KEY"不会自动展开为环境变量，应使用api_key_env。

以下Python示例可在项目根的Python交互环境执行，或保存为临时脚本后运行。无需模型调用即可查看解析结果；只打印public_dict，不要直接打印整个配置对象或本地文件：

```python
from dscg.model_config import resolve_model_config

main = resolve_model_config()
security = resolve_model_config(prefix="DSCG_SEC", fallback=main)
print("main:", main.public_dict())
print("security:", security.public_dict())
```

baseline/NoChecker不需要建立审计客户端；上述两角色检查用于完整框架。有Key也不表示联网鉴权或模型能力已经验证，之后由测试者用新run名做小范围工具/JSON检查。网页填入的连接参数、本地TOML与终端环境可能不同，最终以结果的resolved配置/run_manifest为准；服务启动后才设置的环境变量不会自动进入已有进程。

## 3. 工具参数：查看什么、在哪里获取

真实注册工具具有name、description、parameters和run；输入schema由AgentDojo函数定义/类型标注等生成。schema说明属性类型、required字段、default/枚举等；实际函数实现才决定副作用。工具描述由宿主提供，L2编译、主模型工具视图与L3宿主描述都会使用。

以下示例**只查看注册定义，不执行send_email、不调用模型**：

```python
import json
from agentdojo.task_suite import get_suite

suite = get_suite("v1.2", "workspace")
tools = {tool.name: tool for tool in suite.tools}
print("available:", sorted(tools))
tool = tools["send_email"]
print("description:", tool.description)
print(json.dumps(tool.parameters.model_json_schema(), ensure_ascii=False, indent=2))
```

其他场景将workspace换成travel、banking或slack；选用get_file_by_id等工具时应从实际schema读取file_id等参数，而不假设所有文件工具都接收file_path。required表示调用时必须提供；schema不包含未来任务的真实收件人、文件ID或账单金额，这些值由任务/环境及必要读取获得。

若要查看宿主实现，可用inspect.getsource(tool.run)，或在已安装AgentDojo的suite工具模块中读源码；与当前安装版本匹配，不能只照抄网上另一版本的参数表。description/参数schema不是输出schema，也不能据其推断完整事实来源或对象权限。

## 4. 工具风险元数据：作用、字段及覆盖

### 4.1 加载位置

标准partial/dashboard runner自动加载：显式--tool-metadata/网页路径→DSCG_TOOL_METADATA→已有config/tools.local.toml→内置 [tools.agentdojo-v1.2.toml](../config/tools.agentdojo-v1.2.toml)。显式路径不存在会报错，不偷偷回退；本地文件存在时不会因缺项自动补全内置目录。选中目录里未分类/非法的runtime工具按critical并在默认L2阻断。

直接使用factory API时，需传入tool_metadata=load_tool_metadata()或由宿主在runtime注册元数据；factory本身不会自动读这个文件。工具名必须匹配实际注册name。runner传全suite目录后会按当前runtime筛选；自写set_tool_metadata(runtime, ...)应先筛选当前runtime工具，否则未注册名称会报错。

### 4.2 必需字段

| 字段 | 允许值 | 对框架的实际意义 |
| --- | --- | --- |
| effect | read / write / delete / financial / external_send | 真实动作类型；影响默认读取授权及风险/审计路径，不按名字里含get/read就推断 |
| source | calendar / email / cloud / web / local | 工具接触的来源域；是宿主分类，不认证返回事实；当前schema没有单独的slack枚举 |
| sink | none / external_recipient / public_output | 是否有外部接收方/公共输出；影响风险与免审资格。none不表示任意目标安全 |
| sensitivity | public / internal / personal / secret | 信息敏感度；个人/秘密读取不能当公开免审 |
| idempotent | true / false | 宿主声明重复相同操作是否改变预期结果；是L3新增internal-read路由资格之一，不提供exactly-once保证 |
| reversible | true / false | 宿主是否认为副作用可逆；仅记录属性，当前没有自动撤销/恢复机制 |
| schema_version | 可选，默认dscg.tool-risk.v1 | 当前风险分类schema版本，其他版本拒绝 |

布尔值使用TOML true/false，不是字符串。external_send必须带非none sink；delete不能标reversible=true。risk_level、deterministic_read、confirmation_required、audit_required由源码推导，不是应手工填写的额外字段；多余字段会无效。confirmation_required不是要求测试者逐动作点击确认的网页流程，也不替代用户任务授权。

```toml
[tools.send_email]
effect = "external_send"
source = "email"
sink = "external_recipient"
sensitivity = "personal"
idempotent = false
reversible = false
```

例子：get_unread_emails会标记邮件已读，所以内置effect=write；send_email和带参会人通知的日历修改是external_send。必须根据实现/副作用核对分类。

公开免审来自有效read+public+sink=none的既有规则；idempotent不是这个旧规则的独立硬条件。internal读取仍默认送L3，只有启用并通过L3纯算法校准硬门才能新增免审。风险级别也不是最终allow/deny：Monitor保留已授权sink-free读取的deny例外，详见 [框架边界](../README.md#读取例外开销与当前边界)。

### 4.3 生成、检查与新增工具

默认已内置目录，普通比较无需生成本地文件。需要独立维护覆盖时：

```bash
python -m experiments.generate_tool_metadata --output config/tools.local.toml
```

该命令核对AgentDojo0.1.35/v1.2工具覆盖，再**复制仓库审核目录**，不调用模型、不通过训练或工具名字自动猜分类；已有目标文件默认拒绝覆盖。--force会替换已有本地分类，不应拿它代替人工核对自定义工具。

只读检查所用目录（不生成文件、不调用模型）：

```python
from experiments.generate_tool_metadata import validate_catalog

catalog = validate_catalog()  # 校验内置AgentDojo完整目录
print("classified tools:", len(catalog))
# 若实际指定了完整本地AgentDojo目录，改用validate_catalog("config/tools.local.toml")
```

自定义子集/新增工具不能直接假定通过完整AgentDojo目录检查。自定义接入顺序是：宿主实现并注册工具→从当前函数定义取得schema/描述→补六项风险属性→通过set_tool_metadata/register_tool_metadata注册检查→新可信任务编译权限→执行仍经precheck/L3/Monitor/ticket。注册和填写元数据都不等于用户授权；任务中途更改目录使旧授权失效，不从tool正文注册新工具。

## 5. 运行控制：默认值、用途及设置入口

下表列出的 partial CLI 开关也适用于全量 `experiments.run_benchmark`；两者共用执行与报告流程，仅默认任务范围和输出根不同。另有仅 partial 支持的 `--suites travel banking slack`，可在优化时跳过 workspace，默认仍跑四场景，示例见 [评测指南](./evaluation.md#对照与输出)。完整框架/baseline 全量命令见 [全量测试指南](./full_benchmark.md)。`use_sandbox` 等仅 API/网页控制仍不因此新增同名 CLI。

| 控制 | 默认 | 可设置入口 / 作用 |
| --- | --- | --- |
| use_sandbox | true | factory/API、网页；L2工具授权，关掉不创建任务文件授权；partial普通默认不提供同名CLI |
| input_isolation | true | factory/API、网页；L1来源视图；partial普通默认开 |
| l1_projection_mode | projected | factory/API、partial `--l1-projection-mode off/shadow/projected`；网页默认projected，无独立选择器；off保留原来源封装，关闭L1则有效off |
| authorization_precheck | true | factory/API、网页；L3之前本地整批权限检查；NoL2无效 |
| planning_tool_view | true | factory/API、网页、partial --no-tool-view；关掉展示完整目录，执行授权仍检查 |
| delegated_tasks | true | factory/API、网页、partial --no-delegated-tasks；有界明确执行文件/唯一邮件/指定网页任务，不把普通返回变成任务 |
| use_security_checker | true | factory/API、网页、partial --no-checker；整个L3语义审计开关 |
| audit_router_mode | off | factory/API、partial --audit-router-mode off/shadow/selective；off仍运行原L3，shadow观察，selective需兼容校准artifact |
| audit_router_artifact | None | factory/API、partial --audit-router-artifact PATH；独立标签/分组校准产生，不由模型置信度自动生成；默认不需要 |
| audit_retries | 0 | factory/API、partial --audit-retries 0/1；仅语义abstain有界重审，普通比较保持0，不是SDK传输重试设置 |
| completion_prompt | false | factory/API、partial --completion-prompt；历史可选提示，当前普通比较保持关闭 |
| trace_level | summary | factory/API、网页、partial --trace-level；standard逐条紧凑记录，full压缩诊断增加序列化/写盘成本 |

这些控制不会从模型连接TOML读取。NoL2同时关闭前置检查、授权工具视图与委托展开；L2/L3均关时L1也关闭。shadow/selective要求L2和L3同时开启，baseline使用原生循环。L3真实阈值/epsilon/delta/grid仍待独立数据与选择，见 [README待决定项](../README.md#l3-仍需确定什么)，不能用一个自填tau替代兼容artifact。authorization_profile/delegated_task_reader是受信host API对象，不是普通测试必填项或TOML新增段，详见 [L2方案](../workshop/L2_opt.md)。

--model-config/--tool-metadata是输入配置路径；--name标识实验；--results-dir是输出根；--task-manifest仅用于显式冻结任务ID，默认无需导入。修改任何有效配置/策略后使用新name，--force-rerun不绕过旧manifest绑定。成本比较采用新name并force-rerun，仍核查API usage/样本分母，不能只凭flag保证可比。

L1投影仅支持原生银行月支出请求与完整Transaction返回，最多32768 UTF-8字节、500行；原生callable/code/schema和元数据不兼容、错误/截断或未知字段均回退。无需额外模型、训练、TOML段或外部profile清单。模式/适配器身份影响缓存和L3 artifact兼容，切换用新run名；细节见 [L1说明](../README.md#l1-优化任务限定的结构化投影)。

审计输入v2最多选择当前任务的8条调用—返回对：保留最近4条，再匹配候选参数/用户指定资源补充较早证据；最多考察最近256条当前任务返回。工具正文、规范化调用参数与错误共享8192字符预算，单条调用参数最多1024字符，裁剪显式标记。删除候选且用户仅需文件大小比较时的严格列表适配最多131072 UTF-8字节、512行，保留全部元数据并显式省略正文；失败回退有界原文。工具描述512字符、任务2048字符、动作历史32条，timeout30秒；委托源正文1536字符、规范化T_eff2048字符、序列化返回16384字符。结构化解析最多16层，错误最多512字符，与参数共同占用单条1024字符配额；有序复合委托不自动展开，避免提前读取后续任务源。它们是当前源码边界，普通CLI没有--audit-window/--max-task-chars等参数，不在TOML虚构配置项。

## 6. 常见问题与首次检查顺序

| 现象 | 优先检查 |
| --- | --- |
| Missing API key | api_key_env填的是变量名且该变量在启动进程前已设置；复制模板后security是否仍选另一provider |
| 401/403 | Key所属服务/地域/权限与endpoint、model_id一致；检查服务控制台。离线解析成功不代表鉴权成功 |
| 404/model not found | model_id是真实API ID，base_url含正确兼容路径，不是网页地址或追加了完整/chat/completions |
| 400/JSON或工具回合失败 | 主模型tools、tool角色回合、JSON response_format兼容性；DeepSeek是否用了当前none设置；不要将协议错误算防住攻击 |
| METADATA_MISSING / METADATA_INVALID | 实际选中的工具目录、覆盖、六个字段/布尔/枚举/多余字段；本地目录是否遮蔽内置分类 |
| AUTH_CATALOG_CHANGED | schema、描述、callable/依赖或元数据在任务内改变，旧授权不能继续；用新可信任务边界，不把错误文本作为补权依据 |
| AUTH_CONSTRAINT_CONFLICT | host profile禁止能力与必要读取闭包冲突；不是简单多加权限，需核对独立任务/规则 |
| DELEGATED_* | 有限执行句式/限制、注册reader、源是否唯一且成功监控读取、1536/2048/16384长度；仅总结文件不会展开权限 |
| router设off仍有审计成本 | off只关新增免审路由；关闭整个L3需NoChecker对照，不能混淆两种实验 |

先完成无需API的配置解析/schema/风险目录检查，再由测试者运行有限的干净工具任务与JSON协议检查，最后做匹配attack对照。以上离线检查只确认字段/覆盖，不证明模型理解正确、任务完成或安全有效。其他攻击选择、结果目录和评分口径见 [评测指南](./evaluation.md)。
