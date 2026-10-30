# v3.6归档准备与后续优化基线

更新：2026-10-30。**后续将当前v3.5.4工作区保存为v3.6，之后在v3.6基础上改进。** 当前代码仍记录`DSCG_v3.5.4／static-task-v354`，本次说明更新不切换代码版本，也不重标历史结果。状态见[DV_STATE](../DV_STATE.md)。

## 纳入归档的当前实现

| 部分 | 当前行为 |
| --- | --- |
| 防御策略 | 沿用v3.5.4：片段ID静态视图→冻结全局工具授权；L1、L3、固定读取免审、整批Monitor与票据保留。辅助视图不保证条件、事实或完成 |
| 目标排除 | `--fliter PATH`消费最小后端绑定排除表；partial先取注册前3×3，再筛除，不补位。旧cohort输入拒绝，历史结果只读兼容 |
| 独立筛选 | `screen`用原生无防御baseline；每GOAL一条完整轨迹，成功保留，未通过直接加入fliter排除名单，不等第二次失败，续跑不重测已开始目标 |
| 测量GOAL | 默认关闭；`--goal`使用当前测量框架，先fliter后预检，每目标一次、攻击共用。失败剔除，错误跳过并exit1；不计TSR／ASR，成本另列 |
| 存储／恢复 | `flat-v1`直接写入`attack/suite/user/injection.json`，GOAL单列；根run_manifest绑定配置，summary.json原子保存判定与汇总；原输入名单不合并GOAL排除 |
| 共享入口 | full／partial／Dashboard沿用原生评分，更新缓存、诊断引用／L3回复偏移、子进程筛选传递、历史读取和导出；新旧执行缓存不混用 |

clean／DoS不接受fliter或GOAL筛选；全排除时无计分、指标N/A。不同框架的GOAL可能保留不同集合，比较须使用实际共同任务键。CLI L1默认off、factory/API projected；CLI router shadow、factory/API off，off仍运行L3。SDK retries=0不代表完整轨迹只有一次API请求。

## 已验证与遗留

- **入口与存储验证：**两后端相关合并回归各298项无失败（Dojo跳过3、Dyn跳过4），补充入口拒绝各9项通过，Node51项通过。真实Qwen计分13个不同键、13有效、0计分错误；GOAL为1通过、1有效失败、1连接错误，已正确排除／exit1且未重试。连接错误材料暂保留，见[实施记录](../workshop/completed/fliter_goal_20261030.md)。这些检查不证明TSR提升。
- **后续优化问题：**v3.5.4正式结果中的银行漏授权／未执行、合法更新误拒、日期错误，以及Slack／travel部分最终交付问题仍作为优化起点；归档不表示已解决。依据[结果分析](../analysis/v3-5-4.md)与[具体案例](../analysis/details.md)继续定位，并匹配baseline、任务键与有效分母。
- **边界不变：**没有动态扩权、完成闸门、恢复链、对象／参数硬授权或最终文本审计。损坏／未记账证据及未知usage不能补零；全仓离线仍有既有失败，E0 pending、I3 partial、I2 locked。

后续保存v3.6时同步实际代码版本与文档；`static-task-v354`是现有可用profile，不因归档自动出现新profile。之后的策略变更与验证使用新运行名，保留原v3.5.4和既有结果字节。

[配置](model_tool_configuration.md) · [评测](evaluation.md) · [筛选](injection_precheck.md) · [结果文件](result_files.md)。
