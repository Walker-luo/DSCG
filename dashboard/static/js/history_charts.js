((root) => {
  const suites = ["workspace", "travel", "banking", "slack"];
  const metricInfo = {
    utility_rate: ["任务效用率 TSR", "%"],
    attack_success_rate: ["攻击成功率 ASR", "%"],
    defense_success_rate: ["防御成功率", "%"],
    total_tokens: ["Token 消耗", "Tokens (K)"],
  };
  const shapes = ["circle", "rect", "triangle", "cross", "star"];
  const dashes = [[], [6, 4], [2, 3], [10, 3, 2, 3]];
  const defaultTheme = {
    colors: ["#91b8ee", "#48c6a4", "#e4b66a", "#ed7474", "#b89ae4"],
    text: "#b2bfba", muted: "#74817d", border: "#303b35",
  };

  function alpha(color, opacity) {
    if (color.startsWith("hsl(")) return color.replace("hsl(", "hsla(").replace(")", ", " + opacity + ")");
    const match = color.match(/^#([0-9a-f]{6})$/i);
    if (!match) return color;
    const channels = [0, 2, 4].map((offset) => parseInt(match[1].slice(offset, offset + 2), 16));
    return "rgba(" + channels.join(", ") + ", " + opacity + ")";
  }

  function experimentKey(run) {
    return run.id || run.source || run.label;
  }

  function createExperimentStyles(experiments, colors = defaultTheme.colors, previousStyles = {}) {
    const styles = Object.assign(Object.create(null), previousStyles);
    experiments.forEach((run) => {
      const key = experimentKey(run);
      if (Object.hasOwn(styles, key)) return;
      const index = Object.keys(styles).length;
      styles[key] = {
        color: colors[index] || "hsl(" + ((index * 137.508) % 360).toFixed(2) + ", 62%, 62%)",
        pointStyle: shapes[index % shapes.length],
        borderDash: dashes[index % dashes.length],
      };
    });
    return styles;
  }

  function resolveTheme(experiments, customTheme) {
    const theme = { ...defaultTheme, ...customTheme };
    theme.experimentStyles = createExperimentStyles(experiments, theme.colors, theme.experimentStyles);
    return theme;
  }

  function percentScale(title, values, theme) {
    const finite = values.filter(Number.isFinite);
    const lower = Math.min(0, ...finite);
    const upper = Math.max(100, ...finite);
    const padding = Math.max(5, (upper - lower) * 0.05);
    return {
      type: "linear", min: lower - padding, max: upper + padding,
      title: { display: true, text: title, color: theme.muted },
      afterBuildTicks(scale) {
        // Keep the meaningful endpoint ticks: Chart.js can replace them with the padded bounds.
        scale.ticks = [0, 25, 50, 75, 100].map((value) => ({ value }));
      },
      ticks: {
        color: theme.text, stepSize: 25, autoSkip: false,
        callback: (value) => value >= 0 && value <= 100 ? value + "%" : "",
      },
      grid: { color: theme.border },
    };
  }

  function tokenScale(theme) {
    return {
      type: "linear", beginAtZero: true, grace: "5%",
      title: { display: true, text: "Tokens (K)", color: theme.muted },
      ticks: { color: theme.text, maxTicksLimit: 6 },
      grid: { color: theme.border },
    };
  }

  function options(theme) {
    return {
      responsive: true, maintainAspectRatio: false,
      layout: { padding: 12 },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: theme.text, boxWidth: 10, boxHeight: 10, padding: 14, usePointStyle: true,
            generateLabels(chart) {
              return chart.data.datasets.map((dataset, index) => ({
                text: dataset.label, fillStyle: dataset.borderColor, strokeStyle: dataset.borderColor,
                fontColor: theme.text, lineWidth: dataset.borderWidth || 1,
                pointStyle: dataset.pointStyle, lineDash: dataset.borderDash || [],
                hidden: !chart.isDatasetVisible(index), datasetIndex: index,
              }));
            },
          },
        },
        tooltip: { padding: 10 },
      },
    };
  }

  function canUseRadar(metrics, suite) {
    return metrics.length > 0 && suite === "all" && !metrics.includes("total_tokens");
  }

  function metricConfigs(experiments, { metrics, view, suite, theme: customTheme }) {
    if (!metrics.length || metrics.some((key) => !Object.hasOwn(metricInfo, key))) {
      throw new Error("请至少选择一个有效指标。");
    }
    if (view === "radar" && !canUseRadar(metrics, suite)) {
      throw new Error("雷达图仅支持全部场景的百分比指标。");
    }
    const theme = resolveTheme(experiments, customTheme);
    return metrics.map((metric) => ({
      metric, title: metricInfo[metric][0],
      config: metricConfig(experiments, { metric, view, suite, theme }),
    }));
  }

  function metricConfig(experiments, { metric, view, suite, theme }) {
    const byScenario = suite === "all";
    const labels = byScenario
      ? suites.filter((name) => experiments.some((run) => run.suites.some((item) => item.suite_name === name)))
      : experiments.map((run) => run.label);
    const readMetric = (run, name, key) => {
      const item = run.suites.find((entry) => entry.suite_name === name);
      if (!item) return null;
      return key === "total_tokens" ? item.overhead.total_tokens / 1000 : item.metrics[key] ?? null;
    };
    const datasets = experiments.map((run, index) => {
      const style = theme.experimentStyles[experimentKey(run)];
      const color = style.color;
      const data = byScenario ? labels.map((name) => readMetric(run, name, metric))
        : experiments.map((_, position) => position === index ? readMetric(run, suite, metric) : null);
      const dataset = {
        label: run.label, data, metricKey: metric, borderColor: color,
        backgroundColor: view === "radar" ? alpha(color, 0.16) : color,
        borderWidth: view === "line" ? 2 : 1, spanGaps: false,
        pointStyle: style.pointStyle,
      };
      if (view !== "radar") dataset.yAxisID = "y";
      if (view === "bar") {
        Object.assign(dataset, { borderWidth: 0, borderRadius: 2, maxBarThickness: 24, grouped: byScenario });
      } else {
        Object.assign(dataset, {
          pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: color,
          borderDash: style.borderDash,
          ...(view === "line" ? { tension: 0.28, fill: false } : {}),
        });
      }
      return dataset;
    });
    const chartOptions = options(theme);
    chartOptions.plugins.tooltip.callbacks = {
      label(context) {
        const value = context.raw;
        return context.dataset.label + "：" + (value === null ? "无数据" : value + (context.dataset.metricKey === "total_tokens" ? " K tokens" : "%"));
      },
    };
    if (view === "radar") {
      chartOptions.scales = {
        r: {
          min: 0, max: 110,
          angleLines: { color: theme.border }, grid: { color: theme.border },
          pointLabels: { color: theme.text, font: { size: 11 } },
          ticks: {
            stepSize: 25, color: theme.muted, backdropColor: "transparent",
            callback: (value) => value <= 100 ? value + "%" : "",
          },
        },
      };
    } else {
      chartOptions.interaction = { mode: "index", intersect: false };
      chartOptions.datasets = { bar: { categoryPercentage: 0.66, barPercentage: 0.58, maxBarThickness: 24 } };
      chartOptions.scales = {
        x: { offset: true, ticks: { color: theme.text, maxRotation: 0, autoSkip: false }, grid: { display: false } },
        y: metric === "total_tokens" ? tokenScale(theme) : percentScale("%", datasets.flatMap((row) => row.data), theme),
      };
      if (!byScenario) {
        chartOptions.scales.x.ticks.callback = function (value) {
          const label = this.getLabelForValue(value);
          if (label.length <= 18) return label;
          const separator = label.indexOf("_");
          const split = separator > 0 && separator <= 18 ? separator : 18;
          const rest = label.slice(split + (split === separator ? 1 : 0));
          return [label.slice(0, split), rest.length > 24 ? rest.slice(0, 23) + "…" : rest];
        };
      }
    }
    return { type: view, data: { labels, datasets }, options: chartOptions };
  }

  function scatterConfig(experiments, customTheme) {
    const theme = resolveTheme(experiments, customTheme);
    const datasets = experiments.map((run) => ({
      label: run.label,
      data: run.suites.flatMap((item) => {
        const x = item.metrics.attack_success_rate;
        const y = item.metrics.utility_rate;
        return Number.isFinite(x) && Number.isFinite(y) ? [{ x, y, suite: item.suite_name }] : [];
      }),
      backgroundColor: theme.experimentStyles[experimentKey(run)].color,
      borderColor: theme.experimentStyles[experimentKey(run)].color,
      pointStyle: theme.experimentStyles[experimentKey(run)].pointStyle, pointRadius: 5, pointHoverRadius: 7,
    }));
    const points = datasets.flatMap((dataset) => dataset.data);
    const chartOptions = options(theme);
    chartOptions.plugins.tooltip.callbacks = {
      label(context) {
        return context.dataset.label + " · " + context.raw.suite + " · ASR " + context.raw.x + "% / TSR " + context.raw.y + "%";
      },
    };
    chartOptions.scales = {
      x: percentScale("ASR (%)", points.map((point) => point.x), theme),
      y: percentScale("TSR (%)", points.map((point) => point.y), theme),
    };
    return { type: "scatter", data: { datasets }, options: chartOptions };
  }

  const api = { metricInfo, metricConfigs, scatterConfig, canUseRadar, createExperimentStyles };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DSCGHistoryCharts = api;
})(typeof window === "undefined" ? globalThis : window);
