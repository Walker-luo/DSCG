# L3 路由：当前边界与未验收项

当前规则为`sink-free-read-v4`，实现见 [audit_router.py](../dscg/audit_router.py)与[流水线](../dscg/pipelines/defended.py)；操作见[配置指南](../docs/model_tool_configuration.md#l3读取路由)及[结果指南](../docs/result_files.md)。

## 当前规则

- 已注册、已授权、schema有效的`effect=read`、public/internal、`sink=none`调用在off/shadow/selective均固定免审。外部接收方读取、personal/secret读取及效果动作仍审计；valid deny／abstain阻断。
- 混合批次只审非免审子集，整批候选／权限检查、回执及一次性票据继续约束原调用。工具级标签不认证对象私密性、来源事实或查询参数安全。
- CLI默认shadow，factory/API默认off；off不关闭L3。阈值和分项分数只作诊断／配置绑定，不控制当前免审范围。
- 无需加载旧校准artifact；非空旧artifact参数仍拒绝。旧threshold-read-v1、read-purpose-v2与独立校准工具只按各自历史协议解释，不作为当前放行条件。

## 未验收项

没有建立独立安全标签下的一般风险上界、适应性攻击安全或真实Token节省结论。任何新路由规则须先选择明确范围，保留匹配clean／攻击、错误、未知成本和原生标签；不得凭audit allow或shadow分歧替代独立验证，也不得自动把历史校准范围扩大到新工具。

历史算法与阈值设计见 [算法实施](completed/l3_algorithm_implementation_20261010.md)、[阈值阶段](completed/l3_threshold_20261021.md)；当前后续工作以 [DV_STATE.md](../DV_STATE.md)为准。
