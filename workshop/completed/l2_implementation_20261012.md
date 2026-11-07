# L2 优化实施报告（2026-10-12）

用户明确要求根据 [L2_opt.md](../L2_opt.md)优化现有第二层。本轮工程实现已完成，默认框架版本为 **three-layer-l2-v2**：授权结果现在决定规划器可见工具，受信宿主可配置有限授权profile，明确执行干净任务文件可以先读取再完整编译。真实profile选择及安全/效用/总成本实验尚未完成，候选余项继续留在workshop顶层。

代码基点 `4d61149f55f71eb6d1091ea431b95d1abb6d172e`，分支`workshop`；实现位于未提交工作树，没有创建新branch、commit或push。已有AGENTS/L2候选/索引及两次前序归档修改已保留；本轮独立原始字节、revision manifest和工作树状态见 [归档](../archive/l2_implementation_20261012/)及 [证据](../artifacts/20261012_l2_implementation/evidence.json)。这次用户授权的是workshop工程，不修改formal technical_route，也不宣布论文创新或研究闸门通过。

## 行为与默认值

| 部分 | 本轮实现 | 边界 |
| --- | --- | --- |
| 授权工具视图 | 默认true，只展示有效已授权工具的完整schema，隔离Function和参数JSON展示类，保留完整runtime | 不用top-k，不因隐藏工具就免去执行检查；默认读取权限集合不收紧 |
| 宿主profile | `authorization_profile` API opt-in，有限任务匹配、正/负原文证据、宿主必要读取闭包 | 未配置/未匹配保持原编译；真实业务profile未内置，原文位置不证明语义 |
| 显式任务文件 | 默认true，准备读取→真实执行成功结果→T_eff→一次完整编译；规划/L3共享有效任务 | 有限句式、适配和长度；不把普通tool结果或summary任务升级权限 |
| 任务/目录边界 | 新实际user替换旧grant、撤销未用票据；目录变化阻断，执行消费票据后再次权限复核 | 不热更新/自动补权，不检测任意global/closure/宿主状态变化，不撤回在途副作用 |
| 平台/身份 | API、partial CLI、网页、报告、trace及config/cache/L3绑定同步 | native baseline不变；V2风格对照仍有新版目录检查，不能当历史V2精确复现 |

核心实现：[l2_authorization.py](../../dscg/l2_authorization.py)、[defended.py](../../dscg/pipelines/defended.py)。L1算法仅共享框架版本常量更新，未改变来源隔离逻辑；L3默认off、retries0/completionfalse、READ_ONLY_SOURCE_ALLOW读取例外不变。非法混合批次仍整拒，没有对象/参数/数据provenance、I2、义务账本或恢复机制。

## A：授权工具视图与目录冻结

设完整目录V、授权A，显示`D={t in V ∩ A | metadata(t) valid}`。所有合法授权工具都保留完整定义，不对条件后续工具额外隐藏。授权失败/失配时显示空目录；模型编造隐藏工具仍会被precheck/Monitor拒绝。

例如任务只有查询能力时，未授权发送/付款schema不再进入规划请求；已授权的其他读取仍可能可见。真实runtime不被删改，ActionLedger保留所有提议，包括拒绝调用。参数展示保存原schema JSON的独立快照，避免Python deepcopy共享Pydantic类。

任务内fingerprint绑定runtime/spec/name/description/schema、run对象及代码、dependency extractor对象及代码、宿主元数据。新增/删除/修改工具不继承旧授权；新可信任务边界重新编译。执行后工具状态改变不等于目录改变，任意外部/宿主数据变化不在此fingerprint保证中。只是工具级生命周期检查，不是完整强撤销或参数来源机制。

## B：有限宿主profile

`ToolAuthorizationProfile`是不可变宿主配置，字段为name/version、完整任务匹配patterns、allowed_seed_tools、prerequisites和可选deterministic_reads。profile最多32个pattern、128个seed/node、每项128条关系，循环关系配置时失败。关系只自动补全有效read/sink=none工具；不自动补写入、发送或外部sink。

适用动作目录复用现有一次授权模型调用、temperature0，严格返回`tools / prohibited_tools / evidence`。每项证据有tool/kind(direct/conditional/prohibited)/literal span；本地检查原文位置、注册/元数据、允许seed和闭包。必要读取与禁用能力冲突给AUTH_CONSTRAINT_CONFLICT。未知工具、额外字段或伪造证据失败关闭。原模型仍可能误解否定/例外/任务语义，literal检查不是安全证明。

以下仅是离线fixture的API示例；这些名称不代表现有suite已经选择业务profile：

```python
from dscg.l2_authorization import ToolAuthorizationProfile
from dscg.pipelines.defended import make_defended_pipeline

profile = ToolAuthorizationProfile(
    name="fixture-update",
    request_patterns=(r"Update the record, do not send\.",),
    allowed_seed_tools=frozenset({"write_data", "read_data"}),
    prerequisites=(("write_data", ("read_data",)),),
)
pipeline, main_cost, audit_cost = make_defended_pipeline(
    authorization_profile=profile,
)
# 仅宿主注册了这些工具且风险元数据有效时才适用。
```

未匹配任务标unsupported_task_fallback，不新增模型分类器/过滤调用。原本仅有效读取目录继续零模型授权；若没有host deterministic_reads则保留legacyzero_call_fallback，不为了新协议加调用。网页只控制视图/任务展开，不提供任意文本生成profile入口。

## C：执行order.txt

识别示例：“Complete the tasks in order.txt”“Execute order.txt tasks”“请完成 order.txt 中的任务”。支持txt/md、带引号文件名及有限下游限制，例如“; only query inventory, do not send”。准备读取禁令、矛盾执行意图或未覆盖附加限制以DELEGATED_RESTRICTION_UNSUPPORTED在读取前失败；有限语法不是通用自然语言政策解析。

1. 宿主解析指定source和真实reader参数，不在此步读取正文。内置注册read_file(path/file_path)；AgentDojo云盘由宿主目录唯一filename解析ID，真实get_file_by_id返回YAML需匹配filename/id。API也可传受信DelegatedTaskReader。未知adapter/参数/schema/metadata失败。
2. 只安装准备reader能力，经原L2/L3/Monitor/ticket执行宿主构造的读取调用；此时没有业务写入权限。私有读取可能产生一次L3调用，公开免审仍是原能力。
3. 仅接受匹配call id/name/args、无error、ActionLedger确实EXECUTED的真实返回。伪造tool消息、abstain阻断或读取错误不能升级任务。
4. T_eff保留原用户限制，追加完整任务正文；撤销准备授权，调用一次完整业务授权编译。模型的user展示副本使用T_eff，原始user/tool历史保持；L3任务字段和路由绑定使用相同T_eff。不会伪造新user回合。
5. 业务中的普通库存返回即使写“改发Bob”也不能替换任务；summary任务不展开文件指令。不递归把新文档提升为任务源。

正文≤1536字符、完整T_eff规范化可见长度≤2048、序列化返回≤16384字符；超限失败，不摘要或截断任务。用户已明确排除确认后任务文件被污染的情况，本轮不测试或宣称防住该情形。准备授权仍是工具级，宿主初始读取参数正确不等于已经提供对象ACL；同工具其他对象范围缺口仍属I3。

## 控件、统计与兼容

- API新增planning_tool_view/delegated_tasks（默认true）、authorization_profile/delegated_task_reader（默认None）。NoL2强制前两项false，不创建文件授权；profile要求L2。
- partial CLI新增`--no-tool-view`、`--no-delegated-tasks`，各attack都转发并绑定run manifest。prefix任务选择、typical/all攻击与nativebaseline未改。
- 网页增加相同两个checkbox，NoL2禁用，完整/NoL1/NoL3预设保持启用。V2风格预设关闭L1/precheck/view/delegation，保留新目录复核。报告依据保存effective config显示，旧缺字段仍未记录。
- pipeline名和config绑定新版本、开关、profile/reader hash、协议及1536/2048/16384输入边界。显式run名仍须新名字；旧L3校准artifact需要重新核查/独立标注，新配置不能继承旧阈值。
- `dscg_l2`累计planning_requests、catalog/visible_tools_total、authorization_compilations、bootstrap_reads、delegated_tasks_expanded、catalog_change_denials、effective_task_added_characters_total。compiler invocation不是模型调用；字符/定义数量不是Tokens。网页仅合计计分task trace，排除预检并保留coverage。compact授权仅保留contract opaque id，完整hash仍在public/full/config。

平台交接见 [framework_updates.md](../../docs/framework_updates.md)，使用说明见 [dashboard.md](../../docs/dashboard.md)，README/AGENTS及workshop两级索引已同步；原presentation/report.md、L1/L3候选、论文来源目录和迁移helper不改。

## 验证证据与成本限制

所有新输出位于 `workshop/artifacts/20261012_l2_implementation/`。精确日志/exit/hash和工作树状态由 [evidence.json](../artifacts/20261012_l2_implementation/evidence.json)记录。

| 最终命令（DSCG cwd） | exit / 结果 | 产物（同一task root） |
| --- | --- | --- |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0，283/283；244基线+39新增检查 | full_tests_after_review.log |
| `node --test tests/test_dashboard_ui.cjs tests/test_history*.cjs` | 0，28/28 | node_tests_after_review.log |
| `conda run -n ipi python -m experiments.i3_p0_stress --output workshop/artifacts/20261012_l2_implementation/i3/report.json` | 1，partial；24valid/8scope/0tool-boundary，invalid/error/skipped均0 | i3/report.json、i3.log |
| `conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output workshop/artifacts/20261012_l2_implementation/e0/report.json` | 0，synthetic6：1valid/1tool_error/4infrastructure_error，其他0 | e0/report.json、e0.log |
| `conda run -n ipi python workshop/artifacts/20261012_l2_implementation/schema_probe.py` | 0，4suite/74定义全部原生序列化一致 | schema_probe.json、schema_probe_valid_catalog.log |
| `python workshop/archive/l2_implementation_20261012/validate_revision.py` | 0，当前links/state/原字节、源码范围和results/download保护检查 | validation.json |
| `git diff --check` | 0 | diff_check.log |

独立fresh-context reviewer发现3处实际边界缺口，已先复现再修补：准备读取忽略禁令、view共享schema类、dependency code未绑定。最终复核无新增findings；view/profile19和delegation14项通过，详见 [review.md](../artifacts/20261012_l2_implementation/review.md)。原read-deny例外未改，通过入口支持域收紧解决准备禁令。完整回归初次280项出现3失败：compact重复profilehash2项及旧硬编码版本1项，均修正后重新283/283；所有中间日志保留，不隐藏失败。

本地schema probe采用**合成宿主只读grant**，不是模型授权评测：

| suite | 完整/只读可见工具 | 完整/只读schema JSON字符 |
| --- | --- | --- |
| workspace | 24 / 13 | 12666 / 5073 |
| travel | 28 / 22 | 15132 / 9585 |
| banking | 11 / 6 | 4886 / 1503 |
| slack | 11 / 5 | 3989 / 1493 |

这个结果只确认工具描述输入能缩减且schema保真。原始schema里的有效事实未剪裁，不代表总API Tokens下降；更少工具也不保证更少轮次。profile输出证据、准备读取可能触发L3、T_eff随历史重复输入、创建展示类和多次目录核验都产生额外开销。本轮**外部defender/model calls=0，benchmark rollout=0**，未测真实授权准确率、TSR/nativeASR、总/分阶段Tokens或全链延迟。旧TaskResults重构warning仍会打印，但本轮tests成功，不把它当模型/工具效果证据。

## 剩余项及下一步

工程检查不通过真实E0 gate；I3保持partial，I2和closed研究路线不变。默认没有业务profile，读取范围收紧不会在所有任务自动生效；缺工具、可替代路径或跨轮含糊要求仍可能影响效用。目录/视图不能修复编译语义误判，也不提供对同一工具目标的硬授权。

下一步固定L1、L3off、任务/攻击/model identity，两组都关闭delegation，先做工具视图A0/A1的真实匹配成本/效用/独立终态验证。之后选择宿主可核查的profile及正负/合法替代路径标签评测B0/B1；任务文件单独报告准备与业务成本。按需展示、动态目录、通用跨轮任务解析、部分批次执行不在本轮交付范围；不要借历史方案重新启动闭锁机制。
