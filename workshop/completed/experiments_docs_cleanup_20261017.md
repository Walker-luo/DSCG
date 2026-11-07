# Experiments / docs 整理

日期：2026-10-17。基准 revision：`9f385a3433f6d09bb7c9b278258ecc43f34e62c8`；开始时已有未提交partial场景/cohort改动，全部保留。

## 清理范围

| 原目录 | 处理 |
| --- | --- |
| experiments/plots/ | 4个硬编码旧数据绘图脚本及包入口共5文件原样归档后移除；没有当前运行导入依赖 |
| experiments/payload_reporting_probe.py、payload_reporting_frozen_cases.py | 仅用于10月12日阶段、绑定历史输入的2个模型脚本原样归档后移除 |
| docs/figures/README.md | 退役绘图入口说明移至归档；既有历史图表不动 |
| Python缓存 | 删除28个生成字节码文件，不作为历史证据 |
| 当前文档 | evaluation统一链接模型/工具详解，保留现有partial/cohort命令；framework_updates保留当前流程/平台边界，将重复阶段统计改为报告链接 |

新增 [实验索引](../../experiments/README.md)，更新 [文档索引](../../docs/README.md)。benchmark/预检/校准/元数据/E0/I3/被测试使用的trace诊断均保留。V2旧证据兼容symlink不变。10月12日诊断报告只更新两个脚本阅读链接并明确标注整理；原报告字节已保存，旧命令和样本不改写。

原始文件、退役原因和before/after哈希见 [清理归档](../archive/experiments_docs_cleanup_20261017/README.md) 与 [映射清单](../archive/experiments_docs_cleanup_20261017/relocation_manifest.json)。归档脚本保留原位置ROOT逻辑，不能直接在新位置执行，也不是当前模型效果证据。

## 验证

工程产物根为 `workshop/artifacts/20261017_experiments_docs_cleanup/`；before.json记录初始工作树与文件身份，validation.json记录命令/退出码、归档/引用检查及保护文件哈希。活动experiments共享实现、cohort兼容映射、dscg与tests和开始时逐字节一致，evaluation任务/参数/结果说明段也保持原字节。

- `conda run -n ipi python -B -m unittest discover -s tests -v`：exit0，381/381，未发起真实模型请求。
- full、partial与screen的CLI帮助：exit0；partial场景/cohort选项和每场景3×3默认保持。
- 当前docs/实验索引/归档索引的本地链接、归档哈希、旧绘图历史hash条目、保留模块语法及退役模块导入检查通过；`git diff --check`：exit0。
- `python -B workshop/verify_migration.py`：清理前后均exit1，同一 `AssertionError: README.md`。它校验早期固定文档快照，冲突在本轮前已存在；本次不修改旧manifest或校验器来绕过，不声称历史迁移全量通过。

新增真实模型请求0、benchmark样本0。用户results/download、配置凭证和研究路线未改动；E0 pending、I3 partial、I2 locked及closed路线不变。下一步：按实验索引选择现有入口；历史复现时先核对归档与当时输入身份，不把固定旧数据绘图当成当前结果。
