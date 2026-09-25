(() => {
  const suites = ["workspace", "travel", "banking", "slack"];
  const colors = ["--blue", "--green", "--amber", "--red", "--purple"];
  const shapes = ["circle", "rect", "triangle", "cross", "star"];
  const metricInfo = {
    utility_rate: ["任务效用率 TSR", "%"],
    attack_success_rate: ["攻击成功率 ASR", "%"],
    defense_success_rate: ["防御成功率", "%"],
    total_tokens: ["Token 消耗", "Tokens (K)"],
  };
  let catalog = [];
  let loaded = false;
  let chart = null;

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
    document.querySelector("#tab-history-analysis").addEventListener("click", loadCatalog);
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
      label.append(checkbox, text);
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
    updateControls();
  }

  function addOption(select, value, text) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    select.append(option);
  }

  function updateControls() {
    const view = document.querySelector("#history-chart-type");
    const metric = document.querySelector("#history-metric-select");
    metric.disabled = view.value === "scatter" || view.value === "heatmap";
    const radar = view.querySelector('option[value="radar"]');
    radar.disabled = metric.value === "total_tokens" ||
      document.querySelector("#history-suite-select").value !== "all";
    if (radar.disabled && view.value === "radar") view.value = "bar";
  }

  async function analyze() {
    const status = document.querySelector("#history-analysis-status");
    const ids = Array.from(
      document.querySelectorAll(".history-run-cb:checked"),
      (item) => item.value
    );
    if (!ids.length) {
      status.textContent = "请先选择至少一项历史实验结果。";
      return;
    }
    const suite = document.querySelector("#history-suite-select").value;
    const view = document.querySelector("#history-chart-type").value;
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
      renderAnalysis(data);
    } catch (error) {
      status.textContent = error.message || "历史结果分析失败。";
    }
  }

  function renderAnalysis(result) {
    if (chart) {
      chart.destroy();
      chart = null;
    }
    const experiments = result.experiments || [];
    const rows = experiments.flatMap((run) => run.suites || []);
    renderSummaryTable(experiments);
    if (!rows.length) {
      showEmpty("没有可绘制的指标", "所选结果中没有与当前场景匹配的汇总数据。");
      return;
    }
    const view = document.querySelector("#history-chart-type").value;
    const selectedSuite = document.querySelector("#history-suite-select").value;
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
    const canvas = document.querySelector("#history-chart");
    if (view === "scatter") {
      document.querySelector("#history-chart-title").textContent = "任务效用率与攻击成功率";
      canvas.setAttribute("aria-label", "TSR-ASR 散点图，横轴为攻击成功率，纵轴为任务效用率");
      chart = new Chart(canvas, scatterConfig(experiments));
      return;
    }

    const metricKey = document.querySelector("#history-metric-select").value;
    const [metricTitle, unit] = metricInfo[metricKey];
    const byScenario = selectedSuite === "all";
    const labels = byScenario
      ? suites.filter((name) => rows.some((item) => item.suite_name === name))
      : experiments.map((run) => run.label);
    const chartName = { line: "折线图", bar: "分组柱状", radar: "雷达对比" }[view];
    document.querySelector("#history-chart-title").textContent =
      metricTitle + " · " + suiteTitle + " · " + chartName;
    canvas.setAttribute("aria-label", metricTitle + "，按场景比较 " +
      experiments.map((run) => run.label).join("、"));
    const readMetric = (run, name) => {
      const item = (run.suites || []).find((entry) => entry.suite_name === name);
      if (!item) return null;
      return metricKey === "total_tokens"
        ? item.overhead.total_tokens / 1000
        : item.metrics[metricKey];
    };
    const datasets = byScenario
      ? experiments.map((run, index) =>
        makeMetricDataset(run.label, labels.map((name) => readMetric(run, name)), colorAt(index), view)
      )
      : [makeMetricDataset(
        metricTitle,
        experiments.map((run) => readMetric(run, selectedSuite)),
        colorAt(0),
        view
      )];
    chart = new Chart(canvas, {
      type: view,
      data: { labels, datasets },
      options: view === "radar" ? radarOptions() : cartesianOptions(unit, metricKey !== "total_tokens"),
    });
  }

  function makeMetricDataset(label, data, color, view) {
    const dataset = {
      label,
      data,
      borderColor: color,
      backgroundColor: alpha(color, view === "radar" ? 0.16 : 0.64),
      borderWidth: view === "line" ? 2 : 1,
      spanGaps: false,
    };
    if (view === "line") {
      Object.assign(dataset, {
        tension: 0.28, pointRadius: 3, pointHoverRadius: 5,
        pointBackgroundColor: color, fill: false,
      });
    } else if (view === "bar") {
      Object.assign(dataset, { borderWidth: 0, borderRadius: 2, maxBarThickness: 24 });
    } else {
      Object.assign(dataset, { pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: color });
    }
    return dataset;
  }

  function scatterConfig(experiments) {
    return {
      type: "scatter",
      data: {
        datasets: experiments.map((run, index) => ({
          label: run.label,
          data: (run.suites || []).flatMap((item) => {
            const x = item.metrics.attack_success_rate;
            const y = item.metrics.utility_rate;
            return x === null || y === null ? [] : [{ x, y, suite: item.suite_name }];
          }),
          backgroundColor: colorAt(index),
          borderColor: colorAt(index),
          pointStyle: shapes[index % shapes.length],
          pointRadius: 5,
          pointHoverRadius: 7,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: legendOptions(),
          tooltip: {
            callbacks: {
              label(context) {
                const point = context.raw;
                return context.dataset.label + " · " + point.suite +
                  " · ASR " + point.x + "% / TSR " + point.y + "%";
              },
            },
          },
        },
        scales: { x: scatterScale("ASR (%)"), y: scatterScale("TSR (%)") },
      },
    };
  }

  function scatterScale(title) {
    return {
      type: "linear", min: 0, max: 100,
      title: { display: true, text: title, color: css("--text-muted") },
      ticks: { color: css("--text-secondary"), callback: (value) => value + "%" },
      grid: { color: css("--border") },
    };
  }

  function cartesianOptions(unit, isRate) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: legendOptions(), tooltip: { padding: 10 } },
      datasets: { bar: { categoryPercentage: 0.66, barPercentage: 0.58, maxBarThickness: 24 } },
      scales: {
        x: {
          ticks: { color: css("--text-secondary"), maxRotation: 0, autoSkip: false },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          max: isRate ? 100 : undefined,
          ticks: {
            color: css("--text-secondary"), maxTicksLimit: 6,
            callback: isRate ? (value) => value + "%" : undefined,
          },
          grid: { color: css("--border") },
          title: { display: true, text: unit, color: css("--text-muted") },
        },
      },
    };
  }

  function radarOptions() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: legendOptions(), tooltip: { padding: 10 } },
      scales: {
        r: {
          min: 0, max: 100,
          angleLines: { color: css("--border") },
          grid: { color: css("--border") },
          pointLabels: { color: css("--text-secondary"), font: { size: 11 } },
          ticks: {
            stepSize: 25, color: css("--text-muted"), backdropColor: "transparent",
            callback: (value) => value + "%",
          },
        },
      },
    };
  }

  function legendOptions() {
    return {
      position: "bottom",
      labels: {
        color: css("--text-secondary"), boxWidth: 10, boxHeight: 10,
        padding: 14, usePointStyle: true,
      },
    };
  }

  function renderHeatmap(experiments, suiteTitle) {
    if (chart) {
      chart.destroy();
      chart = null;
    }
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

  function colorAt(index) {
    return css(colors[index % colors.length]);
  }

  function alpha(color, value) {
    const match = color.match(/^#([0-9a-f]{6})$/i);
    if (!match) return color;
    const hex = match[1];
    const red = parseInt(hex.slice(0, 2), 16);
    const green = parseInt(hex.slice(2, 4), 16);
    const blue = parseInt(hex.slice(4, 6), 16);
    return "rgba(" + red + ", " + green + ", " + blue + ", " + value + ")";
  }
})();
