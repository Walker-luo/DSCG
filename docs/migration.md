# BaseIntent 命名与历史兼容

当前项目及 Python 包为 BaseIntent / `baseintent`，默认框架标识为 `BaseIntent`。Git linked-worktree 关系、分支历史和 remote 保持原状；重命名不建立新的防御质量结论。

| 当前接口 | 兼容边界 |
| --- | --- |
| `import baseintent`、`python -m baseintent.benchmark_catalog` | 不提供 `dscg` Python import shim；脚本应更新导入 |
| `BASEINTENT_*` 环境变量 | 对应 `DSCG_*` 仅为已弃用的回退；新旧同值可并存，异值明确报错 |
| 当前 `baseintent_*` 诊断/公开字段 | 历史 `dscg_*` 由共享历史读取层兼容，不重写原文件 |
| `.baseintent.jsonl` / `.baseintent.responses.jsonl` | 新执行格式；旧 `.dscg.*`、inline/v1/gzip 仍可读 |
| BaseIntent 页面和下载标签 | 历史结果保留原 DSCG 版本和配置身份 |
| `artifacts/<日期>_<任务>/` | 新临时产物入口；现有用户结果及历史证据保持原路径 |

provider 的 `DASHSCOPE_API_KEY`、`DEEPSEEK_API_KEY` 等变量、原生 agentdojo 包名、两个 conda 环境 `ipi/ipi-agentdyn` 和本地配置文件名保持不变。无需重建环境或覆盖已有凭证。示例配置见[配置指南](model_tool_configuration.md)。

`legacy` 是现有 profile 选择器，当前解析为 BaseIntent；`legacy-v34` 与其他显式历史 profile 保持原协议语义。运行名称不选择策略。历史结果标签只描述原运行，不提升为新版本。

命名、策略/schema/请求格式/有效配置变化使用新运行名。旧 DSCG 测量缓存、冻结 cohort 和未完成 screen 不转为 BaseIntent 身份；跨命名空间续跑明确拒绝。当前命名空间内已有名单仍按模型/provider、后端与任务绑定验证消费。显式历史 GOAL 证据复用保持原有独立核验边界，不等于迁移旧名单。显式 reuse 仍需匹配完整有效配置，不能靠改目录名或字段绕过。

历史读取在内存中合并允许的旧结构，缺失身份、回复或成本保持未知，不伪造补全。新当前代码和文档可独立运行，不依赖历史工程记录或兄弟仓库。验证和实际限制见[维护记录](maintenance.md)。
