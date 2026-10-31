((root) => {
  const unique = (values) => Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const backendId = run => run.benchmark_id || "unknown";
  function filterRuns(catalog, { folder = "all", backend = "all", models = null, attack = "all" } = {}) {
    return catalog.filter(run => (folder === "all" || run.result_folder === folder)
      && (backend === "all" || backendId(run) === backend)
      && (models === null || models.includes(run.model_group))
      && (attack === "all" || run.attack_name === attack));
  }
  function resolveFilters(catalog, requested = {}) {
    const folders = unique(catalog.map(run => run.result_folder));
    const folder = folders.includes(requested.folder) ? requested.folder : "all";
    const backends = unique(filterRuns(catalog, { folder }).map(backendId));
    const backend = backends.includes(requested.backend) ? requested.backend : "all";
    const models = unique(filterRuns(catalog, { folder, backend }).map(run => run.model_group));
    let selectedModels = Array.isArray(requested.models)
      ? unique(requested.models.filter(model => models.includes(model))) : null;
    if (requested.models?.length && !selectedModels.length) selectedModels = null;
    const attacks = unique(filterRuns(catalog, {
      folder, backend, models: selectedModels?.length === 0 ? null : selectedModels,
    }).map(run => run.attack_name));
    const attack = attacks.includes(requested.attack) ? requested.attack : "all";
    return { folders, backends, models, attacks, filters: { folder, backend, models: selectedModels, attack } };
  }
  function visibleSelection(visible, selected, all = false) {
    const ids = new Set(selected);
    return visible.filter(run => all || ids.has(run.id)).map(run => run.id);
  }
  function attackLabel(name) {
    return ({ unknown: "未记录攻击", mixed: "混合攻击（历史汇总）", none: "无攻击" })[name] || name;
  }
  function backendLabel(name) {
    return ({agentdojo: "AgentDojo", agentdyn: "AgentDyn", unknown: "未记录基准", mixed: "混合／身份不完整"})[name] || name;
  }
  function createRequestGate() {
    let revision = 0;
    return {
      start: () => ++revision,
      invalidate: () => { revision += 1; },
      isCurrent: request => request === revision,
    };
  }
  const api = { filterRuns, resolveFilters, visibleSelection, attackLabel, backendLabel, createRequestGate };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DSCGHistorySelection = api;
})(typeof window === "undefined" ? globalThis : window);
