# 历史分析柱体填充调整（2026-10-15）

用户反馈柱顶标记仍然混乱，要求考虑不同填充。本阶段移除柱顶字母、攻击编号和引线，改为颜色区分版本、填充纹理区分攻击；图例使用同一填充生成器，保留攻击名副标题和完整身份悬停。本阶段替代[上一阶段](history_labels_20261015.md)的柱顶文字错层方案，旧源码、报告和证据保留。

- 攻击纹理按已加载目录的全局攻击顺序分配，筛选和切换指标不重新编号；不同版本的相同攻击使用相同纹理。当前四种攻击对应实心、斜线、圆点、横线，另支持其他线型和密度。
- 精确数值保留在悬停中。原始0/null不改写，零值柱仅显示2px细基线，页面明确说明。折线、雷达和散点展示不改变。
- 柱体保留最小可读宽度，密集图表在卡片内滚动；图例纹理块固定28×28px，避免被原有全局Canvas高度规则放大。副标题保持只显示attack_name、12px。

基线revision：`2dcc3d18af59de0136286d1c7090dba7624f6f8f`，工作树已有框架、运行器、文档和dashboard修改，本阶段只编辑三个历史分析展示文件和一份图表测试。初始状态和源码副本见[before.json](../artifacts/20261015_history_patterns/before.json)。本阶段未提交或创建PR，用户results/download的1341份文件大小和修改时间不变。

| 检查命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `node --test tests/test_history_charts.cjs`（实现前） | 1 | 3项预期失败，[red.log](../artifacts/20261015_history_patterns/red.log) |
| `node --test tests/test_history*.cjs tests/test_dashboard_ui.cjs` | 0 | 33/33，[node.log](../artifacts/20261015_history_patterns/node.log) |
| `conda run -n ipi python -m unittest discover -s tests -v` | 0 | 当时工作树303/303，[offline.log](../artifacts/20261015_history_patterns/offline.log) |
| `node --check dashboard/static/js/history_charts.js` | 0 | 语法检查 |
| `node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `git diff --check` | 0 | [diff_check.log](../artifacts/20261015_history_patterns/diff_check.log) |
| `python workshop/artifacts/20261015_history_patterns/validate.py` | 0 | 源码/证据hash、保护输入、报告链接和日志一致性，[validation.json](../artifacts/20261015_history_patterns/validation.json) |

两项原文字碰撞回归随用户撤回的显示方案替换为纹理稳定性和实际插件生命周期检查；原测试字节保存在before_sources。新检查覆盖跨指标/筛选的纹理身份、模型颜色、共享图例填充、无文字绘制、0/null原值和零值基线。限定独立复核未发现确定的重要问题，另跑图表16/16通过。交付时发现三个受保护运行器文件有本阶段之外的并行修改（partial_controls.py、run_benchmark.py、run_partial_benchmark.py）；完整前后hash记录在validation.json，保留这些修改，不把303项快照解释为对这些后续修改的验证。最终重新运行前端33项和语法检查。

浏览器验收使用1440×1000桌面和390×844窄屏，确认图例纹理与柱体一致、隐藏/恢复图例、完整身份悬停、无柱顶文字以及卡片内滚动。窄屏文档宽383px、绘图区内容1099px/可视331px，24个纹理块均为28px，见[几何记录](../artifacts/20261015_history_patterns/mobile_geometry.json)。[桌面截图](../artifacts/20261015_history_patterns/desktop.jpg)为人工验收数据；swatch_css_red文件保留修复前图例放大的失败证据，不作为交付截图。

临时服务仅监听127.0.0.1:9451，读取本阶段人工48份汇总（3版本×4攻击×4场景，12个版本/攻击身份）。旧人工样例缺少原生攻击元数据，本阶段副本补齐attack_type、attack_kind和task_selection.attack；不修改旧样例或生产数据。临时服务已停止，浏览器测试页关闭。0模型调用、0真实benchmark rollout；本阶段不涉及防御、评分、导出身份或研究闸门。纹理有限，超出当前攻击目录规模时仍需结合完整图例和悬停识别；窄屏需局部横向滚动。

下一步：刷新历史分析页，重新生成图表，在实际所选数据上使用颜色和纹理对照。研究状态只追加到technical_route当前链接的research/Experiments/implementation_status.md，不重建旧paper路径。
