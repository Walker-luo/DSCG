# L3：直接阈值运行与后续扩展

## 当前已实现：threshold-read-v1（2026-10-21）

- 保留字符三元组和四个信号的最大值s；无需分类器、独立标签或运行时artifact。
- 默认经验阈值0.70；合法有限数值[0,1]。满足资格且s<threshold才免审，等于阈值继续审计。
- 资格为单个已授权、元数据有效、幂等、无sink的internal/personal读取；schema、完整性及长度检查保留。secret、写入、金融、删除、邀请、外发仍审计，风险目录不变。
- CLI默认shadow，Python/Dashboard API默认off；shadow保留真实审计，selective才实际免审。L2、Monitor、一次性交接与执行票据保持。
- full/partial/cohort/screen和Dashboard API使用同一阈值，公开字段audit_router_threshold；旧artifact参数非空报迁移错误。
- 策略/资格/阈值绑定运行身份，新策略和不同阈值须新run名；历史结果不重解释。

```bash
python -m experiments.run_benchmark --suites banking slack --name threshold_shadow_new \
  --audit-router-mode shadow --audit-router-threshold 0.70
```

## Shadow记录与阈值选择

逐次保留四个分项、s、阈值、资格/回退原因、模拟选择、实际审计判决与协议有效性、Monitor结果、审计Token及延迟。根级l3_router_summary.md/json按攻击/场景/配置比较0.65/0.70/0.75及实际阈值，原公开读取免审单独统计。

这些是已记录历史轨迹上的经验统计，不是误放率、风险上界或真实Token节省；未知输入/成本保留未知，不自动选阈值。0.70需要后续shadow与匹配实验验证，不承诺TSR/ASR改善。

## 待扩展（当前不作为运行条件）

独立标签校准、多字符长度对照和其他路由特征待单独评估。当前不更改n=3，不新增动态扩权、参数/对象机制或恢复动作。原独立校准工具与config/l3_router.calibration.json保留旧internal范围及原语义，未来应用到扩大后的范围需另行设计验证。

## 0. 候选参数初始化（2026-10-19，历史）

旧grid=[0.65,0.70,0.75]、epsilon/delta=.05/.05和80组算例仅属于原独立分组校准方案，不控制当前路由。原文按原字节保存在[历史方案](./archive/l3_calibration_runtime_20261021/L3_checker_opt.md)，既有实施报告与输入证据均保留。

使用说明：[配置指南](../docs/model_tool_configuration.md#l3直接阈值路由) · [结果指南](../docs/result_files.md)。
