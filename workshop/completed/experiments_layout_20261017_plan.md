# Experiments 目录归类 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; preserve current uncommitted changes and existing evidence.

**Goal:** experiments主目录保留三个当前测量入口，其余按用途归类，行为与任务范围不变。

**Architecture:** run_benchmark、run_partial_benchmark、run_injection_precheck路径不变；common集中共享清单/报告/cohort，diagnostics保留E0/I3/轨迹审计，calibration放L3数据及校准，tools放元数据工具。不保留顶层转发壳。只允许明确哈希绑定的预检目录迁移兼容，攻击测量继续用新name。

**Tech Stack:** Python、unittest、现有AgentDojo；无新依赖。

**Spec:** 本次用户指令与AGENTS.md目录/证据规则。

## Global Constraints

- 不调用真实模型、不删历史结果或既有测试，不改变默认前3×前3、full/cohort/suites、shadow/baseline行为。
- 原文件先归档并记录哈希，历史清单及既有归档不改写。当前引用更新；历史命令保留原上下文。
- 不修改防御机制或研究路线。工程产物在workshop/artifacts/20261017_experiments_layout。

## Review Focus

- I3定位fixture不能因深一级目录而指错；现有I3测试及新入口help验证。
- 源码路径移动仍需绑定实际新文件；证据兼容不能忽略未知哈希、额外文件或防御变化。
- 旧预检manifest/attempt/cohort不改写，续跑不重测已完成目标。
- 三个入口和Dashboard的评分辅助导入不可断开；全套离线回归。
- 当前文档命令与链接指向新目录，历史证据字节保持原样。

### Task 1: 记录身份并锁定预检兼容契约

- [x] 保存当前文件哈希、完整工作树状态和source_revision。
- [x] 新增目录迁移的兼容测试：明确旧来源能恢复原manifest且不重测，未知脚本/防御仍拒绝。
- [x] 对新增契约先运行RED并记录日志；不为简单目录常量添加镜像测试。

### Task 2: 移动模块并修复路径

- [x] 移动common/{partial_controls,partial_reporting,injection_cohort,compatibility}、diagnostics/{harness_audit,i3_p0_stress,trace_diagnostics}、calibration/{l3_router_dataset,calibrate_l3_router}、tools/generate_tool_metadata，增加空包标识。
- [x] 同步当前代码/测试导入，修正root/fixture定位和source路径；入口名称/参数保持不变。
- [x] 兼容映射仅添加明确的旧source完整集合与路径映射，接受正确关联的旧screen脚本哈希，不使用通配忽略。
- [x] 运行新契约和已有预检、full/partial、Dashboard、E0/I3/L3回归。

### Task 3: 文档与证据

- [x] 更新experiments/README及当前文档/工具配置/报告链接；旧历史命令不重写，原文归档。
- [x] 全套离线测试、全部入口help、链接、哈希与git diff --check；独立审阅一次。
- [x] 生成迁移清单、报告及研究侧追加交接；不提交、不合并、不跑真实benchmark。
