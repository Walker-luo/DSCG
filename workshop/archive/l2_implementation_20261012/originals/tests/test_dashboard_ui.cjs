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
  for (const id of ['#use-input-isolation', '#use-sandbox', '#use-security-checker', '#authorization-precheck']) node(id).checked = true;
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
