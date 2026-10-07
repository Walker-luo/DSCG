const test = require("node:test");
const assert = require("node:assert/strict");
const selection = require("../dashboard/static/js/history_selection.js");
const catalog = [
  { id: "a", result_folder: "partial_benchmark", model_group: "model_baseline", model_suffix: "model_baseline", attack_name: "injecagent" },
  { id: "b", result_folder: "partial_benchmark", model_group: "model_baseline", model_suffix: "model_baseline", attack_name: "tool_knowledge" },
  { id: "c", result_folder: "partial_benchmark", model_group: "model_dscg", model_suffix: "model_dscg", attack_name: "injecagent" },
  { id: "d", result_folder: "benchmarks", model_group: "ablation/model_dscg", model_suffix: "model_dscg", attack_name: "unknown" },
];
test("folder, model and attack filters compose without merging model runs", () => {
  assert.deepEqual(selection.filterRuns(catalog, { folder: "partial_benchmark", models: null, attack: "injecagent" }).map(r => r.id), ["a", "c"]);
  assert.deepEqual(selection.filterRuns(catalog, { folder: "partial_benchmark", models: ["model_baseline"], attack: "tool_knowledge" }).map(r => r.id), ["b"]);
});
test("dependent options reset unavailable values when changing folders", () => {
  const state = selection.resolveFilters(catalog, { folder: "benchmarks", models: ["model_baseline"], attack: "injecagent" });
  assert.equal(state.filters.models, null);
  assert.equal(state.filters.attack, "all");
  assert.deepEqual(state.models, ["ablation/model_dscg"]);
  assert.deepEqual(state.attacks, ["unknown"]);
});
test("hidden selections are removed before analyze/export and select-all uses only visible runs", () => {
  const visible = selection.filterRuns(catalog, { folder: "partial_benchmark", models: null, attack: "injecagent" });
  assert.deepEqual(selection.visibleSelection(visible, ["a", "b", "d"]), ["a"]);
  assert.deepEqual(selection.visibleSelection(visible, ["a", "b", "d"], true), ["a", "c"]);
});
test("multiple framework versions retain separate runs under the same attack", () => {
  const filters = { folder: "partial_benchmark", models: ["model_baseline", "model_dscg"], attack: "injecagent" };
  const state = selection.resolveFilters(catalog, filters);
  assert.deepEqual(state.filters.models, filters.models);
  assert.deepEqual(selection.filterRuns(catalog, state.filters).map(r => r.id), ["a", "c"]);
  assert.deepEqual(selection.visibleSelection(selection.filterRuns(catalog, state.filters), [], true), ["a", "c"]);
  assert.deepEqual(selection.filterRuns(catalog, {...filters, models: []}), []);
});
test("catalog refresh preserves an explicit empty model selection and removes unavailable versions", () => {
  assert.deepEqual(selection.resolveFilters(catalog, {models: []}).filters.models, []);
  assert.deepEqual(selection.resolveFilters(catalog, {folder: "partial_benchmark", models: ["model_baseline", "deleted"]}).filters.models, ["model_baseline"]);
});
test("pending analyses cannot restore results hidden by a new filter and the newest request wins", async () => {
  const gate = selection.createRequestGate();
  let rendered = [];
  let resolveOld;
  const oldResult = new Promise(resolve => { resolveOld = resolve; });
  const oldRequest = gate.start();
  const pending = oldResult.then(rows => { if (gate.isCurrent(oldRequest)) rendered = rows; });
  gate.invalidate(); // User switches from all attacks to tool_knowledge.
  const newRequest = gate.start();
  if (gate.isCurrent(newRequest)) rendered = ["b"];
  resolveOld(["a", "c"]);
  await pending;
  assert.deepEqual(rendered, ["b"]);
  gate.invalidate(); // Clear selection while another request is pending.
  assert.equal(gate.isCurrent(newRequest), false);
});
