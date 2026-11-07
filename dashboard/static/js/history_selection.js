((root) => {
  const unique = (values) => Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const backendId = run => run.benchmark_id || "unknown";
  // One selectable run: <model>/<name> keeps runs of the same model apart; flat layouts
  // reuse their recorded group name.
  const runKey = run => run.run_key || run.model_group;
  function filterRuns(catalog, { folder = "all", backend = "all", model = "all", models = null, attack = "all" } = {}) {
    return catalog.filter(run => (folder === "all" || run.result_folder === folder)
      && (backend === "all" || backendId(run) === backend)
      && (model === "all" || run.model === model)
      && (models === null || models.includes(runKey(run)))
      && (attack === "all" || run.attack_name === attack));
  }
  function resolveFilters(catalog, requested = {}) {
    const folders = unique(catalog.map(run => run.result_folder));
    const folder = folders.includes(requested.folder) ? requested.folder : "all";
    const backends = unique(filterRuns(catalog, { folder }).map(backendId));
    const backend = backends.includes(requested.backend) ? requested.backend : "all";
    const modelIds = unique(filterRuns(catalog, { folder, backend }).map(run => run.model));
    const model = modelIds.includes(requested.model) ? requested.model : "all";
    const models = unique(filterRuns(catalog, { folder, backend, model }).map(runKey));
    let selectedModels = Array.isArray(requested.models)
      ? unique(requested.models.filter(name => models.includes(name))) : null;
    if (requested.models?.length && !selectedModels.length) selectedModels = null;
    const attacks = unique(filterRuns(catalog, {
      folder, backend, model, models: selectedModels?.length === 0 ? null : selectedModels,
    }).map(run => run.attack_name));
    const attack = attacks.includes(requested.attack) ? requested.attack : "all";
    return { folders, backends, modelIds, models, attacks,
      filters: { folder, backend, model, models: selectedModels, attack } };
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
  const api = { filterRuns, resolveFilters, visibleSelection, attackLabel, backendLabel, runKey, createRequestGate };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.DSCGHistorySelection = api;
})(typeof window === "undefined" ? globalThis : window);
