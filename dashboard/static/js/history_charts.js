((root) => {
  const metricInfo = {
    utility_rate: ["任务效用率 TSR", "%"],
    attack_success_rate: ["攻击成功率 ASR", "%"],
    defense_success_rate: ["防御成功率", "%"],
    total_tokens: ["已记录总 Token（主模型 + 审计）", "Tokens (K)"],
  };
  const shapes = ["circle", "rect", "triangle", "cross", "star"];
  const dashes = [[], [6, 4], [2, 3], [10, 3, 2, 3]];
  const defaultTheme = {
    colors: ["#91b8ee", "#e4b66a", "#b89ae4", "#48c6a4", "#ed7474"],
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

  function badgeFor(index) {
    let badge = "", number = index + 1;
    while (number > 0) {
      number--;
      badge = String.fromCharCode(65 + number % 26) + badge;
      number = Math.floor(number / 26);
    }
    return badge;
  }

  function createExperimentStyles(experiments, colors = defaultTheme.colors, previousStyles = {}) {
    const styles = Object.create(null);
    const models = new Map();
    const runsById = new Map(experiments.map(run => [experimentKey(run), run]));
    Object.entries(previousStyles).forEach(([key, previous]) => {
      const run = runsById.get(key);
      const modelKey = previous.modelKey || run?.model_group || run?.model_suffix || key;
      const index = models.size;
      const style = models.get(modelKey) || {
        pointStyle: shapes[index % shapes.length], borderDash: dashes[index % dashes.length],
        ...previous, modelKey, badge: previous.badge || badgeFor(index),
      };
      models.set(modelKey, style);
      styles[key] = style;
    });
    experiments.forEach((run) => {
      const key = experimentKey(run);
      if (Object.hasOwn(styles, key)) return;
      const modelKey = run.model_group || run.model_suffix || key;
      if (models.has(modelKey)) { styles[key] = models.get(modelKey); return; }
      const index = models.size;
      const style = {
        modelKey, badge: badgeFor(index),
        color: colors[index] || "hsl(" + ((index * 137.508) % 360).toFixed(2) + ", 62%, 62%)",
        pointStyle: shapes[index % shapes.length],
        borderDash: dashes[index % dashes.length],
      };
      styles[key] = style;
      models.set(modelKey, style);
    });
    return styles;
  }

  function describeExperiment(run) {
    const model = run.model_suffix || run.model_group;
    const separator = model ? model.indexOf("_") : -1;
    return {
      label: separator >= 0 ? model.slice(separator + 1) : model || run.label || experimentKey(run),
      fullLabel: run.label || [run.model_group || model || experimentKey(run), run.attack_name].filter(Boolean).join(" / "),
      subtitle: run.attack_name || "未记录攻击",
    };
  }

  const patternCache = new WeakMap();
  const patternKinds = ["diagonal", "dots", "horizontal", "crosshatch", "vertical", "reverse-diagonal"];

  function createBarFill(ctx, pattern, color, background = "#171d19") {
    if (!pattern || pattern.kind === "solid") return color;
    let cache = patternCache.get(ctx);
    if (!cache) { cache = new Map(); patternCache.set(ctx, cache); }
    const key = [pattern.kind, pattern.size, color, background].join("|");
    if (cache.has(key)) return cache.get(key);
    const tile = ctx.canvas.ownerDocument.createElement("canvas");
    const size = pattern.size;
    tile.width = tile.height = size;
    const ink = tile.getContext("2d");
    ink.fillStyle = background;
    ink.fillRect(0, 0, size, size);
    ink.fillStyle = alpha(color, 0.2);
    ink.fillRect(0, 0, size, size);
    ink.strokeStyle = ink.fillStyle = color;
    ink.lineWidth = 1.5;
    ink.beginPath();
    if (pattern.kind === "dots") {
      for (const x of [size / 4, size * 3 / 4]) for (const y of [size / 4, size * 3 / 4]) {
        ink.beginPath(); ink.arc(x, y, Math.max(0.8, size / 10), 0, Math.PI * 2); ink.fill();
      }
    } else {
      if (["diagonal", "crosshatch"].includes(pattern.kind)) {
        for (const x of [-size, 0, size]) { ink.moveTo(x, size); ink.lineTo(x + size, 0); }
      }
      if (["reverse-diagonal", "crosshatch"].includes(pattern.kind)) {
        for (const x of [-size, 0, size]) { ink.moveTo(x, 0); ink.lineTo(x + size, size); }
      }
      if (pattern.kind === "horizontal") {
        for (const y of [size / 3, size * 2 / 3]) { ink.moveTo(0, y); ink.lineTo(size, y); }
      }
      if (pattern.kind === "vertical") {
        for (const x of [size / 3, size * 2 / 3]) { ink.moveTo(x, 0); ink.lineTo(x, size); }
      }
      ink.stroke();
    }
    const fill = ctx.createPattern(tile, "repeat") || color;
    cache.set(key, fill);
    return fill;
  }

  const barPatterns = {
    id: "historyBarPatterns",
    beforeUpdate(chart) {
      if (chart.config.type !== "bar") return;
      const background = chart.options.plugins.historyBarPatterns?.backgroundColor;
      chart.data.datasets.forEach(dataset => {
        dataset.backgroundColor = createBarFill(chart.ctx, dataset.fillPattern, dataset.borderColor, background);
      });
    },
  };

  function resolveTheme(experiments, customTheme) {
    const theme = { ...defaultTheme, ...customTheme };
    theme.experimentStyles = createExperimentStyles(experiments, theme.colors, theme.experimentStyles);
    theme.attackNames = Array.from(new Set([...(theme.attackNames || []), ...experiments.map(run => run.attack_name).filter(Boolean)])).sort();
    const attacksByModel = new Map();
    experiments.forEach(run => {
      const key = theme.experimentStyles[experimentKey(run)].modelKey;
      if (!attacksByModel.has(key)) attacksByModel.set(key, new Set());
      attacksByModel.get(key).add(run.attack_name);
    });
    theme.multiAttackModels = new Set(Array.from(attacksByModel).filter(([, attacks]) => attacks.size > 1).map(([key]) => key));
    return theme;
  }

  function chartIdentity(run, theme) {
    const style = theme.experimentStyles[experimentKey(run)];
    const identity = describeExperiment(run);
    const multiple = theme.multiAttackModels.has(style.modelKey);
    const attackIndex = theme.attackNames.indexOf(run.attack_name);
    return {
      label: identity.label + (multiple ? " · " + run.attack_name : ""),
      legendLabel: identity.label,
      fullLabel: identity.fullLabel + (run.source ? " · " + run.source : ""),
      legendSubtitle: identity.subtitle,
      identityBadge: style.badge + (multiple ? String(attackIndex + 1) : ""),
      fillPattern: attackIndex <= 0 ? {kind: "solid", size: 12} : {
        kind: patternKinds[(attackIndex - 1) % patternKinds.length],
        size: Math.max(4, 12 - Math.floor((attackIndex - 1) / patternKinds.length) * 4),
      },
      pointStyle: multiple ? shapes[attackIndex % shapes.length] : style.pointStyle,
      borderDash: multiple ? dashes[attackIndex % dashes.length] : style.borderDash,
    };
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
        historyBarPatterns: { backgroundColor: theme.background },
        legend: {
          position: "bottom",
          labels: {
            color: theme.text, boxWidth: 10, boxHeight: 10, padding: 14, usePointStyle: true,
            generateLabels(chart) {
              return chart.data.datasets.map((dataset, index) => ({
                text: dataset.label, fillStyle: chart.config?.type === "bar" ? dataset.backgroundColor : dataset.borderColor, strokeStyle: dataset.borderColor,
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
      ? Array.from(new Set(experiments.flatMap(run => run.suites.map(item => item.suite_name))))
      : experiments.map((run) => chartIdentity(run, theme).label);
    const readMetric = (run, name, key) => {
      const item = run.suites.find((entry) => entry.suite_name === name);
      if (!item) return null;
      return key === "total_tokens" ? item.overhead.total_tokens / 1000 : item.metrics[key] ?? null;
    };
    const datasets = experiments.map((run, index) => {
      const style = theme.experimentStyles[experimentKey(run)];
      const identity = chartIdentity(run, theme);
      const color = style.color;
      const data = byScenario ? labels.map((name) => readMetric(run, name, metric))
        : experiments.map((_, position) => position === index ? readMetric(run, suite, metric) : null);
      const dataset = {
        ...identity, data, metricKey: metric, borderColor: color,
        backgroundColor: view === "radar" ? alpha(color, 0.16) : color,
        borderWidth: view === "line" ? 2 : 1, spanGaps: false,
      };
      if (view !== "radar") dataset.yAxisID = "y";
      if (view === "bar") {
        Object.assign(dataset, { borderWidth: 1, borderSkipped: false, borderRadius: 1,
          minBarLength: 2, maxBarThickness: 24, grouped: byScenario });
      } else {
        Object.assign(dataset, {
          pointRadius: 4, pointHoverRadius: 6, pointBackgroundColor: color,
          borderDash: identity.borderDash,
          ...(view === "line" ? { tension: 0.28, fill: false } : {}),
        });
      }
      return dataset;
    });
    const chartOptions = options(theme);
    chartOptions.plugins.tooltip.callbacks = {
      label(context) {
        const value = context.raw;
        return context.dataset.fullLabel + "：" + (value === null ? "无数据" : value + (context.dataset.metricKey === "total_tokens" ? " K tokens" : "%"));
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
    return { type: view, data: { labels, datasets }, options: chartOptions, plugins: view === "bar" ? [barPatterns] : [] };
  }

  function scatterConfig(experiments, customTheme) {
    const theme = resolveTheme(experiments, customTheme);
    const datasets = experiments.map((run) => ({
      ...chartIdentity(run, theme),
      data: run.suites.flatMap((item) => {
        const x = item.metrics.attack_success_rate;
        const y = item.metrics.utility_rate;
        return Number.isFinite(x) && Number.isFinite(y) ? [{ x, y, suite: item.suite_name }] : [];
      }),
      backgroundColor: theme.experimentStyles[experimentKey(run)].color,
      borderColor: theme.experimentStyles[experimentKey(run)].color,
      pointRadius: 6, pointHoverRadius: 8,
    }));
    const points = datasets.flatMap((dataset) => dataset.data);
    const chartOptions = options(theme);
    chartOptions.plugins.tooltip.callbacks = {
      label(context) {
        return context.dataset.fullLabel + " · " + context.raw.suite + " · ASR " + context.raw.x + "% / TSR " + context.raw.y + "%";
      },
    };
    chartOptions.scales = {
      x: percentScale("ASR (%)", points.map((point) => point.x), theme),
      y: percentScale("TSR (%)", points.map((point) => point.y), theme),
    };
    return { type: "scatter", data: { datasets }, options: chartOptions };
  }

  const api = { metricInfo, metricConfigs, scatterConfig, canUseRadar, createExperimentStyles, describeExperiment, createBarFill };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DSCGHistoryCharts = api;
})(typeof window === "undefined" ? globalThis : window);
