# Experiments目录归类

日期：2026-10-17。基准revision：`8c591e27390c77614dbf4d1ff46f98428c8b5e30`。本次开始时工作区已有上轮文档和CLI改动，均按当时字节保存，不重置、不提交。

## 当前入口与归类

用户要求主目录只留下目前框架测试需要的文件。顶层保留三个日常运行入口及包标识/索引：run_benchmark、run_partial_benchmark、run_injection_precheck。命令、参数、默认输出、shadow/baseline行为及任务范围不变。

- common：任务选择/缓存绑定、报告、cohort与明确版本兼容。
- diagnostics：E0、I3和启发式轨迹诊断。保留专项测试；harness_audit原评分辅助函数仍供runner与Dashboard使用。
- calibration：L3数据准备与独立组阈值校准。
- tools：工具风险元数据检查与导出。

详细模块表和新命令见 [入口索引](../../experiments/README.md)。旧顶层工具不保留转发壳；历史命令保留当时上下文。原始字节与哈希见 [归档](../archive/experiments_layout_20261017/README.md)及[迁移映射](../archive/experiments_layout_20261017/relocation_manifest.json)。

## 身份与证据

移动模块后同步当前代码/测试/Dashboard导入，修正I3 fixture和源码根路径。防御实现、原生评分和任务选择逻辑不变；已有三个入口的外部路径不变。

source_revision记录实际新路径；只为明确已知旧source完整集合添加路径兼容，screen脚本哈希须与该旧来源对应。未知脚本、额外源码、模型/任务/规则或防御实现变化仍拒绝。旧screen可续跑、旧cohort可读取，不重复已完成目标、不改写原manifest/attempt/cohort；新攻击测量需新name，不以目录整理绕过缓存绑定。

修改前的工作树/文件身份、原文归档、RED/GREEN日志、完整命令/退出码、链接及哈希验证放在 `workshop/artifacts/20261017_experiments_layout/`。既有归档和原始结果不改写；先前用户的两项旧文档删除保留。

## 验证范围

- 初始离线回归389/389；目录迁移后391/391，exit0。新增迁移后的E0命令集成验证、真实旧source冻结cohort恢复验证。
- 新命令测试先RED（缺少新模块），迁移后GREEN；E0合成分母仍为valid1/tool_error1/infrastructure_error4。预检29项通过，覆盖错误不剔除、续跑、旧证据与未知源码拒绝。
- 三个日常入口、旧benchmark兼容子命令及专项工具共10次help离线检查；不构建真实模型。
- 当前文档和报告的本地链接/章节锚点、迁移清单、归档原文、未改防御文件与已有证据逐项检查；精确结果见validation.json。此前缺失的plan/report链接单列，不重建旧材料。
- 全套检查不证明模型效用、安全性或成本收益。研究路线不变：真实E0待完成，I3仍partial，I2保持locked，closed路线不重启。

新增真实模型请求0，真实benchmark样本0。下一步：继续使用原三个入口测量；需专项诊断/校准时按新索引选择模块，新的攻击测量使用新name。
