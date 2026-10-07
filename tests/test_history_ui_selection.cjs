const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const selection = require("../dashboard/static/js/history_selection.js");
const historyCharts = require("../dashboard/static/js/history_charts.js");

test("actual filter events keep all selected versions after changing attacks and clear models across refresh", () => {
  const source = fs.readFileSync(path.join(__dirname, "../dashboard/static/js/history.js"), "utf8");
  class Element {
    constructor() { this.children = []; this.handlers = {}; this.style = {}; this.value = "all"; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    setAttribute() {}
  }
  const nodes = new Map();
  let ready;
  const find = (root, className) => root.children.flatMap(node => [
    ...(node.className?.split(" ").includes(className) ? [node] : []), ...find(node, className),
  ]);
  const document = {
    addEventListener(name, callback) { if (name === "DOMContentLoaded") ready = callback; },
    querySelector(selector) { if (!nodes.has(selector)) nodes.set(selector, new Element()); return nodes.get(selector); },
    querySelectorAll(selector) {
      const model = selector.startsWith(".history-model-cb");
      const elements = find(this.querySelector(model ? "#history-model-options" : "#history-run-list"), model ? "history-model-cb" : "history-run-cb");
      return selector.includes(":checked") ? elements.filter(item => item.checked) : elements;
    },
    createElement() { return new Element(); },
  };
  const catalog = ["attackA", "attackB"].flatMap(attack => ["baseline", "dscg"].map(model => ({
    id: model + "/" + attack, result_folder: "partial_benchmark", model_group: model,
    model_suffix: model, attack_name: attack, label: model, source: model + "/" + attack,
    suites: [{suite_name: "workspace"}],
  })));
  const gate = selection.createRequestGate();
  const context = {
    document, window: {setInterval() {}}, historySelection: selection, historyCharts, analysisRequests: gate,
    catalog, filters: {folder: "partial_benchmark", models: null, attack: "attackA"}, suites: ["workspace"],
    experimentStyles: historyCharts.createExperimentStyles(catalog), exporting: false,
    updateControls() {}, loadCatalog() {}, clearCharts() {}, renderSummaryTable() {}, showEmpty() {}, analyze() {}, exportAnalysis() {},
    addOption(select, value, text) { const node = new Element(); node.value = value; node.textContent = text; select.append(node); },
  };
  vm.createContext(context);
  // Run the production event wiring and selection/render helpers with a small DOM adapter.
  // Chart drawing and network activity are covered separately, so this test needs neither.
  const startup = source.slice(source.indexOf('  document.addEventListener("DOMContentLoaded"'), source.indexOf("  async function loadCatalog()"));
  const helpers = source.slice(source.indexOf("  function refreshFilterResults("), source.indexOf("  async function exportAnalysis()"));
  vm.runInContext(startup + helpers, context);
  ready();
  context.renderCatalog(new Set(), false);
  const click = selector => nodes.get(selector).handlers.click();
  const selected = () => Array.from(context.selectedRunIds()).sort();
  click("#history-model-select-all");
  assert.deepEqual(selected(), ["baseline/attackA", "dscg/attackA"]);
  const pending = gate.start();
  nodes.get("#history-attack-select").value = "attackB";
  nodes.get("#history-attack-select").handlers.change();
  assert.equal(gate.isCurrent(pending), false);
  assert.deepEqual(selected(), ["baseline/attackB", "dscg/attackB"]);
  click("#history-model-clear");
  assert.deepEqual(selected(), []);
  context.renderCatalog(new Set(), false);
  assert.deepEqual(selected(), []);
});
