const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function dashboard(fetch = async () => ({ok: true, json: async () => []})) {
  const nodes = new Map();
  const node = selector => {
    if (!nodes.has(selector)) nodes.set(selector, {value: '', checked: false, disabled: false,
      selectedOptions: [{dataset: {}, textContent: ''}], style: {}, dataset: {}, hidden: true,
      classList: {add() {}, remove() {}, toggle() {}}, querySelector: () => ({textContent: ''}),
      setAttribute() {}, addEventListener() {}});
    return nodes.get(selector);
  };
  for (const id of ['#use-input-isolation', '#use-sandbox', '#use-security-checker', '#authorization-precheck', '#planning-tool-view', '#delegated-tasks']) node(id).checked = true;
  node('#pipeline-type').value = 'newframe';
  node('#run-attack').value = 'true';
  node('#trace-level').value = 'summary';
  node('#selection-seed').value = '20260927';
  node('#attack-name').value = 'important_instructions';
  const context = {document: {addEventListener() {}, querySelector: node,
    querySelectorAll: selector => selector.includes('.suite-cb') ? [{value: 'shopping'}] : []},
    fetch, console, alert() {}, bootstrap: {Tab: class {show() {}}},
    EventSource: class {}, setInterval() {}, setTimeout() {}};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('dashboard/static/js/app.js', 'utf8'), context);
  return {context, node, run: code => vm.runInContext(code, context)};
}

test('submitted config carries an independently disabled L1 and selected trace level', () => {
  const ui = dashboard();
  ui.node('#use-input-isolation').checked = false;
  ui.node('#trace-level').value = 'standard';
  const config = ui.run('getSelectedConfig()');
  assert.equal(config.input_isolation, false);
  assert.equal(config.authorization_precheck, true);
  assert.equal(config.trace_level, 'standard');
});

test('removing L2 disables its precheck while retaining L1 and L3', () => {
  const ui = dashboard();
  ui.run("applyDefensePreset('no-l2')");
  const config = ui.run('getSelectedConfig()');
  assert.equal(config.use_sandbox, false);
  assert.equal(config.authorization_precheck, false);
  assert.equal(config.input_isolation, true);
  assert.equal(config.use_security_checker, true);
});

test('V2 control removes L1 and candidate precheck but keeps authorization and auditing', () => {
  const ui = dashboard();
  ui.run("applyDefensePreset('v2')");
  const config = ui.run('getSelectedConfig()');
  assert.equal(config.input_isolation, false);
  assert.equal(config.authorization_precheck, false);
  assert.equal(config.use_sandbox, true);
  assert.equal(config.use_security_checker, true);
  assert.equal(config.planning_tool_view, false);
  assert.equal(config.delegated_tasks, false);
});

test('full preset uses authorized views and explicit delegation, while no L2 disables both', () => {
  const ui = dashboard();
  ui.run("applyDefensePreset('full')");
  assert.equal(ui.run('getSelectedConfig()').planning_tool_view, true);
  assert.equal(ui.run('getSelectedConfig()').delegated_tasks, true);
  ui.run("applyDefensePreset('no-l2')");
  assert.equal(ui.run('getSelectedConfig()').planning_tool_view, false);
  assert.equal(ui.run('getSelectedConfig()').delegated_tasks, false);
});

test('report shows saved effective L2 controls independently from the current draft', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({suites: ['workspace'],
    config: {origin: false, use_sandbox: true, use_security_checker: true,
    planning_tool_view: false, delegated_tasks: false}, suites: []})}));
  ui.node('#report-data-source').value = 'fixture';
  await ui.run('loadReport()');
  assert.equal(ui.run('getSelectedConfig()').planning_tool_view, true);
  assert.match(ui.node('#report-content').innerHTML, /L2 授权工具视图<\/td><td>关闭/);
  assert.match(ui.node('#report-content').innerHTML, /显式任务来源展开<\/td><td>关闭/);
});

test('failed submission shows the server error and restores run state', async () => {
  const ui = dashboard(async () => ({ok: false, json: async () => ({error: '无效配置'})}));
  await ui.run('startRun()');
  assert.equal(ui.run('state.isRunning'), false);
  assert.equal(ui.run('state.currentRunId'), null);
  assert.equal(ui.node('#config-error').textContent, '无效配置');
  assert.equal(ui.node('#config-error').hidden, false);
});

test('reports distinguish an unused auditor from unknown historical configuration', async () => {
  for (const [config, expected] of [
    [{origin: true, model_id: 'main'}, '未使用'],
    [{origin: false, use_security_checker: false, model_id: 'main'}, '未使用'],
    [{origin: false, model_id: 'main'}, '未记录'],
    [{origin: false, use_security_checker: true, model_id: 'main'}, 'Local/Env 配置'],
  ]) {
    const ui = dashboard(async () => ({ok: true, json: async () => ({config, suites: []})}));
    ui.node('#report-data-source').value = 'fixture';
    await ui.run('loadReport()');
    assert.match(ui.node('#report-content').innerHTML,
      new RegExp(`审计模型</td><td>${expected}</td>`));
  }
});

test('draft version follows server metadata and switches to the native loop for baseline', () => {
  const ui = dashboard();
  ui.run("state.dashboardConfig = {framework_version: 'future-engine-version', benchmark_label: 'AgentDojo'}; updateRunPreview()");
  assert.equal(ui.node('#workspace-framework').textContent, 'future-engine-version');
  assert.equal(ui.node('#config-defense .framework-version').textContent, 'future-engine-version');
  ui.node('#pipeline-type').value = 'origin';
  ui.run('updateRunPreview()');
  assert.equal(ui.node('#workspace-framework').textContent, 'AgentDojo 原生循环');
});

test('draft flow follows the effective tool view and delegation switches', () => {
  const ui = dashboard();
  ui.run("applyDefensePreset('full')");
  assert.equal(ui.node('#delegation-flow').hidden, false);
  assert.match(ui.node('#framework-flow').textContent, /已授权工具视图/);
  ui.run("applyDefensePreset('v2')");
  assert.equal(ui.node('#delegation-flow').hidden, true);
  assert.doesNotMatch(ui.node('#framework-flow').textContent, /已授权工具视图/);
  assert.match(ui.node('#layer-config-note').textContent, /不是历史 V2/);
});

test('saved run keeps its own version and distinguishes router off from disabled L3', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({config: {
    framework_version: 'three-layer-v1', use_security_checker: true, audit_router_mode: 'off'},
    suites: [{suite_name: 'workspace', layer_stats: {l2_records: 1}, cost_comparison_ready: false}],
    display_metrics: {total_tasks: 2}})}));
  ui.run("state.dashboardConfig = {framework_version: 'future-engine-version', benchmark_label: 'AgentDojo'}; updateRunPreview()");
  await ui.run("loadOverview('historical-run')");
  assert.match(ui.node('#overview-content').innerHTML, /result-version">three-layer-v1/);
  assert.match(ui.node('#overview-content').innerHTML, /off[^<]*仍启用 L3/);
  assert.match(ui.node('#overview-content').innerHTML, /L2 1 \/ 2/);
  assert.match(ui.node('#overview-content').innerHTML, /成本未标为可比较/);
  assert.equal(ui.node('#workspace-framework').textContent, 'future-engine-version');
});

test('task preview has no invented catalog counts before the backend loads', () => {
  const ui = dashboard();
  ui.run('updateRunPreview()');
  assert.equal(ui.node('#preview-tasks').textContent, '未加载');
  ui.run("state.dashboardConfig = {suites: [{id: 'shopping', user_tasks: 7, injection_tasks: 2}]}; updateRunPreview()");
  assert.equal(ui.node('#preview-suites').textContent, '1 / 1');
  assert.equal(ui.node('#preview-tasks').textContent, '14');
});

test('comparison rejection is shown instead of attempting to draw pooled results', async () => {
  const ui = dashboard(async () => ({ok: false, json: async () => ({error: '基准任务目录未对齐'})}));
  ui.context.document.querySelectorAll = () => [{value: 'a'}, {value: 'b'}];
  ui.run('renderComparison = () => { throw new Error("should not render rejected comparison"); }');
  await ui.run('runComparison()');
  assert.match(ui.node('#compare-results').innerHTML, /基准任务目录未对齐/);
});

test('saved report displays recorded benchmark provenance without inventing legacy identity', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({config: {benchmark: {
    id: 'agentdyn', revision: 'fixed-revision', catalog_sha256: 'recorded-catalog'}}, suites: []})}));
  ui.node('#report-data-source').value = 'fixture';
  await ui.run('loadReport()');
  assert.match(ui.node('#report-content').innerHTML, /fixed-revision/);
  assert.match(ui.node('#report-content').innerHTML, /recorded-catalog/);
});

test('backend absence remains actionable and disables new execution in the page', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({
    suites: [], backend_ready: false, backend_error: 'Use the pinned ipi-agentdyn environment', suite_version: 'v1.2',
  })}));
  ui.context.document.querySelectorAll = () => [];
  await ui.run('loadDashboardConfig()');
  assert.equal(ui.node('#btn-run').disabled, true);
  assert.match(ui.node('#backend-status').textContent, /ipi-agentdyn/);
  assert.equal(ui.node('#suite-grid').innerHTML, '');
  assert.equal(ui.node('#preview-tasks').textContent, '未加载');
});

test('overview distinguishes valid utility denominator from total and runtime errors', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({
    config: {origin: true, run_attack: true}, suites: [],
    display_metrics: {avg_utility_rate: 100, utility_passed: 1, utility_valid: 1, total_tasks: 2, execution_errors: 1}
  })}));
  await ui.run('loadOverview("errors")');
  const html = ui.node('#overview-content').innerHTML;
  assert.match(html, /1 \/ 1 个有效任务成功/);
  assert.match(html, /总任务 2/);
  assert.match(html, /运行错误 1/);
});

test('native draft labels follow the active environment without a benchmark selector', () => {
  const ui = dashboard();
  ui.node('#pipeline-type').value = 'origin';
  for (const label of ['AgentDojo', 'AgentDyn']) {
    ui.run(`state.dashboardConfig = {benchmark_label: '${label}'}; updateRunPreview()`);
    assert.equal(ui.node('#workspace-framework').textContent, `${label} 原生循环`);
    assert.equal(ui.node('#config-defense .framework-version').textContent, label);
    assert.match(ui.node('#framework-flow').textContent, new RegExp(label));
  }
});

test('unknown backend page never defaults to a different benchmark label or risk catalog', async () => {
  const ui = dashboard(async () => ({ok: true, json: async () => ({suites: [],
    backend_ready: false, benchmark_id: 'unknown', benchmark_label: '未识别基准',
    backend_error: 'Unrecognized backend', tool_metadata_path: null})}));
  ui.context.document.querySelectorAll = () => [];
  await ui.run('loadDashboardConfig()');
  assert.match(ui.node('#benchmark-badge').textContent, /未识别基准/);
  assert.doesNotMatch(ui.node('#benchmark-badge').textContent, /AgentDyn|AgentDojo/);
  assert.equal(ui.node('#tool-metadata-path').placeholder, '后端未就绪');
  assert.equal(ui.node('#btn-run').disabled, true);
});
