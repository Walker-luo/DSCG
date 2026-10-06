(() => {
  const suites = ["workspace", "travel", "banking", "slack"];
  const colors = ["--blue", "--green", "--amber", "--red", "--purple"];
  const historyCharts = window.DSCGHistoryCharts;
  let catalog = [];
  let loaded = false;
  let charts = [];
  let experimentStyles = {};
  let exporting = false;

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelector("#history-select-all").addEventListener("click", () => {
      document.querySelectorAll(".history-run-cb").forEach((item) => { item.checked = true; });
      updateSelection();
    });
    document.querySelector("#history-clear-selection").addEventListener("click", () => {
      document.querySelectorAll(".history-run-cb").forEach((item) => { item.checked = false; });
      updateSelection();
    });
    document.querySelector("#history-run-list").addEventListener("change", updateSelection);
    document.querySelector("#history-suite-select").addEventListener("change", updateControls);
    document.querySelector("#history-chart-type").addEventListener("change", updateControls);
    document.querySelector("#history-metric-select").addEventListener("change", updateControls);
    document.querySelector("#history-analyze").addEventListener("click", analyze);
    document.querySelector("#history-export").addEventListener("click", exportAnalysis);
    document.querySelector("#btn-history-analysis").addEventListener("click", loadCatalog);
    document.querySelector("#history-analysis-modal").addEventListener("shown.bs.modal", () => {
      loadCatalog();
      charts.forEach((chart) => chart.resize());
    });
    loadCatalog();
    updateControls();
    window.setInterval(loadCatalog, 30000);
  });

  async function loadCatalog() {
    const status = document.querySelector("#history-analysis-status");
    try {
      const response = await fetch("/api/history/catalog");
      if (!response.ok) throw new Error("结果目录读取失败");
      const incoming = await response.json();
      const selected = new Set(
        Array.from(document.querySelectorAll(".history-run-cb:checked"), (item) => item.value)
      );
      const chooseLatest = !loaded && incoming.length > 0;
      catalog = Array.isArray(incoming) ? incoming : [];
      experimentStyles = historyCharts.createExperimentStyles(catalog, colors.map(css), experimentStyles);
      renderCatalog(selected, chooseLatest);
      loaded = true;
      if (!catalog.length) status.textContent = "results/ 中尚未找到可识别的实验汇总文件。";
      else if (!status.textContent || status.textContent.startsWith("正在")) {
        status.textContent = "已发现 " + catalog.length + " 项历史实验结果。";
      }
    } catch (error) {
      status.textContent = error.message || "读取历史结果失败。";
    }
  }

  function renderCatalog(selected, chooseLatest) {
    const list = document.querySelector("#history-run-list");
    list.replaceChildren();
    document.querySelector("#history-catalog-count").textContent = catalog.length + " 项结果";
    if (!catalog.length) {
      const empty = document.createElement("div");
      empty.className = "empty-state history-list-empty";
      empty.textContent = "尚无可分析的结果";
      list.append(empty);
      updateSelection();
      return;
    }
    catalog.forEach((run, index) => {
      const label = document.createElement("label");
      label.className = "history-run-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "form-check-input history-run-cb";
      checkbox.value = run.id;
      checkbox.checked = selected.has(run.id) || (chooseLatest && index === 0);
      const text = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = run.label || run.source;
      const detail = document.createElement("small");
      detail.textContent = (run.result_type || "results") + " · " + run.source + " · " +
        (run.suites || []).map((item) => item.suite_name).join(", ");
      text.append(title, detail);
      const swatch = document.createElement("i");
      swatch.className = "history-run-swatch";
      swatch.setAttribute("aria-hidden", "true");
      swatch.style.backgroundColor = experimentStyles[run.id].color;
      label.append(checkbox, swatch, text);
      list.append(label);
    });
    updateSelection();
  }

  function updateSelection() {
    const selected = new Set(
      Array.from(document.querySelectorAll(".history-run-cb:checked"), (item) => item.value)
    );
    document.querySelector("#history-selection-count").textContent = selected.size + " 项已选";
    const available = new Set();
    catalog.forEach((run) => {
      if (selected.has(run.id)) (run.suites || []).forEach((item) => available.add(item.suite_name));
    });
    const select = document.querySelector("#history-suite-select");
    const previous = select.value;
    select.replaceChildren();
    addOption(select, "all", "全部场景");
    suites.forEach((suite) => {
      if (available.has(suite)) addOption(select, suite, suite);
    });
    select.value = available.has(previous) ? previous : "all";
    updateExportButton();
    updateControls();
  }

  function selectedRunIds() {
    return Array.from(document.querySelectorAll(".history-run-cb:checked"), (item) => item.value);
  }

  function updateExportButton() {
    document.querySelector("#history-export").disabled = exporting || !selectedRunIds().length;
  }

  async function exportAnalysis() {
    if (exporting) return;
    const status = document.querySelector("#history-analysis-status");
    const ids = selectedRunIds();
    if (!ids.length) {
      status.textContent = "请先选择至少一项历史实验结果。";
      return;
    }
    const suite = document.querySelector("#history-suite-select").value;
    const button = document.querySelector("#history-export");
    const originalLabel = button.innerHTML;
    exporting = true;
    updateExportButton();
    button.setAttribute("aria-busy", "true");
    button.textContent = "正在打包…";
    status.textContent = "正在打包所选实验的 ASR / TSR 和任务明细…";
    try {
      const response = await fetch("/api/history/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_ids: ids, suites: suite === "all" ? [] : [suite] }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || "分析数据导出失败");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const disposition = response.headers.get("Content-Disposition") || "";
      const filename = disposition.match(/filename="?([a-zA-Z0-9_.-]+\.zip)"?/);
      link.href = url;
      link.download = filename ? filename[1] : "dscg-history-analysis.zip";
      document.body.append(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 10000);
      status.textContent = "已生成 " + ids.length + " 项实验的分析数据，已开始下载 ZIP。解压后可将 analysis.json 交给 agent。";
    } catch (error) {
      status.textContent = error.message || "分析数据导出失败，请重试。";
    } finally {
      exporting = false;
      button.innerHTML = originalLabel;
      button.removeAttribute("aria-busy");
      updateExportButton();
    }
  }

  function addOption(select, value, text) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  }

  function updateControls() {
    const view = document.querySelector("#history-chart-type");
    const metrics = selectedMetricKeys();
    const fixedMetrics = view.value === "scatter" || view.value === "heatmap";
    document.querySelector("#history-metric-select").disabled = fixedMetrics;
    const radar = view.querySelector('option[value="radar"]');
    radar.disabled = !historyCharts.canUseRadar(metrics, document.querySelector("#history-suite-select").value);
    if (radar.disabled && view.value === "radar") view.value = "bar";
    document.querySelector("#history-analyze").disabled = !fixedMetrics && !metrics.length;
    document.querySelector("#history-metric-hint").textContent = fixedMetrics
      ? (view.value === "scatter" ? "散点图固定比较 ASR 与 TSR。" : "热图固定展示逐任务效用结果。")
      : !metrics.length ? "请至少选择一个指标。"
        : "每个指标单独成图，同一实验颜色一致；雷达图仅支持全部场景的百分比指标。";
  }

  function selectedMetricKeys() {
    return Array.from(document.querySelectorAll(".history-metric-cb:checked"), (item) => item.value);
  }

  async function analyze() {
    const status = document.querySelector("#history-analysis-status");
    const ids = selectedRunIds();
    if (!ids.length) {
      status.textContent = "请先选择至少一项历史实验结果。";
      return;
    }
    const suite = document.querySelector("#history-suite-select").value;
    const view = document.querySelector("#history-chart-type").value;
    const settings = { suite, view, metrics: selectedMetricKeys() };
    status.textContent = "正在汇总所选结果…";
    try {
      const response = await fetch("/api/history/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_ids: ids,
          suites: suite === "all" ? [] : [suite],
          include_task_records: view === "heatmap",
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "历史结果分析失败");
      renderAnalysis(data, settings);
    } catch (error) {
      status.textContent = error.message || "历史结果分析失败。";
    }
  }

  function clearCharts() {
    charts.forEach((chart) => chart.destroy());
    charts = [];
    document.querySelector("#history-canvas-wrap").replaceChildren();
  }

  function renderAnalysis(result, settings) {
    clearCharts();
    const experiments = result.experiments || [];
    const rows = experiments.flatMap((run) => run.suites || []);
    renderSummaryTable(experiments);
    if (!rows.length) {
      showEmpty("没有可绘制的指标", "所选结果中没有与当前场景匹配的汇总数据。");
      return;
    }
    const { view, metrics, suite: selectedSuite } = settings;
    const suiteTitle = selectedSuite === "all" ? "全部场景" : selectedSuite;
    const status = document.querySelector("#history-analysis-status");
    document.querySelector("#history-source-caption").textContent =
      experiments.length + " 项实验 · " + rows.length + " 个场景结果";
    status.textContent = "已载入 " + experiments.length + " 项实验、" + rows.length + " 个场景结果。";
    if (view === "heatmap") {
      renderHeatmap(experiments, suiteTitle);
      return;
    }

    const wrap = document.querySelector("#history-canvas-wrap");
    const heatmap = document.querySelector("#history-heatmap-container");
    const chartContainer = document.querySelector(".history-chart-container");
    wrap.hidden = false;
    heatmap.hidden = true;
    chartContainer.classList.add("is-ready");
    if (view === "scatter") {
      document.querySelector("#history-chart-title").textContent = "任务效用率与攻击成功率";
      renderChartPanel(wrap, "scatter", "TSR-ASR 散点", "横轴为攻击成功率，纵轴为任务效用率", historyCharts.scatterConfig(experiments, chartTheme()));
      return;
    }

    if (!metrics.length) {
      showEmpty("尚未选择指标", "请至少选择一个指标，再生成分析。");
      return;
    }
    const chartName = { line: "折线图", bar: "分组柱状", radar: "雷达对比" }[view];
    document.querySelector("#history-chart-title").textContent =
      "指标对比 · " + suiteTitle + " · " + chartName + " · " + metrics.length + " 个指标";
    const panels = historyCharts.metricConfigs(experiments, {
      metrics, view, suite: selectedSuite, theme: chartTheme(),
    });
    panels.forEach((panel) => renderChartPanel(wrap, panel.metric, panel.title,
      panel.title + "，" + suiteTitle + "，比较 " + experiments.map((run) => run.label).join("、"), panel.config));
  }

  function renderChartPanel(wrap, key, title, description, config) {
    const panel = document.createElement("section");
    panel.className = "history-chart-card";
    panel.dataset.metric = key;
    const heading = document.createElement("h3");
    heading.id = "history-chart-title-" + key;
    heading.textContent = title;
    panel.setAttribute("aria-labelledby", heading.id);
    const plot = document.createElement("div");
    plot.className = "history-chart-plot";
    const canvas = document.createElement("canvas");
    canvas.id = "history-chart-" + key;
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", description);
    plot.append(canvas);
    panel.append(heading, plot);
    wrap.append(panel);
    charts.push(new Chart(canvas, config));
  }

  function chartTheme() {
    return {
      colors: colors.map(css),
      experimentStyles,
      text: css("--text-secondary"), muted: css("--text-muted"), border: css("--border"),
    };
  }

  function renderHeatmap(experiments, suiteTitle) {
    const wrap = document.querySelector("#history-canvas-wrap");
    const container = document.querySelector(".history-chart-container");
    const target = document.querySelector("#history-heatmap-container");
    wrap.hidden = true;
    target.hidden = false;
    container.classList.add("is-ready");
    target.replaceChildren();
    document.querySelector("#history-chart-title").textContent = "任务效用结果 · " + suiteTitle;

    const matrix = new Map();
    let truncated = false;
    experiments.forEach((run) => {
      (run.suites || []).forEach((item) => {
        (item.task_records || []).forEach((record) => {
          const key = JSON.stringify([item.suite_name, record.user_task_id, record.injection_task_id]);
          if (!matrix.has(key)) {
            matrix.set(key, {
              suite: item.suite_name, user: record.user_task_id,
              injection: record.injection_task_id, values: new Map(),
            });
          }
          matrix.get(key).values.set(run.id, record.utility_success);
        });
        truncated = truncated || item.task_records_truncated === true;
      });
    });
    if (!matrix.size) {
      showEmpty("没有任务级记录", "所选结果没有 detailed_results.csv 或结构化任务记录。");
      document.querySelector("#history-chart-title").textContent = "任务效用结果 · " + suiteTitle;
      return;
    }

    const table = document.createElement("table");
    table.className = "table table-dark table-hover table-sm";
    const head = document.createElement("thead");
    const heading = document.createElement("tr");
    const taskHeader = document.createElement("th");
    taskHeader.scope = "col";
    taskHeader.textContent = "场景 / 用户任务 / 注入任务";
    heading.append(taskHeader);
    experiments.forEach((run) => {
      const cell = document.createElement("th");
      cell.scope = "col";
      cell.textContent = run.label;
      cell.setAttribute("aria-label", run.label + " · " + run.source);
      heading.append(cell);
    });
    head.append(heading);
    table.append(head);
    const body = document.createElement("tbody");
    const sorted = Array.from(matrix.values()).sort((left, right) =>
      suites.indexOf(left.suite) - suites.indexOf(right.suite) ||
      left.user.localeCompare(right.user, undefined, { numeric: true }) ||
      left.injection.localeCompare(right.injection, undefined, { numeric: true })
    );
    sorted.forEach((task) => {
      const row = document.createElement("tr");
      const name = document.createElement("th");
      name.scope = "row";
      name.textContent = task.suite + " / " + task.user + " / " + task.injection;
      row.append(name);
      experiments.forEach((run) => {
        const value = task.values.get(run.id);
        const cell = document.createElement("td");
        cell.className = "history-result-cell";
        cell.textContent = value === true ? "成功" : value === false ? "失败" : "无数据";
        cell.classList.add(value === true ? "utility-pass" : value === false ? "utility-fail" : "utility-missing");
        cell.setAttribute("aria-label", run.label + "：" + cell.textContent);
        row.append(cell);
      });
      body.append(row);
    });
    table.append(body);
    target.append(table);
    const legend = document.createElement("p");
    legend.className = "history-heatmap-legend";
    legend.textContent = "成功：效用任务通过　失败：效用任务未通过　无数据：该实验未覆盖此任务";
    target.append(legend);
    document.querySelector("#history-analysis-status").textContent =
      "热图包含 " + matrix.size + " 个任务组合。" +
      (truncated ? " 部分任务记录受接口上限截断。" : "");
  }

  function renderSummaryTable(experiments) {
    const body = document.querySelector("#history-summary-table tbody");
    body.replaceChildren();
    const rows = experiments.flatMap((run) =>
      (run.suites || []).map((item) => ({ run, item }))
    );
    if (!rows.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 7;
      cell.textContent = "尚无分析数据";
      row.append(cell);
      body.append(row);
      return;
    }
    rows.forEach(({ run, item }) => {
      const row = document.createElement("tr");
      const nameCell = document.createElement("td");
      const name = document.createElement("strong");
      name.textContent = run.label;
      const source = document.createElement("small");
      source.className = "history-table-source";
      source.textContent = run.source;
      nameCell.append(name, source);
      row.append(nameCell);
      addCell(row, item.suite_name);
      addCell(row, formatRate(item.metrics.utility_rate));
      addCell(row, formatRate(item.metrics.attack_success_rate));
      addCell(row, formatRate(item.metrics.defense_success_rate));
      addCell(row, Number(item.overhead.total_tokens || 0).toLocaleString("en-US"));
      addCell(row, (item.task_counts.utility_passed || 0) + " / " + (item.task_counts.total_tasks || 0));
      body.append(row);
    });
  }

  function addCell(row, text) {
    const cell = document.createElement("td");
    cell.textContent = text;
    row.append(cell);
  }

  function formatRate(value) {
    return value === null || value === undefined ? "N/A" : Number(value).toFixed(2);
  }

  function showEmpty(title, description) {
    clearCharts();
    document.querySelector("#history-canvas-wrap").hidden = true;
    document.querySelector("#history-heatmap-container").hidden = true;
    document.querySelector(".history-chart-container").classList.remove("is-ready");
    const empty = document.querySelector("#history-chart-empty");
    empty.querySelector("strong").textContent = title;
    empty.querySelector("span").textContent = description;
    document.querySelector("#history-analysis-status").textContent = description;
  }

  function css(token) {
    return getComputedStyle(document.documentElement).getPropertyValue(token).trim() || "#74817d";
  }

})();
