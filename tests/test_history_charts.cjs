const test = require("node:test");
const assert = require("node:assert/strict");
const charts = require("../dashboard/static/js/history_charts.js");

const experiments = [
  { id: "a", label: "Version A", suites: [
    { suite_name: "workspace", metrics: { utility_rate: 100, attack_success_rate: 0, defense_success_rate: 100 }, overhead: { total_tokens: 2000 } },
    { suite_name: "travel", metrics: { utility_rate: 50, attack_success_rate: null, defense_success_rate: null }, overhead: { total_tokens: 1000 } },
  ] },
  { id: "b", label: "Version B", suites: [
    { suite_name: "workspace", metrics: { utility_rate: 75, attack_success_rate: 25, defense_success_rate: 75 }, overhead: { total_tokens: 5000 } },
  ] },
];

const selection = { metrics: ["utility_rate", "attack_success_rate"], view: "line", suite: "all" };

test("each selected metric gets its own chart with only that metric's data", () => {
  const panels = charts.metricConfigs(experiments, selection);
  assert.deepEqual(panels.map((panel) => panel.metric), ["utility_rate", "attack_success_rate"]);
  assert.equal(panels[0].title, "任务效用率 TSR");
  assert.deepEqual(panels[0].config.data.labels, ["workspace", "travel"]);
  assert.deepEqual(panels[0].config.data.datasets.map((row) => row.data), [[100, 50], [75, null]]);
  assert.deepEqual(panels[1].config.data.datasets.map((row) => row.data), [[0, null], [25, null]]);
  for (const panel of panels) {
    assert.deepEqual(panel.config.data.datasets.map((row) => row.metricKey), [panel.metric, panel.metric]);
  }
});

test("a single suite keeps experiment identity and colors in separate charts", () => {
  const panels = charts.metricConfigs(experiments, { ...selection, view: "bar", suite: "workspace" });
  assert.deepEqual(panels[0].config.data.labels, ["Version A", "Version B"]);
  assert.deepEqual(panels[0].config.data.datasets.map((row) => row.data), [[100, null], [null, 75]]);
  assert.deepEqual(panels[1].config.data.datasets.map((row) => row.data), [[0, null], [null, 25]]);
  assert.deepEqual(panels[0].config.data.datasets.map((row) => row.label), ["Version A", "Version B"]);
  for (const dataset of panels[0].config.data.datasets) assert.equal(dataset.grouped, false);
});

test("experiment colors and styles stay stable across metrics, order, and subset changes", () => {
  const styles = charts.createExperimentStyles(experiments, ["#123456", "#abcdef"]);
  const theme = { experimentStyles: styles };
  const panels = charts.metricConfigs(experiments, { ...selection, theme });
  assert.deepEqual(panels[0].config.data.datasets.map((row) => row.borderColor), ["#123456", "#abcdef"]);
  for (const panel of panels) {
    assert.deepEqual(panel.config.data.datasets.map((row) => row.borderColor), ["#123456", "#abcdef"]);
    assert.deepEqual(panel.config.data.datasets.map((row) => row.pointBackgroundColor), ["#123456", "#abcdef"]);
    assert.deepEqual(panel.config.data.datasets.map((row) => row.backgroundColor), ["#123456", "#abcdef"]);
    assert.notDeepEqual(panel.config.data.datasets[0].borderDash, panel.config.data.datasets[1].borderDash);
  }
  const reversed = charts.metricConfigs([experiments[1], experiments[0]], { ...selection, metrics: ["attack_success_rate", "utility_rate"], theme });
  assert.deepEqual(reversed[0].config.data.datasets.map((row) => row.borderColor), ["#abcdef", "#123456"]);
  const extended = charts.createExperimentStyles([{ id: "c", label: "Version A", suites: [] }, experiments[1]], ["#123456", "#abcdef"], styles);
  assert.deepEqual(extended.a, styles.a);
  assert.deepEqual(extended.b, styles.b);
  assert.notEqual(extended.c.color, styles.a.color);
  const subset = charts.metricConfigs([experiments[1]], { ...selection, theme });
  assert.equal(subset[0].config.data.datasets[0].borderColor, "#abcdef");
});

test("additional experiments receive distinct colors instead of recycling the five-color palette", () => {
  const runs = Array.from({ length: 9 }, (_, index) => ({ id: String(index), label: String(index) }));
  const styles = charts.createExperimentStyles(runs);
  assert.equal(new Set(Object.values(styles).map((style) => style.color)).size, 9);
});

test("percentage endpoints stay inside cartesian, radar and scatter plot bounds", () => {
  for (const view of ["line", "bar"]) {
    const config = charts.metricConfigs(experiments, { metrics: ["utility_rate"], view, suite: "all" })[0].config;
    assert.ok(config.options.scales.y.min < 0);
    assert.ok(config.options.scales.y.max > 100);
    assert.equal(config.options.scales.x.offset, true);
    const scale = { min: -5, max: 105, ticks: [{ value: -5 }, { value: 25 }, { value: 105 }] };
    config.options.scales.y.afterBuildTicks(scale);
    assert.deepEqual(scale.ticks.map((tick) => tick.value), [0, 25, 50, 75, 100]);
    assert.equal(scale.min, -5);
    assert.equal(scale.max, 105);
    assert.equal(config.options.scales.y.ticks.callback(0), "0%");
    assert.equal(config.options.scales.y.ticks.callback(100), "100%");
  }
  const radar = charts.metricConfigs(experiments, { ...selection, view: "radar" });
  assert.equal(radar.length, 2);
  for (const panel of radar) assert.ok(panel.config.options.scales.r.max > 100);
  const scatter = charts.scatterConfig(experiments);
  for (const axis of ["x", "y"]) {
    assert.ok(scatter.options.scales[axis].min < 0);
    assert.ok(scatter.options.scales[axis].max > 100);
  }
});

test("tokens get their own chart in K units with no shared percentage axis", () => {
  const panels = charts.metricConfigs(experiments, { ...selection, metrics: ["utility_rate", "total_tokens"], suite: "workspace" });
  assert.deepEqual(panels[1].config.data.datasets.map((row) => row.data), [[2, null], [null, 5]]);
  assert.equal(panels[1].config.options.scales.y.title.text, "Tokens (K)");
  assert.equal(panels[1].config.options.scales.y.max, undefined);
  assert.equal(panels[0].config.options.scales.y.title.text, "%");
  for (const panel of panels) assert.equal(panel.config.options.scales.yTokens, undefined);
});

test("unsupported radar combinations and empty selections are rejected", () => {
  assert.equal(charts.canUseRadar(selection.metrics, "all"), true);
  assert.equal(charts.canUseRadar(["utility_rate", "total_tokens"], "all"), false);
  assert.equal(charts.canUseRadar(["utility_rate"], "workspace"), false);
  assert.throws(() => charts.metricConfigs(experiments, { ...selection, metrics: [] }), /指标/);
  assert.throws(() => charts.metricConfigs(experiments, { ...selection, metrics: ["total_tokens"], view: "radar" }), /雷达/);
});

test("scatter skips missing metrics and uses the same experiment colors", () => {
  const styles = charts.createExperimentStyles(experiments, ["#123456", "#abcdef"]);
  const config = charts.scatterConfig(experiments, { experimentStyles: styles });
  assert.deepEqual(config.data.datasets[0].data, [{ x: 0, y: 100, suite: "workspace" }]);
  assert.deepEqual(config.data.datasets[1].data, [{ x: 25, y: 75, suite: "workspace" }]);
  assert.deepEqual(config.data.datasets.map((row) => row.backgroundColor), ["#123456", "#abcdef"]);
});

test("legend markers use each experiment's line color including radar fill transparency", () => {
  const config = charts.metricConfigs(experiments, { ...selection, view: "radar" })[0].config;
  const legend = config.options.plugins.legend.labels.generateLabels({ data: config.data, isDatasetVisible: (index) => index === 0 });
  assert.deepEqual(legend.map((row) => row.text), ["Version A", "Version B"]);
  assert.deepEqual(legend.map((row) => row.fillStyle), config.data.datasets.map((row) => row.borderColor));
  assert.deepEqual(legend.map((row) => row.hidden), [false, true]);
  assert.deepEqual(legend.map((row) => row.datasetIndex), [0, 1]);
});

test("single-suite axis labels wrap experiment names to fit independent panels", () => {
  const runs = experiments.map((run) => ({ ...run, label: "deepseek-flash_baseline_new" }));
  const config = charts.metricConfigs(runs, { ...selection, suite: "workspace" })[0].config;
  const format = config.options.scales.x.ticks.callback;
  assert.deepEqual(format.call({ getLabelForValue: () => runs[0].label }, 0), ["deepseek-flash", "baseline_new"]);
});
