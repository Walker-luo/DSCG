# DSCG_v3.5真实迭代计划与状态

已获用户实施批准。累计1000次API、200万Tokens、最多3轮；不跑离线测试。默认保持legacy/DSCG_v3.4，仅候选intent-evidence-v35使用新协议与DSCG_v3.5身份。

- L2：完整原生目录分组，一次输出每个动作工具的布尔许可；宿主求并集，合并原自动读取，无动态补权。
- L3：当前读取/效果/混合阶段，排除额外确认误导字段；同次assessment+verdict，严格有界、失败关闭、原Monitor/回执/票据不变。
- 固定banking3/13/15、Slack3/11/16的原攻击键；新baseline最多60次，每轮组件最多18次，每原生案例最多30次；shadow，Qwen双模型，关闭思考，温度0。
- 六类相邻反例不得新增allow。两次完整新运行均至少5/6utility成功且security全false、无错误，才切默认；预算/三轮耗尽未达标则保留v3.4。

新证据：[任务目录](./artifacts/20261023_v35_live_iterations/)。原结果/download和已有未提交修改保留。此为工程效用候选，不解锁研究闸门或宣称总体安全。

## 已完成与停止

三轮已完成，最终组件六正例allow、六反例deny；原生六例utility4/6、security0/6，未达5/6，未启动确认或提升默认。220次API/384803Tokens，APIerrors0；因三轮上限停止。候选保留，后续迭代不在本次授权范围。详见[实施报告](./completed/v35_live_iterations_20261023.md)。
