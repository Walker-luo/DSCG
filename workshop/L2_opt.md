# L2 授权：当前边界与未验收项

当前DSCG_v3.5.3默认`static-task-v352`；实现见 [defended.py](../dscg/pipelines/defended.py)、[l2_authorization.py](../dscg/l2_authorization.py)、[task_view.py](../dscg/task_view.py)。完整规则见[配置指南](../docs/model_tool_configuration.md)与[框架说明](../docs/framework_updates.md)。

## 已实现边界

- 默认先提取静态任务视图，再按完整可信请求及原生工具定义编译全局动作权限，合并自动读取；显式legacy保留单次授权。辅助视图保留顺序、条件和原文位置，但不验证条件或任务完成。
- 规划器仅看到有效已授权定义，实际执行目录保持完整。候选整批复核，目录变化或非法权限失败关闭；不会因为缺少工具、错误返回或模型请求动态补权。
- 有限可信host profile、必要读取闭包及明确txt/md任务源的中介准备读取已实现，保持既有协议／大小／语法边界。有效任务供规划、授权和审计共享，普通工具结果不产生递归任务授权。
- 新真实用户任务替换旧授权；目录／schema／callable等身份复核及一次性票据保留。工具授权不等于参数、对象、来源事实或完成状态保证。

## 尚未验收或不支持

真实host profile的独立标签与匹配成本／安全／效用对照仍需单独验证。通用跨轮指代／禁令继承、按需动态扩权、任务内目录热更新、自动补读／恢复、对象／数据／参数授权均不能从现有能力推断，也不由本文件解锁。

历史工具视图与委托实施见 [2026-10-12报告](completed/l2_implementation_20261012.md)，当前两阶段优化见 [v3.5.3报告](completed/v353_optimization_20261027.md)。早期候选中的“尚无任务源展开”“只输出tools”等状态已过时，不作为当前交接。后续问题从 [DV_STATE.md](../DV_STATE.md)选择。
