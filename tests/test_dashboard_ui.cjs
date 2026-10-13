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
    querySelectorAll: selector => selector.includes('.suite-cb') ? [{value: 'workspace'}] : []},
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
  assert.match(ui.node('#report-content').innerHTML, /显式任务文件展开<\/td><td>关闭/);
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
  ui.run("state.dashboardConfig = {framework_version: 'future-engine-version'}; updateRunPreview()");
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
  ui.run("state.dashboardConfig = {framework_version: 'future-engine-version'}; updateRunPreview()");
  await ui.run("loadOverview('historical-run')");
  assert.match(ui.node('#overview-content').innerHTML, /result-version">three-layer-v1/);
  assert.match(ui.node('#overview-content').innerHTML, /off[^<]*仍启用 L3/);
  assert.match(ui.node('#overview-content').innerHTML, /L2 1 \/ 2/);
  assert.match(ui.node('#overview-content').innerHTML, /成本未标为可比较/);
  assert.equal(ui.node('#workspace-framework').textContent, 'future-engine-version');
});
