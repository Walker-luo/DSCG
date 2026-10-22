# 模型、工具与运行参数详解

本文供首次运行或更换模型/工具的测试者使用，对应当前three-layer-v3.3。所有命令从DSCG/执行；激活`ipi`使用AgentDojo，激活`ipi-agentdyn`使用AgentDyn，相同运行入口自动识别实际安装。模型配置和工具风险目录是宿主输入；模型返回、网页正文或工具错误不能改写它们。

两个独立环境的安装入口是 [environment.yml](../environment.yml) 与 [environment-agentdyn.yml](../environment-agentdyn.yml)。保留已有环境和本地模型配置；运行前可离线自检：

```bash
conda activate ipi              # 或 conda activate ipi-agentdyn
python -m dscg.benchmark_catalog
```

离线检查核对实际导入路径、安装来源、版本和固定revision，再显示场景；不遍历源码、不计算后端哈希。两份[AgentDojo锁](../config/agentdojo.lock.json)、[AgentDyn锁](../config/agentdyn.lock.json)保留历史源码证据，当前仅使用元数据。新记录verification_mode=metadata_only、runtime_variant=unverified。未知来源/revision/路径冲突仍拒绝；不要求新增backend参数。

## 1. 测试者需要准备哪些信息

| 信息 | 用途 | 从哪里获取 | 标准后端测试是否要自行准备 |
| --- | --- | --- | --- |
| 模型ID、API地址和API Key | 连接主模型及可选的独立审计模型 | 模型服务商控制台、模型列表与OpenAI兼容API文档 | 是；可以两种角色共用一个模型服务 |
| 工具名称、描述、输入参数schema和真实实现 | 让规划器知道如何调用工具；运行时校验参数并执行 | 当前后端的suite.tools；自定义工具则来自宿主实现/接口定义 | AgentDojo四场景或AgentDyn三场景已提供，不必手写参数表 |
| 工具风险元数据 | 让L2/L3识别读取、修改、外发与敏感性，选择检查路径 | 仓库内置审核目录；自定义工具需宿主按实际行为补充 | 默认内置，无需另下载或复制 |
| 用户任务、注入任务和初始模拟环境 | 定义任务事实、攻击目标和评分环境 | 当前锁定后端的native v1.2任务套件 | 默认已有；普通partial无需外部任务清单 |
| 宿主授权profile、任务文件reader | 有界授权扩展、文件适配或选择性审计 | 测试者有针对性地维护/验证 | 均可选；普通比较不要求提供 |

**工具参数schema与风险元数据是两份不同的信息。** `send_email`的参数schema说明收件人/标题/正文如何传入；风险元数据说明它会把数据发给外部接收者。填写风险TOML不会创建该工具，也不会实现邮箱连接。两个后端都在模拟环境执行动作，通常不需要真实邮箱、GitHub、购物、Slack或银行凭证；换成真实服务的自定义工具时才由宿主负责接口和凭证。

## 2. 主模型和审计模型

Qwen banking/Slack的协议诊断、`--prompt-profile`候选、日志字段及配对测试见[效用诊断指南](./qwen_utility.md)。新精简候选用 `--prompt-profile task-alignment-v1`；该开关属于防御策略，不是模型TOML参数，默认legacy，不更换主/安全模型。JSON输出可用仍需严格字段校验，普通聊天成功不代表审计协议稳定。

### 消息角色兼容与请求排错

DSCG公共客户端对实际provider=dashscope或deepseek的同步`chat.completions.create`分别启用`dashscope-system-v1`和`deepseek-system-text-v1`：把结构化developer消息转换成system。DeepSeek还要求system正文为字符串，因此仅将完全由`{type:text,text:<字符串>}`组成的文本块按原顺序拼接；不识别的块保留原状，由服务端明确校验。DashScope的正文格式不变。两种适配均保留消息文本/顺序、user/assistant/tool角色、工具schema、temperature和其余请求参数；不原地修改消息，不新增重试或降级。其他provider保持原客户端。两套后端的baseline、DSCG、GOAL预检、screen和Dashboard均从此入口创建客户端；不需改site-packages。对应[百炼Chat系统消息协议](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-chat-completions/)和[DeepSeek Chat Completions消息结构](https://api-docs.deepseek.com/api/create-chat-completion/)，不涉及Responses API。

`chat_request_adapter`由宿主计算，写入DashScope或DeepSeek主/审计模型的公开配置，进入原有manifest、cohort测量配置和路由身份。更新后实际测量缓存需匹配请求身份，否则使用新run名。冻结cohort的名单兼容只比较主模型ID/provider、后端/版本及所选任务，并校验名单自身摘要；不再以adapter、endpoint或思考设置差异要求重新预检，也不重读原预检证据。screen自身续跑仍保留原证据流程。原名单与证据不改写。当前L3使用直接阈值；旧校准预设仅保留作离线研究。

已核对`results/partial_benchmark/agentdyn/qwen3.7-flash_test`：9个攻击/场景组均在第一个GOAL预检的首个generation请求失败，L2成功、L3未触发，没有81条有效计分轨迹。本机原生消息捕获为AgentDojo system/user、AgentDyn developer/user；角色差异与失败位置一致。旧文件未保存400详情，因此不能排除服务端其他校验错误；不把它标为TSR=0或防御成功。

DeepSeek Flash在AgentDyn的`deepseek-flash_test`记录显示9组均于首个GOAL预检返回422，安全诊断计数为developer/user各1条；此前的Qwen适配不作用于DeepSeek。AgentDyn还把该受信任消息正文序列化为文本块数组，而DeepSeek Chat文档要求system正文是字符串。当前按DeepSeek Chat协议转换为system/user，并把可确认的纯文本块合并为字符串。422未暴露受限参数名，不能把原错误唯一归因于角色或正文类型；离线模拟不能证明真实服务已接受完整工具schema、JSON模式及后续请求。原目录保留，服务器用新运行名小范围复测；若仍422，检查新诊断里的实际角色计数和参数。

新API失败诊断`api_error`只含schema版本、http_status、provider_error_code、provider_error_param和request_role_counts；code/param采用受限字符集和长度，角色仅计数。CLI输出同一受限结构，执行记录、attack_manifest、failure_cases.jsonl及screen的attempt.json保留；TokenTracker各失败phase记录last_api_error。默认不保存请求正文、响应message、凭据或完整SDK异常。Dashboard API失败仅输出受限结构并尽力保存execution_error.json，不推造成功指标。

服务器更新后先做小批量clean（以下命令会请求真实模型；本轮离线验收没有执行，名称替换为未使用的新值）：

```bash
conda activate ipi-agentdyn
python -m experiments.run_partial_benchmark --clean --baseline --name qwen_rolefix_clean_base_01
python -m experiments.run_partial_benchmark --clean --name qwen_rolefix_clean_dscg_01
# 两组各9项，先确认无请求级400，再恢复攻击测量
python -m experiments.run_partial_benchmark --attack typical --name qwen_rolefix_attack_01
```

不使用旧test目录做reuse/force-rerun。若仍400或422，先查看新api_error的状态/code/param/角色计数：system/user只说明角色已适配，不能证明工具schema、JSON输出及服务部署都兼容。保持原错误/费用分母并按具体参数继续定位，不自动删工具、改模型或放宽审计。

### 2.1 两种角色及能力要求

- `[main]`：主模型规划/最终回答，以及L2任务开始时的授权编译。攻击评测还会有攻击生成/预检，按实际运行计费。
- `[security]`：L3当前动作语义审计，可以与main同模型/同服务，也可以独立配置。它不一定是小模型，不是需要训练的分类器。
- 主模型接口需要支持当前Chat Completions消息格式、tools/function calling，以及L2使用的JSON输出；审计接口需要支持JSON输出。仅有普通聊天可用并不能证明工具循环和授权/审计协议可用。
- 主模型与审计模型默认均为 `qwen3.7-flash`，流水线沿用temperature=0配置（实际序列化由锁定的后端适配器决定）、reasoning_effort="none"，显式关闭思考；实际设置记录在模型公开配置中。DeepSeek仍保持none适配。两项由源码设置，**不是**models.local.toml中的可调字段；仅写入temperature/max_tokens等额外键不会让流水线采用它们。两个后端共用模型接入。

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
| DeepSeek | 按[官方API认证说明](https://api-docs.deepseek.com/api/deepseek-api/)到控制台创建Key；从[Chat Completions参考](https://api-docs.deepseek.com/api/create-chat-completion/)核对model、tools与JSON支持 | provider=deepseek，base_url=https://api.deepseek.com；可显式使用deepseek-flash，运行前确认账号可用 |
| 阿里云百炼/Qwen | 按[获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)选择地域/业务空间；按[首次调用文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen)核对模型ID和OpenAI兼容地址 | provider=dashscope；模板qwen3.7-flash；使用公共OpenAI兼容地址或本地配置的北京业务空间地址，Key须匹配该空间 |
| 其他兼容服务 | 从该服务官方API文档获取完整base_url、实际model_id与Key；不要只依据模型品牌猜endpoint | 显式填写provider/model_id/base_url和独立Key变量 |

百炼Key、模型和endpoint有地域/业务空间范围，不能混用；以[当前官方Key说明](https://help.aliyun.com/zh/model-studio/get-api-key)为准。官方链接核查于2026-10-13，模型可用性以后仍应由测试者确认。

### 2.4 最小可运行配置与角色复用

复制 [models.example.toml](../config/models.example.toml)到被Git忽略的config/models.local.toml，填写自己的连接信息。下面是单服务示例：

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
# api_key = "YOUR_DASHSCOPE_API_KEY"
```

```bash
export DASHSCOPE_API_KEY='填入自己的API Key'
```

如使用北京子业务空间，保留控制台给出的 `https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1` 地址及其对应Key，不要换成其他空间地址。`api_key_env` 是**变量名**，不能填密钥；希望直接填写时放在被Git忽略的local文件的 `api_key` 中。配置模板和日志中不要放入真实密钥。

省略security段、且没有DSCG_SEC_*覆盖时，审计角色通过fallback复用主模型配置；模板则显式将两者均设为千问。需要独立审计模型时修改该角色的provider/model_id及对应provider连接。角色中不要保留另一个服务的base_url/api_key/api_key_env；provider共享段有助于避免切换后误用凭证。

DeepSeek仍可使用：将main/security都改为provider=deepseek、model_id=deepseek-flash，并在 `[providers.deepseek]` 中设置其地址和Key；保留千问共享段便于切回。也可通过现有角色环境变量覆盖模型和provider。多个服务的Key各自留在对应provider段，不共用。

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

真实注册工具具有name、description、parameters和run；输入schema由当前后端的函数定义/类型标注机制生成。schema说明属性类型、required字段、default/枚举等；实际函数实现才决定副作用。工具描述由宿主提供；默认L2编译使用全部原生名称、描述与完整参数schema，主模型工具视图仍只展示有效已授权工具。L3宿主描述逻辑不变。`tools.local.toml`仅描述风险，不替代原生参数定义，也不直接指定本任务白名单。步骤输出与限制见[运行指南](./benchmark.md#默认-v33-策略与复测)。

以下示例**只查看注册定义，不执行send_email、不调用模型**：

```python
import json
from dscg.benchmark_catalog import get_backend, get_suite

backend = get_backend()
suite = get_suite(backend.suite_version, backend.suites[0])
tools = {tool.name: tool for tool in suite.tools}
print("available:", sorted(tools))
tool = tools["send_email"]
print("description:", tool.description)
print(json.dumps(tool.parameters.model_json_schema(), ensure_ascii=False, indent=2))
```

AgentDojo可选workspace、travel、banking、slack，工具数24、28、11、11，同名去重69个；AgentDyn可选shopping、github、dailylife，工具数39、34、27，同名去重65个，不跨后端混选。核对实际schema：AgentDojo的`get_file_by_id`使用file_id，AgentDyn的`read_file`/`create_file`使用path；GitHub的`input_to_webpage`接收inputs映射，购物/日常场景接收input_ids和input_values列表。required表示调用时必须提供；schema不包含未来任务的真实收件人、文件ID或金额，这些值由任务/环境及必要读取获得。

若要查看宿主实现，可用inspect.getsource(tool.run)，或在当前后端的suite工具模块中读源码；与当前安装版本及实际工具实现匹配，不能只照抄另一后端或版本的参数表。description/参数schema不是输出schema，也不能据其推断完整事实来源或对象权限。

必须按实际副作用审阅：`browse_webpage`和`input_to_webpage`会调用页面handler，可修改状态、发送数据或付款；OTP验证工具会执行先前排队的callback。因此它们按critical、非幂等分类并接受审计，不能当普通网页读取。`get_invoice`会创建托管附件并发邮件；`git_get_linked_ssh_keys`在未验证分支发OTP、排队请求。下载和git clone/pull写入模拟文件系统；未读邮件接口会标记已读。相反，`add_calendar_event_participants`的当前实现只追加参与人，不像描述声称的那样发邮件；分类以实现为准。

## 4. 工具风险元数据：作用、字段及覆盖

### 4.1 加载位置

标准full/partial/dashboard runner只选择一个风险目录，顺序为：显式`--tool-metadata`/网页路径→`DSCG_TOOL_METADATA`→`config/tools.<backend>.local.toml`→可归属且匹配当前后端的`config/tools.local.toml`→对应内置目录：[AgentDojo](../config/tools.agentdojo-v1.2.toml)或[AgentDyn](../config/tools.agentdyn-v1.2.toml)。专用local路径分别为tools.agentdojo.local.toml和tools.agentdyn.local.toml。显式路径不存在会报错，不合并目录，也不因选中目录缺项而自动补全。

通用local只有在完整工具映射的验证后语义与某份审核内置目录完全相同时，才能自动归属该后端；注释和顺序不影响判断，工具名集合相同但分类改过不算匹配。当前通用文件是AgentDojo审核目录的副本：在ipi中使用，在ipi-agentdyn中提示跳过并使用AgentDyn内置目录，原始字节不变。无法归属的自定义通用目录会fail closed，需显式指定该文件或维护专用local；显式/环境/专用local允许自定义目录，无需增加benchmark字段。

普通测量无需工具目录flag，激活任一后端环境后使用同一命令：

```bash
python -m experiments.run_partial_benchmark --clean --name clean_20261018_01
```

该命令会调用模型，需测试者自行启动；前面的目录/schema检查无需调用模型。需要覆盖时使用显式flag、启动Dashboard前设置DSCG_TOOL_METADATA或填写网页路径。DSCG测量在创建模型前验证当前后端全部工具覆盖/字段，baseline不加载防御目录。`resolve_tool_metadata(..., backend=get_backend()).public_dict()`可离线查看所选路径、来源、当前/目录所属后端与跳过原因；显式自定义目录的所属后端可为null（未归属），不猜测归属。

直接使用factory API时，需传入tool_metadata=load_tool_metadata()或由宿主在runtime注册元数据；factory本身不会自动读这个文件。工具名必须匹配实际注册name。runner传全suite目录后会按当前runtime筛选；自写set_tool_metadata(runtime, ...)应先筛选当前runtime工具，否则未注册名称会报错。隔离runtime可显式加载自定义/部分目录，无需后端身份字段；缺失/非法项保持critical并fail closed。benchmark的完整覆盖预检是独立API。

### 4.2 必需字段

| 字段 | 允许值 | 对框架的实际意义 |
| --- | --- | --- |
| effect | read / write / delete / financial / external_send | 真实动作类型；影响默认读取授权及风险/审计路径，不按名字里含get/read就推断 |
| source | calendar / email / cloud / web / local | 工具接触的来源域；是宿主分类，不认证返回事实；新平台按实际操作使用既有域 |
| sink | none / external_recipient / public_output | 是否有外部接收方/公共输出；影响风险与免审资格。none不表示任意目标安全 |
| sensitivity | public / internal / personal / secret | 信息敏感度；个人/秘密读取不能当公开免审 |
| idempotent | true / false | 宿主声明重复相同操作是否改变预期结果；是L3新增internal/personal读取路由资格之一，不提供exactly-once保证 |
| reversible | true / false | 宿主是否认为副作用可逆；仅记录属性，当前没有自动撤销/恢复机制 |
| schema_version | 可选，默认dscg.tool-risk.v1 | 当前风险分类schema版本，其他版本拒绝 |

布尔值使用TOML true/false，不是字符串。external_send必须带非none sink；delete不能标reversible=true。risk_level、deterministic_read、confirmation_required、audit_required由源码推导，不是应手工填写的额外字段；多余字段被拒绝。confirmation_required不是要求测试者逐动作点击确认的网页流程，也不替代用户任务授权。

以下是AgentDyn内置send_email分类；其他后端同名工具应读取各自审核目录：

```toml
[tools.send_email]
effect = "external_send"
source = "email"
sink = "external_recipient"
sensitivity = "secret"
idempotent = false
reversible = false
```

例子：get_unread_emails会标记邮件已读，所以内置effect=write；send_email和真实发送参会人通知的日历修改是external_send。单effect字段不能枚举动态handler的所有行为；同名工具采用跨场景保守主风险分类，配合sink/敏感度保留审计要求，不表示付款以外的行为已被约束。

公开免审来自有效read+public+sink=none的既有规则；idempotent不是这个旧规则的独立硬条件。单个internal/personal幂等无sink读取，在输入完整、L2允许且开启selective时可按经验阈值免审；其他情况继续审计。风险级别也不是最终allow/deny：Monitor保留已授权sink-free读取的deny例外，详见 [框架边界](../README.md#读取例外开销与当前边界)。

### 4.3 生成、检查与新增工具

默认已内置目录，普通比较无需生成本地文件。需要独立维护覆盖时：

```bash
python -m experiments.tools.generate_tool_metadata
```

该命令先核对当前后端安装元数据与全部注册工具覆盖，再**复制该后端审核目录**，不调用模型、不通过训练或工具名猜分类。默认目标为config/tools.agentdojo.local.toml或config/tools.agentdyn.local.toml，后续同后端会优先加载它；已有目标默认拒绝覆盖。可显式指定新输出路径；--force仅替换允许的输出文件，通用tools.local.toml及两份审核内置目录始终受保护，不能用force覆盖。生成不会合并或导入另一后端分类。

只读检查所用目录（不生成文件、不调用模型）：

```python
from experiments.tools.generate_tool_metadata import validate_catalog

catalog = validate_catalog()  # 校验当前后端的内置完整目录
print("classified tools:", len(catalog))
# 自维护完整目录时，显式传入对应路径，例如validate_catalog("config/tools.agentdojo.local.toml")
```

自定义子集/新增工具不能直接假定通过完整后端目录检查。自定义接入顺序是：宿主实现并注册工具→从当前函数定义取得schema/描述→补六项风险属性→通过set_tool_metadata/register_tool_metadata注册检查→新可信任务编译权限→执行仍经precheck/L3/Monitor/ticket。注册和填写元数据都不等于用户授权；任务中途更改目录使旧授权失效，不从tool正文注册新工具。当前权限和风险控制仍是工具级；动态handler、OTP链和任意文件/收件人参数没有因此获得对象/数据来源约束，研究闸门与I3 partial状态保持。

## 5. 运行控制：默认值、用途及设置入口

下表列出的 partial CLI 开关也适用于全量 `experiments.run_benchmark`；两者共用执行与报告流程，仅任务范围和默认输出根不同。两入口默认当前后端全部场景；AgentDojo可用`--suites workspace travel`，AgentDyn可用`--suites shopping github`，不跨后端混选。full保留所选场景全部注册任务，partial保留前三个任务前缀。当前计划数：AgentDojo full clean97、每攻击targeted网格949、typical2847，partial clean12/typical108；AgentDyn对应60/560/1680和9/81。这些不是有效分母或API请求数。示例见 [小批量指南](./partial_benchmark.md#对照与输出)及[全量指南](./benchmark.md)。`use_sandbox` 等仅 API/网页控制仍不因此新增同名 CLI。

| 控制 | 默认 | 可设置入口 / 作用 |
| --- | --- | --- |
| use_sandbox | true | factory/API、网页；L2工具授权，关掉不创建任务文件授权；partial普通默认不提供同名CLI |
| input_isolation | true | factory/API、网页；L1来源视图；partial普通默认开 |
| l1_projection_mode | projected | factory/API、partial `--l1-projection-mode off/shadow/projected`；网页默认projected，无独立选择器；off保留原来源封装，关闭L1则有效off |
| authorization_precheck | true | factory/API、网页；L3之前本地整批权限检查；NoL2无效 |
| planning_tool_view | true | factory/API、网页、partial --no-tool-view；关掉展示完整目录，执行授权仍检查 |
| delegated_tasks | true | factory/API、网页、partial --no-delegated-tasks；有界明确执行文件/唯一邮件/指定网页任务，不把普通返回变成任务 |
| use_security_checker | true | factory/API、网页、partial --no-checker；整个L3语义审计开关 |
| audit_router_mode | API/factory off；DSCG CLI shadow | full/partial CLI未显式指定时，baseline/NoChecker为off，其余为shadow；显式不兼容组合报错。off仍运行原L3，shadow观察并审计，selective按直接阈值免审 |
| audit_router_threshold | 0.70 | CLI --audit-router-threshold、Python/Dashboard API；有限数值[0,1]，等于阈值仍审计；0不新增免审，1仍审计分数恰为1的调用 |
| audit_router_artifact | 已停用 | 非空值直接报迁移错误，改用threshold；不读取旧artifact |
| audit_retries | 0 | factory/API、partial --audit-retries 0/1；仅语义abstain有界重审，普通比较保持0，不是SDK传输重试设置 |
| completion_prompt | false | factory/API、partial --completion-prompt；历史可选提示，当前普通比较保持关闭 |
| trace_level | summary | factory/API、网页、partial --trace-level；standard逐条紧凑记录，full压缩诊断增加序列化/写盘成本 |

这些控制不会从模型连接TOML读取。NoL2同时关闭前置检查、授权工具视图与委托展开；L2/L3均关时L1也关闭。shadow/selective要求L2和L3同时开启，baseline使用原生循环。L3运行时不再要求独立标签或artifact；0.70是经验参数，尚无独立风险校准保证。authorization_profile/delegated_task_reader是受信host API对象，不是普通测试必填项或TOML新增段，详见 [L2方案](../workshop/L2_opt.md)。

### L3直接阈值路由

`threshold-read-v1` 使用原字符三元组与四信号最大值，不训练模型。单个已授权、有效元数据、幂等、无sink的internal/personal读取，只有输入完整、参数有效且 `s < audit_router_threshold` 时才免审；其他调用继续审计。secret、外发及副作用动作不进入新增免审。

```bash
python -m experiments.run_benchmark --suites banking slack --name threshold_shadow_new \
  --audit-router-mode shadow --audit-router-threshold 0.70
```

Python使用 `make_defended_pipeline(audit_router_mode="selective", audit_router_threshold=0.70)`；Dashboard API接受同名字段并校验/透传，默认off，页面没有新增控件。阈值不从模型连接TOML读取。NaN/Infinity、布尔值、非数值和越界值在创建模型前拒绝。

shadow保留真实审计，并在根级报告比较0.65/0.70/0.75及实际阈值。模拟Token只统计已知事件，缺失/损坏输入或成本时不推造全量；审计allow/deny分歧不能当作独立安全标签。策略、资格范围与阈值进入配置/缓存身份，换阈值须新name。旧artifact参数非空明确拒绝。

### 历史独立校准（当前运行不依赖）

[历史预设](../config/l3_router.calibration.json)和离线数据构建/校准器保留原独立分组流程，epsilon/delta及80组算例属于旧方案，不再控制当前selective。未来重新启用独立校准需另行验证范围、数据和配置；历史artifact不能作为当前运行输入。见[L3方案](../workshop/L3_checker_opt.md)。

--model-config/--tool-metadata是输入配置路径；--name标识实验；--results-dir是输出根；--task-manifest仅用于显式冻结任务ID，默认无需导入。修改任何有效配置/策略后使用新name，--force-rerun不绕过旧manifest绑定。成本比较采用新name并force-rerun，仍核查API usage/样本分母，不能只凭flag保证可比。

两测量入口和cohort默认按attack使用spawn独立进程并行，不新增CLI/API参数；每个attack内部仍顺序执行场景及任务，单attack与clean继续直接顺序运行。准备阶段静默核对全部配置，不创建pipeline；每组执行时再创建独立pipeline及tracker。通过Python脚本调用时，将测量调用放在`if __name__ == "__main__":`保护内，以满足spawn入口要求；CLI已处理。见[运行流程](./benchmark.md#按攻击并行与准备信息)。

两测量入口支持显式`--reuse`（API：reuse=True，默认False），未指定攻击/场景时恢复原计划。要求原name和可核验目录，与force-rerun/清单导出互斥，并覆盖环境强制重跑。核对后端、模型、完整任务、攻击、工具元数据内容和有效防御设置；源码哈希、Git commit及Python补丁版本不作为续跑门槛。旧绑定保持原字节，规则变化另存configuration_only记录；缺少必要配置时拒绝。冻结cohort测量只校验名单自身摘要与模型/环境/所选任务，screen续跑仍检查原预检证据。见[续跑指南](./benchmark.md#显式续跑示例)。

保留的L1银行投影适配器针对AgentDojo原生银行月支出请求与完整Transaction返回，最多32768 UTF-8字节、500行；没有为AgentDyn三个场景新增profile，使用完整来源隔离。原生callable/code/schema和元数据不兼容、错误/截断或未知字段均回退，不把旧适配器结果视为新场景已验证。模式/适配器身份影响缓存和L3路由配置兼容，切换用新run名；细节见 [L1说明](../README.md#l1-优化任务限定的结构化投影)。

现有文件委托支持AgentDyn的`read_file(path)`文本；有副作用的`browse_webpage`不能替代纯`get_webpage`委托引导读取。目录自动选择不扩展委托或内部handler权限。

审计输入v2最多选择当前任务的8条调用—返回对：保留最近4条，再匹配候选参数/用户指定资源补充较早证据；最多考察最近256条当前任务返回。工具正文、规范化调用参数与错误共享8192字符预算，单条调用参数最多1024字符，裁剪显式标记。删除候选且用户仅需文件大小比较时的严格列表适配最多131072 UTF-8字节、512行，保留全部元数据并显式省略正文；失败回退有界原文。工具描述512字符、任务2048字符、动作历史32条，timeout30秒；委托源正文1536字符、规范化T_eff2048字符、序列化返回16384字符。结构化解析最多16层，错误最多512字符，与参数共同占用单条1024字符配额；有序复合委托不自动展开，避免提前读取后续任务源。它们是当前源码边界，普通CLI没有--audit-window/--max-task-chars等参数，不在TOML虚构配置项。

## 6. 常见问题与首次检查顺序

| 现象 | 优先检查 |
| --- | --- |
| Missing API key | api_key_env填的是变量名且该变量在启动进程前已设置；复制模板后security是否仍选另一provider |
| 401/403 | Key所属服务/地域/权限与endpoint、model_id一致；检查服务控制台。离线解析成功不代表鉴权成功 |
| 404/model not found | model_id是真实API ID，base_url含正确兼容路径，不是网页地址或追加了完整/chat/completions |
| 400/JSON或工具回合失败 | 主模型tools、tool角色回合、JSON response_format兼容性；DeepSeek是否用了当前none设置；不要将协议错误算防住攻击 |
| METADATA_MISSING / METADATA_INVALID | 实际选中的工具目录、覆盖、六个字段/布尔/枚举/多余字段；本地目录是否遮蔽内置分类 |
| benchmark tool metadata missing classifications | 核对显式/环境/专用local选中的目录是否覆盖当前后端；不通过合并另一目录补齐 |
| unassigned custom generic tool metadata | 通用tools.local.toml不是任何审核目录的语义相同副本；保留文件，显式选择它或维护后端专用local |
| 来源/revision/包路径不匹配 | 核对当前Python、实际导入路径、发行/commit与安装来源；源码哈希已不作为启动条件 |
| AUTH_CATALOG_CHANGED | schema、描述、callable/依赖或元数据在任务内改变，旧授权不能继续；用新可信任务边界，不把错误文本作为补权依据 |
| AUTH_CONSTRAINT_CONFLICT | host profile禁止能力与必要读取闭包冲突；不是简单多加权限，需核对独立任务/规则 |
| DELEGATED_* | 有限执行句式/限制、注册reader、源是否唯一且成功监控读取、1536/2048/16384长度；仅总结文件不会展开权限 |
| router设off仍有审计成本 | off只关新增免审路由；关闭整个L3需NoChecker对照，不能混淆两种实验 |

先完成无需API的配置解析/schema/风险目录检查，再由测试者运行有限的干净工具任务与JSON协议检查，最后做匹配attack对照。以上离线检查只确认字段/覆盖，不证明模型理解正确、任务完成或安全有效。其他攻击选择、结果目录和评分口径见 [测试文件索引](./evaluation.md)。

CLI结果按分类根/后端/运行目录保存：`results/partial_benchmark/agentdojo/qwen3.7-flash_baseline/`。results-dir仍指分类根；full、partial、screen/cohort共用路径规则。已有旧目录通过reuse原地恢复，选择顺序与限制见[结果指南](./benchmark.md#显式续跑示例)。
