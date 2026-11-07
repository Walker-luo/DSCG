# AIMLL 论文与配图更新（2026-11-04）

- 工作站 `LuodeMacBook-Air.local`，分支 `workshop`，HEAD `8429dec719991e96db4fe25b7b86a3f261964ea4`。开始时 `paper/main.tex`、`paper/plan.md` 和架构图已有未提交修改；`paper/fig/` 的结果图、数据与脚本及 `paper/main.pdf` 已有未跟踪文件。本次基于这些文件修改，修改前的主要源文件与图保存在 `workshop/artifacts/20261104_paper_v37_update/originals/`。未暂存或提交。
- 正文按当前 v3.7 记录更新输入形态和约束；Qwen3.5 采用已有 v3.7 运行，Qwen3.7 与 DeepSeek 保留各自已有的 v3.6.3 运行身份。架构图模块图标统一，两个 L2 节点复用同一 SVG 图标；结果图增加 Qwen3.5，主表、图和正文从同一结果重算。
- 既有 Qwen3.5 结果位于 `results/workshop/agentdojo/qwen3.5-flash/{baseline,v3.7,baseline_clean,v3.7_clean}`，原始运行记录的路径指向测试服务器；本次不推定原始环境或运行命令。2,139 个两臂共同有效攻击键：原生 TSR 1,805→1,175、ASR 221→2；clean 90→53/97。两臂记录为 completed、使用相同排除表，测量 GOAL 关闭。其他模型的保留集合不同，不能将这些汇总当作共同网格比较。
- 更正论文成本口径：历史 Qwen3.7 和 DeepSeek 防御臂总已知用量分别为主模型加审计的 51,254,188 与 44,081,158 tokens；原文将主模型部分 39,980,871 与 33,286,716 当成了总量。Qwen3.7 防御臂、Qwen3.5 基线各有 1 条未知用量。原有结果和报告未回写。

## 验证与产物

下列为本次工作站离线命令，均 exit 0；系统 `python3` 为 3.9.6，`/opt/miniconda3/envs/ipi/bin/python` 为 3.10.21：

```text
python3 paper/fig/extract_paper_numbers.py
MPLCONFIGDIR=/private/tmp/dscg-paper-mpl /opt/miniconda3/envs/ipi/bin/python paper/fig/make_results_figure.py
python3 /Users/luo/.agents/skills/diagram-design/scripts/self_check.py paper/fig/system-architecture.html
python3 /Users/luo/.agents/skills/diagram-design/scripts/export_svg.py paper/fig/system-architecture.html paper/fig/system-architecture.svg --system-fonts
NODE_PATH=/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node workshop/artifacts/20261104_paper_v37_update/render_architecture.cjs
python3 /Users/luo/.codex/skills/nature-figure/scripts/audit_svg_schematic.py paper/fig/system-architecture.svg
python3 /Users/luo/.codex/skills/nature-figure/scripts/audit_pdf_text.py paper/fig/results-tradeoff.pdf
python3 /Users/luo/.codex/skills/nature-figure/scripts/audit_figure_collisions.py paper/fig/results-tradeoff.pdf --json-out paper/fig/results-tradeoff.collision-audit.json --overlay-pdf paper/fig/results-tradeoff.collision-audit.pdf
python3 /Users/luo/.codex/plugins/cache/openai-bundled/latex/0.2.8/scripts/compile_latex.py /Users/luo/Desktop/AgentDefence/DSCG/paper/main.tex --compiler tectonic --output-directory /Users/luo/Desktop/AgentDefence/DSCG/workshop/artifacts/20261104_paper_v37_update/latex-build --json
python3 /Users/luo/.codex/plugins/cache/openai-bundled/latex/0.2.8/scripts/compile_latex.py /Users/luo/Desktop/AgentDefence/DSCG/workshop/artifacts/20261104_paper_v37_update/overleaf-import/main.tex --compiler tectonic --output-directory /Users/luo/Desktop/AgentDefence/DSCG/workshop/artifacts/20261104_paper_v37_update/overleaf-import-build --json
git diff --check
```

两次独立 Tectonic 编译均为 4 页、无 overfull 或未定义引用；解压 ZIP 后的逐页文本与主 PDF 一致。Tectonic 报告字体形态替代，页面已渲染目视检查；未在 Overleaf 的服务器上实编。图 2 的面板对齐、碰撞与 PDF 文字检查通过；架构图 SVG 审计通过并有与 IEEE 图标题字号有关的非阻塞提醒。结果表各场景和三个总分母已对照 JSON 中的原始计数复算。

| 产物 | SHA-256 |
| --- | --- |
| `paper/main.tex` | `50cbbcbdc08a2d64aafde219fab5f4ae7e70bf6c3294da8bdd00638872453e71` |
| `paper/main.pdf` | `44833baf0c98ef612c18d498403744d637ab32a75ad016144d35963c69a6808b` |
| `paper/DSCG_IWCMC2027_v37.zip` | `9b3275a3770a15ffbfc313c3a1b3d4a30b31cc2bad5f5e13d209482fdebd4c0b` |
| `paper/fig/system-architecture.svg` | `5fd286eab7571d5819d527f047e379f7a07c3ef73a395e94c7eaaedb57a25bd4` |
| `paper/fig/results-tradeoff.pdf` | `2d732e8df049841fe5cd23b55525a87340c357294a7ac4ae90b695feca855c95` |

本次新增在线模型调用 0；报告与诊断不得用于推断未记录调用的用量。E0 未通过，缺少共同模型网格、独立审计器与强近邻对照；本稿仍是工作草稿。下一步：人工核验 Qwen3.5 的两个原生攻击命中与 clean/攻击条件任务损失的轨迹，分别定位规划、L2 和 L3，不据汇总结果预先归因。
