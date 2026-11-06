# GrantBind 稿件更新（2026-11-06）

工作站 `LuodeMacBook-Air.local`，`workshop@c249139ea78f9e9b1b34c2a0fc0f795f680e83a2`。在已有更名、稿件及工程修改之上更新论文和项目文档。历史结果、框架实现、既有 ZIP 和用户实验清单保留。新增模型请求、用量和计分轨迹均为 0。未暂存或提交。

Qwen3.5 图沿用上一轮配对提取结果。攻击对照 2,139 个共同有效键，任务成功 1,805→1,175，原生命中 221→2。Clean 三臂各 97 个共同有效键，原生、同模型 v3.7 和混合组分别成功 90、53、82。混合组的 Qwen3.7 审计器与 v3.8 候选 L2 格式同时变化。报告截图另读取 Qwen3.8 v3.7 攻击臂和 Qwen3.5 混合 clean 臂的归档清单与摘要，分别为 108/108 和 97/97 完成、零任务错误。截图呈现离线报告，历史运行标识和计分用量见 [前次核验](paper_model_results_20261105.md)。

## 离线验证

执行目录为仓库根目录。出图使用 conda `ipi` 的 Python 3.10.21。编译和 PDF 检查使用系统 Python 与 Tectonic 0.17.0。下列为最终核验命令，退出码均为 0。初次浏览器启动在受限环境失败，获准启动本地 headless Chromium 后截图完成。结果图修正了 100% 网格线与文字的相交。

```sh
a="$PWD/workshop/artifacts/20261106_grantbind_paper"
compiler=/Users/luo/.codex/plugins/cache/openai-bundled/latex/0.2.8/scripts/compile_latex.py
MPLCONFIGDIR=/private/tmp/dscg-paper-mpl /opt/miniconda3/envs/ipi/bin/python -B paper/fig/make_qwen35_figure.py
NODE_PATH=/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node "$a/render_run_report.cjs"
python3 -B /Users/luo/.codex/skills/nature-figure/scripts/audit_pdf_text.py paper/fig/qwen35-configurations.pdf
python3 -B /Users/luo/.codex/skills/nature-figure/scripts/audit_figure_collisions.py paper/fig/qwen35-configurations.pdf --json-out "$a/qwen35-collisions.json"
python3 "$compiler" "$PWD/paper/main.tex" --compiler tectonic --output-directory "$a/build" --json
(cd paper && zip -X -q "$a/GrantBind_IWCMC2027_20261106_rev2.zip" main.tex fig/system-architecture.png fig/results-tradeoff.pdf fig/qwen35-configurations.pdf fig/recorded-run-report.png)
unzip -t "$a/GrantBind_IWCMC2027_20261106_rev2.zip"
unzip -oq "$a/GrantBind_IWCMC2027_20261106_rev2.zip" -d "$a/overleaf-import"
python3 "$compiler" "$a/overleaf-import/main.tex" --compiler tectonic --output-directory "$a/overleaf-build" --json
git diff --check
```

交付 [PDF](../../paper/main.pdf)、[Overleaf ZIP](../../paper/GrantBind_IWCMC2027_20261106_rev2.zip)、[Qwen3.5 图](../../paper/fig/qwen35-configurations.pdf) 和 [历史运行报告截图](../../paper/fig/recorded-run-report.png)。编译日志和页面预览位于 `workshop/artifacts/20261106_grantbind_paper/`。跨方法对比与消融待测，Overleaf 服务端编译待确认。
