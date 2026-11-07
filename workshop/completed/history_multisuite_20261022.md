# 历史分析场景多选与默认指标（2026-10-22）

用户要求场景像指标一样多选，指标移除防御成功率，默认TSR、ASR、Token消耗全部勾选。本次复用原指标复选框样式和后端suites数组接口，未增加依赖或后端接口。

- 默认选中已勾选运行的全部可用场景；刷新保留子集及明确清空。非空旧选择在切换结果后全部不可用时，选择新结果的全部可用场景。
- 分析和下载显式提交勾选场景，空选择时禁用按钮且请求函数直接拒绝，防止API的空数组语义意外变成全部场景。过期分析检查包括场景数组。
- 多场景沿用各场景独立绘图，单场景沿用版本对比；散点、热图和明细接收相同的后端场景过滤。雷达需多个场景且不包含Token。
- 指标选项仅保留TSR、ASR、Token且默认全选；原结果／导出中的其他字段不删除。

基线revision `60f3da3fd7071380057e4daca4ad70edaac98e9c`，开始时工作树干净。只修改history.js、history.html及两份测试，新增本报告；未提交。882份其他已跟踪文件SHA不变，14841份用户results/download文件大小及修改时间不变。源码和产物SHA、精确工作树见[validation.json](../artifacts/20261022_history_multisuite/validation.json)，原字节见同目录before_sources。

| 命令（DSCG根目录） | 退出码 | 结果 |
| --- | --- | --- |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/test_history_ui_selection.cjs`，实现前 | 1 | 3项预期失败；red_node.log |
| `conda run --no-capture-output -n ipi python -B -m unittest discover -s tests -p test_dashboard_history.py -v`，实现前 | 1 | 默认指标用例失败；red_python.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/test_history_ui_selection.cjs`，实现后 | 0 | 4/4；green_node.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 0 | 49/49；node.log |
| `conda run --no-capture-output -n ipi python -B -u -m unittest discover -s tests -v` | 0 | 663项，653通过、10跳过；ipi.log |
| `conda run --no-capture-output -n ipi-agentdyn python -B -u -m unittest discover -s tests -v` | 0 | 667项，664通过、3跳过；ipi_agentdyn.log |
| `conda run --no-capture-output -n ipi env PYTHONPATH=. python -B workshop/artifacts/20261022_history_multisuite/verify_api.py` | 0 | 3份人工summary，分析及ZIP仅保留2个指定场景；api.log |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --check dashboard/static/js/history.js` | 0 | 语法检查 |
| `git diff --check` | 0 | 空输出 |
| `python workshop/artifacts/20261022_history_multisuite/delivery.py` | 0 | 保护输入、证据及状态准备检查 |

上述日志均位于workshop/artifacts/20261022_history_multisuite/。新增回归运行真实模板响应、生产事件／请求函数及绘图配置，验证默认3指标、场景子集与清空保持、分析／下载范围、过期请求、独立场景数值和单场景版本轴。限定独立只读复核未发现可行动问题；复核环境缺少node，测试结果以上述主执行日志为准。

0模型调用、0真实benchmark rollout；3份人工summary和ZIP仅作API验收，不是效能分母。未做浏览器视觉验收，控件沿用现有样式。没有改防御、默认模型、评分、用户结果或研究闸门。

下一步：刷新历史页，勾选需要比较的场景并生成分析；三个指标默认选中，可按需取消。
