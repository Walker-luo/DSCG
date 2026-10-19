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
const dualCatalog = [
  {id: "dojo-new", result_folder: "benchmarks", benchmark_id: "agentdojo", model_group: "agentdojo/qwen_baseline", attack_name: "tool_knowledge"},
  {id: "dyn-new", result_folder: "benchmarks", benchmark_id: "agentdyn", model_group: "agentdyn/qwen_baseline", attack_name: "important_instructions"},
  {id: "dyn-old", result_folder: "benchmarks", benchmark_id: "agentdyn", model_group: "qwen_agentdyn_baseline", attack_name: "tool_knowledge"},
  {id: "unrecorded", result_folder: "benchmarks", model_group: "agentdyn/legacy", attack_name: "unknown"},
  {id: "incomplete", result_folder: "benchmarks", benchmark_id: "mixed", model_group: "legacy_mixed", attack_name: "mixed"},
  {id: "dojo-partial", result_folder: "partial_benchmark", benchmark_id: "agentdojo", model_group: "qwen_partial", attack_name: "ignore_previous"},
];
test("backend filtering uses recorded identity, keeps old/new runs and never infers from paths", () => {
  assert.deepEqual(selection.filterRuns(dualCatalog, {folder: "benchmarks", backend: "agentdyn"}).map(r => r.id), ["dyn-new", "dyn-old"]);
  assert.deepEqual(selection.filterRuns(dualCatalog, {backend: "unknown"}).map(r => r.id), ["unrecorded"]);
  assert.deepEqual(selection.filterRuns(dualCatalog, {backend: "mixed"}).map(r => r.id), ["incomplete"]);
  assert.deepEqual(selection.filterRuns(dualCatalog, {folder: "benchmarks", backend: "agentdyn", models: ["agentdyn/qwen_baseline"], attack: "important_instructions"}).map(r => r.id), ["dyn-new"]);
});
test("backend options depend on folder and restrict downstream model and attack choices", () => {
  const state = selection.resolveFilters(dualCatalog, {folder: "benchmarks", backend: "agentdyn", models: ["agentdojo/qwen_baseline"], attack: "ignore_previous"});
  assert.deepEqual(state.backends, ["agentdojo", "agentdyn", "mixed", "unknown"]);
  assert.deepEqual(state.models, ["agentdyn/qwen_baseline", "qwen_agentdyn_baseline"]);
  assert.deepEqual(state.attacks, ["important_instructions", "tool_knowledge"]);
  assert.equal(state.filters.backend, "agentdyn");
  assert.equal(state.filters.models, null);
  assert.equal(state.filters.attack, "all");
  const partial = selection.resolveFilters(dualCatalog, {...state.filters, folder: "partial_benchmark"});
  assert.deepEqual(partial.backends, ["agentdojo"]);
  assert.equal(partial.filters.backend, "all");
  assert.deepEqual(partial.models, ["qwen_partial"]);
});
test("backend refresh preserves exclusions and explicit empty models, including an empty catalog", () => {
  const state = selection.resolveFilters(dualCatalog, {folder: "benchmarks", backend: "agentdyn", models: []});
  assert.deepEqual(state.filters.models, []);
  assert.deepEqual(selection.filterRuns(dualCatalog, state.filters), []);
  const visible = selection.filterRuns(dualCatalog, {...state.filters, models: null});
  assert.deepEqual(selection.visibleSelection(visible, ["dyn-old", "dojo-new"]), ["dyn-old"]);
  const empty = selection.resolveFilters([], state.filters);
  assert.deepEqual(empty.backends, []);
  assert.equal(empty.filters.backend, "all");
  assert.deepEqual(empty.filters.models, []);
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
