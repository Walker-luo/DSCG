/**
 * DSCG Dashboard - 前端应用逻辑
 * 实时日志 / 图表渲染 / 对比分析 / 报告生成
 */

// =============================================
// 全局状态
// =============================================
const state = {
  currentRunId: null,
  autoScroll: true,
  allRuns: [],
  charts: {},          // 保存 Chart.js 实例引用
  comparisonCharts: {},
  eventSource: null,
  isRunning: false,
  dashboardConfig: null,
  overviewLoaded: false,
  overviewRequest: 0,
};

// DOM 引用缓存
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// =============================================
// 初始化
// =============================================
document.addEventListener("DOMContentLoaded", () => {
  initConfigListeners();
  loadDashboardConfig();
  loadAllRuns();
  refreshDataSources();
  updateRunPreview();

  // 定时刷新运行列表
  setInterval(loadAllRuns, 10000);
  setInterval(refreshDataSources, 10000);
});

// =============================================
// 配置面板交互逻辑
// =============================================
function initConfigListeners() {
  // 框架类型切换
  $("#pipeline-type").addEventListener("change", (e) => {
    updateRunPreview();
  });

  // 攻击模式切换
  $("#run-attack").addEventListener("change", (e) => {
    const isAttack = e.target.value === "true";
    $("#attack-type-group").style.display = isAttack ? "block" : "none";
    $("#injection-limit-group").style.display = isAttack ? "block" : "none";
    updateRunPreview();
  });

  // 启动测试
  $("#btn-run").addEventListener("click", startRun);
  $("#btn-stop").addEventListener("click", stopRun);

  // 日志过滤
  $("#filter-errors").addEventListener("change", toggleLogFilter);
  $("#defense-preset").addEventListener("change", e => applyDefensePreset(e.target.value));
  $("#workspace-run").addEventListener("change", e => {
    ["chart-data-source", "detail-data-source", "report-data-source"].forEach(id => $("#" + id).value = e.target.value);
    if (e.target.value) loadOverview(e.target.value);
  });
  ["use-input-isolation", "use-sandbox", "use-security-checker", "authorization-precheck"].forEach(id => {
    $("#" + id).addEventListener("change", () => {
      $("#defense-preset").value = "custom";
      updateRunPreview();
    });
  });

  [
    "#model-id", "#sec-model-id", "#defense", "#use-sandbox",
    "#use-security-checker", "#max-user-tasks", "#max-injection-tasks",
    "#api-key", "#base-url", "#sec-api-key", "#sec-base-url",
    "#tool-metadata-path",
    "#trace-level", "#selection-seed",
  ].forEach((selector) => {
    const element = $(selector);
    if (!element) return;
    element.addEventListener("change", updateRunPreview);
    element.addEventListener("input", updateRunPreview);
  });
  $$(".suite-cb").forEach((checkbox) => checkbox.addEventListener("change", updateRunPreview));
}

function getSelectedConfig() {
  const suites = [];
  $$(".suite-cb:checked").forEach(cb => suites.push(cb.value));

  const pipelineType = $("#pipeline-type").value;
  const isOrigin = pipelineType === "origin";
  const withChecker = !isOrigin && $("#use-security-checker").checked;
  const mainOption = $("#model-id").selectedOptions[0];
  const secOption = $("#sec-model-id").selectedOptions[0];
  const customApiKey = $("#api-key").value.trim();
  const customBaseUrl = $("#base-url").value.trim();
  const customSecApiKey = $("#sec-api-key").value.trim();
  const customSecBaseUrl = $("#sec-base-url").value.trim();

  return {
    label: $("#run-label").value || null,
    model_id: $("#model-id").value || null,
    provider: mainOption?.dataset.provider || null,
    api_key: customApiKey || null,
    base_url: customBaseUrl || null,
    sec_model_id: withChecker ? ($("#sec-model-id").value || null) : null,
    sec_provider: withChecker ? (secOption?.dataset.provider || null) : null,
    sec_api_key: withChecker ? (customSecApiKey || null) : null,
    sec_base_url: withChecker ? (customSecBaseUrl || null) : null,
    suites: suites,
    run_attack: $("#run-attack").value === "true",
    origin: isOrigin,
    defense: isOrigin && $("#defense").value ? $("#defense").value : null,
    attack_name: $("#attack-name").value,
    use_sandbox: !isOrigin && $("#use-sandbox").checked,
    use_security_checker: !isOrigin && $("#use-security-checker").checked,
    input_isolation: !isOrigin && ($("#use-sandbox").checked || $("#use-security-checker").checked) && $("#use-input-isolation").checked,
    authorization_precheck: !isOrigin && $("#use-sandbox").checked && $("#authorization-precheck").checked,
    trace_level: $("#trace-level").value,
    selection_seed: Number($("#selection-seed").value),
    max_user_tasks: Number($("#max-user-tasks").value),
    max_injection_tasks: Number($("#max-injection-tasks").value),
    tool_metadata_path: $("#tool-metadata-path").value.trim() || null,
  };
}

function applyDefensePreset(preset) {
  if (preset === "custom") return;
  $("#use-input-isolation").checked = !["no-l1", "v2"].includes(preset);
  $("#use-sandbox").checked = preset !== "no-l2";
  $("#use-security-checker").checked = preset !== "no-l3";
  $("#authorization-precheck").checked = !["no-l2", "v2"].includes(preset);
  updateRunPreview();
}

function showConfigError(message) {
  $("#config-error").textContent = message || "";
  $("#config-error").hidden = !message;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
}

const formatRate = value => typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}%` : "—";
const formatCount = value => typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("zh-CN") : "未记录";

function toggleSecretVisibility(inputId, button) {
  const input = $("#" + inputId);
  if (!input) return;
  const shouldShow = input.type === "password";
  input.type = shouldShow ? "text" : "password";
  button.innerHTML = `<i class="bi bi-eye${shouldShow ? '-slash' : ''}"></i>`;
  button.setAttribute(
    "aria-label",
    `${shouldShow ? "隐藏" : "显示"} ${inputId === "api-key" ? "主模型" : "安全模型"} API Key`,
  );
}

async function loadDashboardConfig() {
  try {
    const resp = await fetch("/api/config");
    const config = await resp.json();
    state.dashboardConfig = config;
    populateModelSelect("model-id", config.models || []);
    populateModelSelect("sec-model-id", config.sec_models || []);
    populateModelSelect("attack-name", config.attacks || []);
    (config.suites || []).forEach((suite) => {
      const count = document.querySelector(`[data-suite-count="${suite.id}"]`);
      if (count) count.textContent = `${suite.user_tasks} × ${suite.injection_tasks}`;
    });
    updateRunPreview();
  } catch (err) {
    console.error("加载模型配置失败:", err);
  }
}

function updateRunPreview() {
  const selectedSuites = Array.from($$(".suite-cb:checked")).map((item) => item.value);
  const allSuites = state.dashboardConfig?.suites || [
    { id: "workspace", user_tasks: 40, injection_tasks: 14 },
    { id: "travel", user_tasks: 20, injection_tasks: 7 },
    { id: "banking", user_tasks: 16, injection_tasks: 9 },
    { id: "slack", user_tasks: 21, injection_tasks: 5 },
  ];
  const maxUsers = Math.max(0, Number.parseInt($("#max-user-tasks")?.value, 10) || 0);
  const maxInjections = Math.max(0, Number.parseInt($("#max-injection-tasks")?.value, 10) || 0);
  const withAttack = $("#run-attack")?.value === "true";

  const estimatedTasks = allSuites
    .filter((suite) => selectedSuites.includes(suite.id))
    .reduce((sum, suite) => {
      const users = maxUsers > 0 ? Math.min(maxUsers, suite.user_tasks) : suite.user_tasks;
      const injections = maxInjections > 0
        ? Math.min(maxInjections, suite.injection_tasks)
        : suite.injection_tasks;
      return sum + (withAttack ? users * injections : users);
    }, 0);

  const isOrigin = $("#pipeline-type")?.value === "origin";
  const sandbox = !isOrigin && $("#use-sandbox").checked;
  const checker = !isOrigin && $("#use-security-checker").checked;
  const isolation = !isOrigin && (sandbox || checker) && $("#use-input-isolation").checked;
  const precheck = sandbox && $("#authorization-precheck").checked;
  $("#use-input-isolation").disabled = isOrigin || !(sandbox || checker);
  $("#authorization-precheck").disabled = !sandbox;
  $("#sec-model-group").style.display = checker ? "block" : "none";
  $("#sec-connection-group").style.display = checker ? "block" : "none";
  $("#defense-group").style.display = isOrigin ? "block" : "none";
  $("#ablation-group").style.display = isOrigin ? "none" : "grid";
  $("#trace-level-group").style.display = isOrigin ? "none" : "block";
  $("#config-defense .framework-version").textContent = isOrigin ? "AgentDojo" : "three-layer-v1";
  $(".metadata-path-group").style.display = isOrigin ? "none" : "block";
  let defenseLabel = "Baseline";
  if (isOrigin) {
    defenseLabel = $("#defense")?.selectedOptions[0]?.textContent || "Baseline";
  } else {
    defenseLabel = [isolation && "L1", sandbox && "L2", checker && "L3"].filter(Boolean).join(" + ") || "关闭防御";
  }
  $("#layer-config-note").textContent = !(sandbox || checker)
    ? "L2/L3 全关时 L1 随之关闭；该 DSCG 消融仍使用 Monitor，与原生 Baseline 的工具循环不同。"
    : sandbox && !precheck ? "已关闭候选前置检查；工具授权仍由 Monitor 检查。重审 0 次，完成提示关闭。"
    : "Monitor 与一次性票据负责执行。重审 0 次，完成提示关闭；学习免审尚未实施。";
  [["l1", isolation], ["l2", sandbox], ["l3", checker]].forEach(([id, enabled]) => {
    const layer = $("#preview-layer-" + id);
    layer.classList.toggle("is-disabled", !enabled);
    layer.querySelector("b").textContent = enabled ? "启用" : "关闭";
  });
  $("#workspace-framework").textContent = isOrigin ? "AgentDojo 原生循环" : "three-layer-v1";
  $("#workspace-mode").textContent = withAttack ? "对抗评测" : "良性效用评测";
  $("#framework-flow").textContent = isOrigin
    ? "原生 AgentDojo 规划与工具执行；DSCG 三层不参与运行。"
    : `${sandbox ? "任务授权 → " : ""}主模型规划${isolation ? "（返回经 L1）" : ""} → ${precheck ? "L2 前置检查 → " : ""}${checker ? "L3 路由 → " : ""}Monitor 执行`;

  if ($("#preview-suites")) $("#preview-suites").textContent = `${selectedSuites.length} / ${allSuites.length}`;
  if ($("#preview-tasks")) $("#preview-tasks").textContent = estimatedTasks.toLocaleString("zh-CN");
  if ($("#preview-defense")) $("#preview-defense").textContent = defenseLabel;
}

function populateModelSelect(selectorId, models) {
  const select = $("#" + selectorId);
  if (!select || models.length === 0) return;

  const currentValue = select.value;
  select.innerHTML = "";
  models.forEach((model) => {
    const option = document.createElement("option");
    option.value = model.id || "";
    option.textContent = model.label || model.id || "Local/Env 配置";
    if (model.provider) option.dataset.provider = model.provider;
    if (model.base_url) option.dataset.baseUrl = model.base_url;
    select.appendChild(option);
  });

  const values = Array.from(select.options).map((option) => option.value);
  if (values.includes(currentValue)) {
    select.value = currentValue;
  }
}

// =============================================
// 运行管理
// =============================================
async function startRun() {
  const config = getSelectedConfig();
  showConfigError("");

  if (config.suites.length === 0) {
    showConfigError("请至少选择一个测试场景。");
    return;
  }
  if ([config.max_user_tasks, config.max_injection_tasks, config.selection_seed].some(value => !Number.isSafeInteger(value) || value < 0)) {
    showConfigError("任务上限和 seed 必须为非负整数。");
    return;
  }

  if (state.isRunning) {
    alert("已有测试正在运行中，请等待完成后再启动新测试。");
    return;
  }

  // UI 状态切换
  state.isRunning = true;
  $("#btn-run").disabled = true;
  $("#btn-run").innerHTML = '<i class="bi bi-hourglass-split"></i> 启动中...';
  updateStatus("running", "运行中");
  $("#btn-stop").style.display = "inline-flex";
  if ($("#live-context")) $("#live-context").textContent = "正在建立连接";

  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await resp.json();
    if (!resp.ok || !data.run_id) throw new Error(data.error || "服务端未返回运行 ID");
    state.currentRunId = data.run_id;

    // 更新 UI
    $("#current-run-badge").style.display = "block";
    $("#current-run-id").textContent = data.run_id.slice(0, 16) + "...";
    $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 测试运行中...';
    updateStatus("running", "运行中: " + data.run_id.slice(0, 12));
    if ($("#live-context")) $("#live-context").textContent = `${config.suites.length} 个场景 · ${data.run_id.slice(0, 12)}`;

    // 切换到日志面板
    const logTab = new bootstrap.Tab($("#tab-live"));
    logTab.show();

    // 清空日志并启动 SSE
    clearLogs();
    $("#run-progress").hidden = false;
    updateProgress({phase: "setup", completed_suites: 0, total_suites: config.suites.length});
    connectSSE(data.run_id);

  } catch (err) {
    console.error("启动测试失败:", err);
    showConfigError(err.message);
    state.isRunning = false;
    $("#btn-run").disabled = false;
    $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始评测';
    $("#btn-stop").style.display = "none";
    updateStatus("idle", "就绪");
  }
}

function stopRun() {
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }
  state.isRunning = false;
  $("#btn-run").disabled = false;
  $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始评测';
  $("#btn-stop").style.display = "none";
  updateStatus("idle", "日志已断开");
  if ($("#live-context")) $("#live-context").textContent = "实时连接已断开";
  pushLogEntry("warning", "实时日志连接已断开；后台评测任务可能仍在运行。此操作不会终止服务端线程。");
}

// =============================================
// SSE 实时日志
// =============================================
function connectSSE(runId) {
  if (state.eventSource) {
    state.eventSource.close();
  }

  const es = new EventSource(`/api/stream/${escapeHtml(runId)}`);
  state.eventSource = es;

  es.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleSSEMessage(msg);
    } catch (e) {
      // 忽略解析错误
    }
  };

  es.onerror = () => {
    // SSE 连接中断——可能是测试完成或网络问题
    if (es.readyState === EventSource.CLOSED) {
      // 正常关闭，不做额外处理
    }
  };
}

function handleSSEMessage(msg) {
  switch (msg.type) {
    case "log":
      pushLogEntry(msg.level || "info", msg.message);
      break;

    case "progress":
      updateProgress(msg);
      break;

    case "done":
      onRunComplete(msg);
      break;

    case "heartbeat":
      // 保持连接活跃
      break;
  }
}

function pushLogEntry(level, message) {
  const viewer = $("#log-viewer");

  // 移除占位符
  const placeholder = viewer.querySelector(".log-placeholder");
  if (placeholder) placeholder.remove();

  const entry = document.createElement("div");
  entry.className = `log-entry ${level}`;

  const ts = document.createElement("span");
  ts.className = "log-timestamp";
  ts.textContent = new Date().toLocaleTimeString("zh-CN");
  entry.appendChild(ts);

  const text = document.createTextNode(message);
  entry.appendChild(text);

  // 过滤逻辑
  if ($("#filter-errors").checked && level !== "error") {
    entry.style.display = "none";
    entry.dataset.hidden = "true";
  }

  viewer.appendChild(entry);

  // 自动滚动
  if (state.autoScroll) {
    viewer.scrollTop = viewer.scrollHeight;
  }
}

function clearLogs() {
  const viewer = $("#log-viewer");
  viewer.innerHTML = "";
}

function scrollLogsToBottom() {
  const viewer = $("#log-viewer");
  viewer.scrollTop = viewer.scrollHeight;
}

function toggleAutoScroll() {
  state.autoScroll = !state.autoScroll;
  const btn = $("#btn-auto-scroll");
  if (state.autoScroll) {
    btn.innerHTML = '<i class="bi bi-check-circle"></i> 自动滚动';
    btn.classList.remove("btn-outline-secondary");
    btn.classList.add("btn-outline-success");
  } else {
    btn.innerHTML = '<i class="bi bi-circle"></i> 自动滚动 (关)';
    btn.classList.remove("btn-outline-success");
    btn.classList.add("btn-outline-secondary");
  }
}

function toggleLogFilter() {
  const filterErrors = $("#filter-errors").checked;
  $$(".log-entry").forEach(entry => {
    if (filterErrors) {
      if (!entry.classList.contains("error")) {
        entry.style.display = "none";
        entry.dataset.hidden = "true";
      }
    } else {
      if (entry.dataset.hidden === "true") {
        entry.style.display = "";
        entry.dataset.hidden = "false";
      }
    }
  });
}

function updateProgress(progress) {
  const phase = {setup: "准备场景", benchmark: "执行评测", analysis: "场景完成"}[progress.phase] || "运行中";
  $("#progress-phase").textContent = `${progress.current_suite || ""} ${phase}`;
  if (Number.isInteger(progress.completed_suites)) {
    $("#suite-progress").max = progress.total_suites || 1;
    $("#suite-progress").value = progress.completed_suites;
    $("#progress-count").textContent = `${progress.completed_suites} / ${progress.total_suites} 个场景完成`;
  }
  // 可以在日志中显示进度
  if (progress.current_suite && progress.phase) {
    const phaseLabels = {
      "setup": "🔧 构建 Pipeline",
      "benchmark": "🏃 执行基准测试",
      "analysis": "📊 分析结果",
    };
    const label = phaseLabels[progress.phase] || progress.phase;
    pushLogEntry("metric", `[${progress.current_suite}] ${label}`);
  }
}

function updateStatus(status, text) {
  const indicator = $("#status-indicator");
  indicator.className = `run-status ${status}`;
  indicator.innerHTML = `<span class="status-dot"></span><span>${escapeHtml(text)}</span>`;
}

// =============================================
// 测试完成处理
// =============================================
function onRunComplete(msg) {
  state.isRunning = false;
  $("#btn-run").disabled = false;
  $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始评测';
  $("#btn-stop").style.display = "none";
  updateStatus(msg.summary?.error ? "failed" : "completed", msg.summary?.error ? "运行失败" : "已完成");
  if ($("#live-context")) $("#live-context").textContent = msg.summary?.error ? "运行失败，查看错误日志" : "运行已完成";
  $("#progress-phase").textContent = msg.summary?.error ? "运行失败" : "评测完成";

  if (msg.summary && msg.summary.error) {
    pushLogEntry("error", `测试异常结束: ${msg.summary.error}`);
  } else {
    pushLogEntry("success", "✅ 所有测试套件执行完毕！");
    if (msg.summary) {
      pushLogEntry("metric",
        `📊 聚合结果: TSR=${msg.summary.avg_utility_rate}%, ` +
        `ASR=${msg.summary.avg_attack_success_rate}%, ` +
        `Defense=${msg.summary.avg_defense_success_rate}%`
      );
    }
  }

  // 关闭 SSE
  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }

  // 刷新数据
  loadAllRuns();
  refreshDataSources();

  // 自动切换到概览面板
  if (!msg.summary?.error) setTimeout(() => {
    const overviewTab = new bootstrap.Tab($("#tab-overview"));
    overviewTab.show();
    loadOverview(state.currentRunId);
  }, 1500);
}

// =============================================
// 数据加载
// =============================================
async function loadAllRuns() {
  try {
    const resp = await fetch("/api/runs");
    const runs = await resp.json();
    state.allRuns = runs.filter(run => run.completed_at).sort((left, right) => {
      const rightTime = Date.parse(right.completed_at || "") || 0;
      const leftTime = Date.parse(left.completed_at || "") || 0;
      return rightTime - leftTime;
    });
    refreshDataSources();
    if (!state.overviewLoaded && state.allRuns.length && !state.isRunning) {
      state.overviewLoaded = true;
      loadOverview(state.allRuns[0].run_id);
    }
  } catch (err) {
    console.error("加载运行列表失败:", err);
  }
}

function refreshDataSources() {
  updateRunSelector("workspace-run");
  // 更新图表数据源
  updateRunSelector("chart-data-source");
  // 更新详细结果数据源
  updateRunSelector("detail-data-source");
  // 更新报告数据源
  updateRunSelector("report-data-source");
  // 更新对比选择框
  updateCompareCheckboxes();
}

function updateRunSelector(selectorId) {
  const sel = $("#" + selectorId);
  if (!sel) return;
  const currentVal = sel.value;
  sel.innerHTML = '<option value="">-- 选择运行 --</option>';
  state.allRuns.forEach(r => {
    const label = r.config?.label || r.run_id?.slice(0, 12) || "Unknown";
    const ts = r.completed_at ? new Date(r.completed_at).toLocaleString("zh-CN") : "";
    sel.innerHTML += `<option value="${escapeHtml(r.run_id)}">${escapeHtml(label)} (${escapeHtml(ts)})</option>`;
  });
  const preferred = currentVal || state.currentRunId || state.allRuns[0]?.run_id;
  if (preferred && state.allRuns.some(r => r.run_id === preferred)) sel.value = preferred;
}

function updateCompareCheckboxes() {
  const container = $("#compare-run-checkboxes");
  if (!container) return;
  const selected = new Set(Array.from($$(".compare-cb:checked"), cb => cb.value));
  container.innerHTML = state.allRuns.map(r => {
    const label = r.config?.label || r.run_id?.slice(0, 12) || "Unknown";
    return `
      <div class="form-check form-check-inline">
        <input class="form-check-input compare-cb" type="checkbox"
               value="${escapeHtml(r.run_id)}" id="cmp-${escapeHtml(r.run_id)}" ${selected.has(r.run_id) ? 'checked' : ''}>
        <label class="form-check-label" for="cmp-${escapeHtml(r.run_id)}">${escapeHtml(label)}</label>
      </div>
    `;
  }).join("");
}

// =============================================
// 概览仪表盘
// =============================================
async function loadOverview(runId) {
  runId ||= $("#workspace-run").value;
  if (!runId) return;
  const request = ++state.overviewRequest;
  try {
    const resp = await fetch(`/api/runs/${encodeURIComponent(runId)}`);
    const run = await resp.json();
    if (!resp.ok) throw new Error(run.error || "读取运行失败");
    if (request !== state.overviewRequest) return;
    const agg = run.display_metrics || run.aggregate_metrics || {};
    const config = run.config || {};
    const suites = run.suites || [];
    const framework = suites.find(s => s.framework)?.framework;
    const layerFlag = key => typeof framework?.[key] === "boolean" ? framework[key] :
      typeof config[key] === "boolean" ? config[key] : null;
    const layerBadge = (name, value) => `<span class="effective-layer ${value === true ? 'enabled' : ''}">${name} · ${value === null ? '未记录' : value ? '启用' : '关闭'}</span>`;
    const stats = suites.map(s => s.layer_stats).filter(Boolean);
    const sum = (group, key) => stats.reduce((total, s) => total + (s[group]?.[key] || 0), 0);
    const coverage = key => stats.reduce((total, s) => total + (s[key] || 0), 0);
    const statValue = (group, key) => coverage(group + '_records') ? formatCount(sum(group, key)) : '未记录';
    const statRows = [
      ['L1 工具结果呈现次数', statValue('isolation', 'tool_results_rendered')],
      ['L1 累计新增字符', statValue('isolation', 'added_characters_total')],
      ['L2 前置允许批次', statValue('routing', 'precheck_allowed_batches')],
      ['L2 前置拒绝批次', statValue('routing', 'precheck_rejected_batches')],
      ['L3 公开读取免审批次', statValue('routing', 'public_read_bypass_batches')],
      ['L3 实际语义调用', statValue('routing', 'semantic_audit_calls')],
    ];
    const totalTokens = s => (s.overhead?.total_tokens || 0) + (s.sec_overhead?.total_tokens || 0);
    $("#overview-content").innerHTML = `
      <div class="result-heading"><div><h3>${escapeHtml(config.label || '运行结果')}</h3><p>${escapeHtml(runId)} · ${escapeHtml(run.completed_at ? new Date(run.completed_at).toLocaleString('zh-CN') : '未完成')}</p></div><span class="result-version">${escapeHtml(config.origin ? 'AgentDojo 原生' : framework?.framework_version || config.framework_version || '历史版本 · 未记录')}</span></div>
      <div class="effective-config"><strong>本次实际配置</strong>${config.origin ? '<span>原生工具循环 · 无 DSCG 层</span>' :
        layerBadge('L1 返回隔离', layerFlag('input_isolation')) + layerBadge('L2 工具授权', layerFlag('use_sandbox')) +
        layerBadge('L2 前置检查', layerFlag('authorization_precheck')) + layerBadge('L3 动作审计', layerFlag('use_security_checker'))}</div>
      <div class="overview-cards">
        <div class="metric-card tsr"><div class="metric-label">任务成功率 TSR</div><div class="metric-value">${formatRate(agg.avg_utility_rate)}</div><small>${formatCount(agg.utility_passed)} / ${formatCount(agg.total_tasks)} 个任务成功</small></div>
        <div class="metric-card asr"><div class="metric-label">攻击成功率 ASR</div><div class="metric-value">${formatRate(agg.avg_attack_success_rate)}</div><small>${config.run_attack === false ? '良性评测不适用' : `${agg.security_denominator === null ? "有效分母未记录" : `${formatCount(agg.security_denominator)} 条原生安全判定`} · 越低越好`}</small></div>
        <div class="metric-card tokens"><div class="metric-label">${agg.security_cost_complete || config.origin || config.use_security_checker === false ? "总 Token 消耗" : "已记录 Token（审计缺失）"}</div><div class="metric-value">${formatCount(agg.total_tokens)}</div><small>主模型（含授权）${formatCount(agg.main_total_tokens)} + 审计 ${formatCount(agg.security_cost_complete || config.origin || config.use_security_checker === false ? agg.security_total_tokens : null)}</small></div>
        <div class="metric-card quality"><div class="metric-label">缺失 / 无效安全判定</div><div class="metric-value">${formatCount(agg.security_missing)}</div><small>不计为零 ASR；需核对原始结果</small></div>
      </div>
      <div class="result-section-heading"><h4>各场景结果</h4><span>TSR 按任务加权；ASR 按有效安全判定加权</span></div>
      <div class="table-responsive"><table class="table table-dark table-hover evaluation-suite-table"><thead><tr><th>场景</th><th>TSR</th><th>ASR</th><th>任务数</th><th>已记录总 Tokens</th><th>审计 Tokens</th></tr></thead><tbody>${suites.map(s => `<tr><td><strong>${escapeHtml(s.suite_name)}</strong></td><td class="text-info">${formatRate(s.metrics?.utility_rate)}</td><td class="text-danger">${formatRate(config.run_attack === false ? null : s.metrics?.attack_success_rate)}</td><td>${formatCount(s.task_counts?.total_tasks)}</td><td>${formatCount(totalTokens(s))}</td><td>${formatCount(s.sec_overhead?.total_tokens ?? (config.origin || config.use_security_checker === false ? 0 : null))}</td></tr>`).join('')}</tbody></table></div>
      ${config.origin ? '' : `<section class="layer-observations"><div class="result-section-heading"><h4>三层运行记录</h4><span>路由 ${coverage('routing_records')} / ${formatCount(agg.total_tasks)} · 隔离 ${coverage('isolation_records')} / ${formatCount(agg.total_tasks)} 条 trace</span></div><dl>${statRows.map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl><p>仅统计已计分任务，排除攻击生成预检；覆盖不全时为已记录部分。L1 字符与呈现次数含重复历史，字符数不等于 Tokens。</p></section>`}
      <div class="result-footnote"><i class="bi bi-info-circle"></i><span>ASR 使用 AgentDojo 原生判定；工具级约束与路由统计不代表独立安全验证。任务 ID、模型、攻击一致后再作比较。</span></div>
    `;
    $("#workspace-run").value = runId;
    ["chart-data-source", "detail-data-source", "report-data-source"].forEach(id => $("#" + id).value = runId);
    new bootstrap.Tab($("#tab-overview")).show();
  } catch (err) {
    if (request === state.overviewRequest) $("#overview-content").innerHTML = `<div class="empty-state"><strong>读取运行结果失败</strong><span>${escapeHtml(err.message)}</span></div>`;
  }
}

// =============================================
// 图表渲染 (Chart.js)
// =============================================
async function refreshCharts() {
  const runId = $("#chart-data-source").value;
  if (!runId) {
    alert("请先选择一个运行结果！");
    return;
  }

  try {
    const resp = await fetch(`/api/runs/${escapeHtml(runId)}`);
    const run = await resp.json();
    // 先显示面板，再创建 Chart.js 实例，避免隐藏容器导致首次宽度计算为 0。
    const chartsTab = new bootstrap.Tab($("#tab-charts"));
    chartsTab.show();
    requestAnimationFrame(() => renderSuiteCharts(run));
  } catch (err) {
    console.error("加载图表数据失败:", err);
  }
}

function renderSuiteCharts(run) {
  const suites = run.suites || [];

  if (suites.length === 0) {
    $("#charts-container").innerHTML = '<div class="placeholder-message"><p>无数据可供图表展示</p></div>';
    return;
  }

  // 销毁旧图表
  Object.values(state.charts).forEach(c => c.destroy());
  state.charts = {};

  // 指标对比柱状图
  let chartsHtml = `
    <div class="col-lg-6">
      <div class="chart-container">
        <h6>各场景可用性与防御率</h6>
        <canvas id="chart-tsr-defense"></canvas>
      </div>
    </div>
    <div class="col-lg-6">
      <div class="chart-container">
        <h6>各场景攻击成功率 (ASR)</h6>
        <canvas id="chart-asr"></canvas>
      </div>
    </div>
  `;
  $("#charts-container").innerHTML = chartsHtml;

  // Token 消耗图
  let tokenHtml = `
    <div class="col-lg-6">
      <div class="chart-container">
        <h6>各场景已记录 Token（主 + 审计）</h6>
        <canvas id="chart-tokens"></canvas>
      </div>
    </div>
    <div class="col-lg-6">
      <div class="chart-container">
        <h6>任务完成统计</h6>
        <canvas id="chart-tasks"></canvas>
      </div>
    </div>
  `;
  $("#charts-row-2").innerHTML = tokenHtml;

  const labels = suites.map(s => s.suite_name);
  const tsrData = suites.map(s => s.metrics.utility_rate);
  const defenseData = suites.map(s => run.config?.run_attack === false ? null : s.metrics.defense_success_rate);
  const asrData = suites.map(s => run.config?.run_attack === false ? null : s.metrics.attack_success_rate);
  const promptTokens = suites.map(s => (s.overhead?.prompt_tokens || 0) + (s.sec_overhead?.prompt_tokens || 0));
  const completionTokens = suites.map(s => (s.overhead?.completion_tokens || 0) + (s.sec_overhead?.completion_tokens || 0));
  const totalTasks = suites.map(s => s.task_counts.total_tasks);
  const passedTasks = suites.map(s => s.task_counts.utility_passed);

  // 可用性与防御率：用折线强调跨场景趋势，避免双柱挤在一起。
  state.charts.tsrDefense = new Chart($("#chart-tsr-defense"), {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "可用性 TSR (%)",
          data: tsrData,
          borderColor: "#75a7ee",
          backgroundColor: "rgba(117, 167, 238, 0.10)",
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: "#75a7ee",
          tension: 0.32,
        },
        {
          label: "防御成功率 (%)",
          data: defenseData,
          borderColor: "#48c6a4",
          backgroundColor: "rgba(72, 198, 164, 0.08)",
          borderWidth: 2,
          pointRadius: 3,
          pointHoverRadius: 5,
          pointBackgroundColor: "#48c6a4",
          tension: 0.32,
        },
      ],
    },
    options: getMetricOptions("%"),
  });

  // ASR：用带填充的趋势线突出高风险场景。
  state.charts.asr = new Chart($("#chart-asr"), {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "攻击成功率 ASR (%)",
        data: asrData,
        backgroundColor: "rgba(237, 116, 116, 0.12)",
        borderColor: "#ed7474",
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        pointBackgroundColor: "#ed7474",
        tension: 0.32,
        fill: true,
      }],
    },
    options: getMetricOptions("%"),
  });

  // Token 消耗堆叠图
  state.charts.tokens = new Chart($("#chart-tokens"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "已记录 Prompt（主 + 审计，K）",
          data: promptTokens.map(v => v / 1000),
          backgroundColor: "rgba(176, 147, 229, 0.68)",
          borderColor: "#b093e5",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 24,
        },
        {
          label: "已记录 Completion（主 + 审计，K）",
          data: completionTokens.map(v => v / 1000),
          backgroundColor: "rgba(117, 167, 238, 0.68)",
          borderColor: "#75a7ee",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 24,
        },
      ],
    },
    options: getBarOptions("Tokens (K)", { stacked: true }),
  });

  // 任务统计
  state.charts.tasks = new Chart($("#chart-tasks"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "总任务数",
          data: totalTasks,
          backgroundColor: "rgba(116, 129, 125, 0.35)",
          borderColor: "#74817d",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 22,
        },
        {
          label: "通过任务数",
          data: passedTasks,
          backgroundColor: "rgba(72, 198, 164, 0.72)",
          borderColor: "#48c6a4",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 22,
        },
      ],
    },
    options: getBarOptions("任务数"),
  });
}

function getBarOptions(yLabel, { stacked = false, max = undefined } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        position: "bottom",
        labels: { color: "#a7b1ae", boxWidth: 10, boxHeight: 10, padding: 14, font: { size: 10 } },
      },
      tooltip: { padding: 10, displayColors: true },
    },
    datasets: {
      bar: { categoryPercentage: 0.58, barPercentage: 0.45, maxBarThickness: 26 },
    },
    scales: {
      x: { ...getXScale(), stacked },
      y: {
        beginAtZero: true,
        stacked,
        suggestedMax: max,
        ticks: { color: "#a7b1ae", maxTicksLimit: 6 },
        grid: { color: "rgba(70, 80, 77, 0.32)" },
        title: {
          display: true,
          text: yLabel,
          color: "#74817d",
          font: { size: 10 },
        },
      },
    },
  };
}

function getMetricOptions(yLabel) {
  return {
    ...getBarOptions(yLabel, { max: 100 }),
    elements: {
      line: { tension: 0.32 },
      point: { borderWidth: 2 },
    },
    scales: {
      x: getXScale(),
      y: {
        beginAtZero: true,
        min: -5, max: 105,
        ticks: { color: "#a7b1ae", maxTicksLimit: 6, stepSize: 20, callback: value => value >= 0 && value <= 100 ? `${value}%` : "" },
        grid: { color: "rgba(70, 80, 77, 0.32)" },
        title: { display: true, text: yLabel, color: "#74817d", font: { size: 10 } },
      },
    },
  };
}

function getXScale() {
  return {
    ticks: { color: "#a7b1ae", font: { size: 10, weight: "600" }, maxRotation: 0 },
    grid: { display: false },
  };
}

// =============================================
// 详细结果表格
// =============================================
async function refreshDetailTable() {
  const runId = $("#detail-data-source").value;
  const suiteFilter = $("#detail-suite-filter").value;

  if (!runId) {
    alert("请先选择一个运行结果！");
    return;
  }

  try {
    const resp = await fetch(`/api/runs/${escapeHtml(runId)}`);
    const run = await resp.json();
    const records = run.structured_records || [];

    // 更新套件过滤器
    const suiteSet = new Set(records.map(r => r.suite_name));
    const suiteSel = $("#detail-suite-filter");
    suiteSel.innerHTML = '<option value="all">全部</option>';
    suiteSet.forEach(s => {
      suiteSel.innerHTML += `<option value="${s}">${s}</option>`;
    });
    if (suiteFilter && suiteSet.has(suiteFilter)) {
      suiteSel.value = suiteFilter;
    }

    const filtered = suiteFilter === "all"
      ? records
      : records.filter(r => r.suite_name === suiteFilter);

    const container = $("#detail-table-container");
    if (filtered.length === 0) {
      container.innerHTML = '<div class="placeholder-message"><p>无符合条件的记录</p></div>';
      return;
    }

    container.innerHTML = `
      <table class="table table-dark table-hover table-sm">
        <thead>
          <tr>
            <th>场景</th>
            <th>用户任务 ID</th>
            <th>注入任务 ID</th>
            <th>可用性</th>
            <th>攻击成功</th>
            <th>防御成功</th>
          </tr>
        </thead>
        <tbody>
          ${filtered.map(r => `
            <tr>
              <td>${escapeHtml(r.suite_name)}</td>
              <td><code>${escapeHtml(r.user_task_id)}</code></td>
              <td><code>${escapeHtml(r.injection_task_id)}</code></td>
              <td><span class="result-badge ${r.utility_success ? 'pass' : 'fail'}">${r.utility_success ? '成功' : '失败'}</span></td>
              <td>${r.attack_success === null ? '<span class="result-badge neutral">N/A</span>' : (r.attack_success ? '<span class="result-badge fail">被攻破</span>' : '<span class="result-badge pass">安全</span>')}</td>
              <td>${r.defense_success === null ? '<span class="result-badge neutral">N/A</span>' : (r.defense_success ? '<span class="result-badge pass">成功</span>' : '<span class="result-badge fail">失败</span>')}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;

    const detailTab = new bootstrap.Tab($("#tab-detail"));
    detailTab.show();
  } catch (err) {
    console.error("加载详细结果失败:", err);
  }
}

// =============================================
// 对比分析
// =============================================
async function runComparison() {
  const checkboxes = $$(".compare-cb:checked");
  const runIds = Array.from(checkboxes).map(cb => cb.value);

  if (runIds.length < 2) {
    alert("请至少选择 2 个运行结果进行对比！");
    return;
  }

  try {
    const resp = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_ids: runIds }),
    });
    const data = await resp.json();
    renderComparison(data);

    const compareTab = new bootstrap.Tab($("#tab-compare"));
    compareTab.show();
  } catch (err) {
    console.error("对比分析失败:", err);
  }
}

function renderComparison(data) {
  // 销毁旧图表
  Object.values(state.comparisonCharts).forEach(c => c.destroy());
  state.comparisonCharts = {};

  const container = $("#compare-results");

  let html = `
    <div class="mb-3"><span class="section-kicker">Comparison</span><h5 class="mb-0">多配置对比分析</h5></div>
    <div class="row">
      <div class="col-lg-4">
        <div class="chart-container">
          <h6>可用性 & 防御率对比</h6>
          <canvas id="cmp-tsr-defense"></canvas>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="chart-container">
          <h6>攻击成功率 (ASR) 对比</h6>
          <canvas id="cmp-asr"></canvas>
        </div>
      </div>
      <div class="col-lg-4">
        <div class="chart-container">
          <h6>已记录 Token 对比 (M)</h6>
          <canvas id="cmp-tokens"></canvas>
        </div>
      </div>
    </div>
  `;

  // 按套件对比
  if (Object.keys(data.per_suite).length > 0) {
    html += '<div class="row mt-3">';
    Object.entries(data.per_suite).forEach(([suiteName, suiteData]) => {
      html += `
        <div class="col-lg-6 mb-3">
          <div class="chart-container">
            <h6>${suiteName} - 各配置指标对比</h6>
            <canvas id="cmp-suite-${suiteName}"></canvas>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }

  container.innerHTML = html;

  const labels = data.labels;

  // TSR + Defense 对比
  const tsrMetric = data.metrics.find(m => m.name === "avg_utility_rate");
  const defMetric = data.metrics.find(m => m.name === "avg_defense_success_rate");
  state.comparisonCharts.tsrDef = new Chart($("#cmp-tsr-defense"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "TSR (%)",
          data: tsrMetric?.values || [],
          backgroundColor: "rgba(59, 130, 246, 0.7)",
          borderColor: "#3b82f6",
          borderWidth: 1,
          borderRadius: 6,
        },
        {
          label: "Defense (%)",
          data: defMetric?.values || [],
          backgroundColor: "rgba(16, 185, 129, 0.7)",
          borderColor: "#10b981",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: getBarOptions("%"),
  });

  // ASR 对比
  const asrMetric = data.metrics.find(m => m.name === "avg_attack_success_rate");
  state.comparisonCharts.asr = new Chart($("#cmp-asr"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "ASR (%)",
        data: asrMetric?.values || [],
        backgroundColor: "rgba(239, 68, 68, 0.7)",
        borderColor: "#ef4444",
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: getBarOptions("%"),
  });

  // Token 对比
  const tokenData = data.token_metrics || {};
  state.comparisonCharts.tokens = new Chart($("#cmp-tokens"), {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "已记录总 Tokens (M)",
        data: (tokenData.total_tokens || []).map(v => v / 1000000),
        backgroundColor: "rgba(245, 158, 11, 0.7)",
        borderColor: "#f59e0b",
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: getBarOptions("Millions"),
  });

  // 按套件的对比图
  Object.entries(data.per_suite).forEach(([suiteName, suiteData]) => {
    const canvasId = `cmp-suite-${suiteName}`;
    const canvas = $("#" + canvasId);
    if (!canvas) return;

    state.comparisonCharts[`suite_${suiteName}`] = new Chart(canvas, {
      type: "bar",
      data: {
        labels: suiteData.labels,
        datasets: [
          {
            label: "TSR (%)",
            data: suiteData.utility_rates,
            backgroundColor: "rgba(59, 130, 246, 0.6)",
            borderColor: "#3b82f6",
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: "Defense (%)",
            data: suiteData.defense_rates,
            backgroundColor: "rgba(16, 185, 129, 0.6)",
            borderColor: "#10b981",
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: "ASR (%)",
            data: suiteData.attack_rates,
            type: "line",
            borderColor: "#ef4444",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 5,
            pointBackgroundColor: "#ef4444",
          },
        ],
      },
      options: getBarOptions("%"),
    });
  });
}

// =============================================
// 报告
// =============================================
async function loadReport() {
  const runId = $("#report-data-source").value;
  if (!runId) {
    alert("请先选择一个运行结果！");
    return;
  }

  try {
    const resp = await fetch(`/api/runs/${escapeHtml(runId)}`);
    const run = await resp.json();

    // 设置下载链接
    const downloadBtn = $("#btn-download-report");
    downloadBtn.style.display = "inline-block";
    downloadBtn.href = `/api/report/${escapeHtml(runId)}`;

    // 渲染 HTML 报告
    const agg = run.display_metrics || run.aggregate_metrics || {};
    const config = run.config || {};
    const auditModel = config.origin || config.use_security_checker === false
      ? '未使用'
      : config.use_security_checker === true
        ? config.resolved_security_model?.model_id || config.sec_model_id || 'Local/Env 配置'
        : '未记录';

    const container = $("#report-content");
    container.innerHTML = `
      <div class="report-sheet">
        <div class="mb-3"><span class="section-kicker">Experiment report</span><h4>安全测试报告</h4></div>
        <hr style="border-color: var(--border-color);">

        <h6>测试配置</h6>
        <table class="table table-dark table-sm w-auto">
          <tr><td class="text-muted">运行 ID</td><td>${escapeHtml(runId)}</td></tr>
          <tr><td class="text-muted">完成时间</td><td>${run.completed_at || "N/A"}</td></tr>
          <tr><td class="text-muted">主模型</td><td>${escapeHtml(config.resolved_main_model?.model_id || config.model_id || "Local/Env 配置")}</td></tr>
          <tr><td class="text-muted">审计模型</td><td>${escapeHtml(auditModel)}</td></tr>
          <tr><td class="text-muted">测试套件</td><td>${escapeHtml((config.suites || []).join(", "))}</td></tr>
          <tr><td class="text-muted">攻击模式</td><td>${config.run_attack ? "启用" : "禁用"}</td></tr>
          <tr><td class="text-muted">攻击类型</td><td>${escapeHtml(config.run_attack === false ? "不适用" : config.attack_name || "未记录")}</td></tr>
          <tr><td class="text-muted">框架</td><td>${config.origin ? "原始模型" : "DSCG"}</td></tr>
          ${config.defense ? `<tr><td class="text-muted">AgentDojo 防御</td><td>${escapeHtml(config.defense)}</td></tr>` : ""}
          ${!config.origin ? `
            <tr><td class="text-muted">框架版本</td><td>${escapeHtml(config.framework_version || '未记录')}</td></tr>
            ${[['input_isolation','L1 工具返回隔离'],['use_sandbox','L2 工具授权'],['authorization_precheck','L2 前置检查'],['use_security_checker','L3 动作审计']].map(([key,label]) => `<tr><td class="text-muted">${label}</td><td>${typeof config[key] === 'boolean' ? config[key] ? '启用' : '关闭' : '未记录'}</td></tr>`).join('')}
          ` : ""}
        </table>

        <h6 class="mt-3">聚合指标</h6>
        <div class="overview-cards">
          <div class="metric-card tsr">
            <div class="metric-value">${formatRate(agg.avg_utility_rate)}</div>
            <div class="metric-label">平均可用性 (TSR)</div>
          </div>
          <div class="metric-card asr">
            <div class="metric-value">${formatRate(agg.avg_attack_success_rate)}</div>
            <div class="metric-label">平均攻击成功率 (ASR)</div>
          </div>
          <div class="metric-card defense">
            <div class="metric-value">${formatRate(agg.avg_defense_success_rate)}</div>
            <div class="metric-label">平均防御成功率</div>
          </div>
          <div class="metric-card tokens">
            <div class="metric-value">${formatCount(agg.total_tokens)}</div>
            <div class="metric-label">已记录总 Token（主 + 审计）</div>
          </div>
        </div>

        <h6 class="mt-3">分场景结果</h6>
        <div class="table-responsive">
          <table class="table table-dark table-hover">
            <thead>
              <tr><th>场景</th><th>TSR (%)</th><th>ASR (%)</th><th>Defense (%)</th>
                  <th>任务数</th><th>已记录 Prompt</th><th>已记录 Completion</th></tr>
            </thead>
            <tbody>
              ${(run.suites || []).map(s => `
                <tr>
                  <td><strong>${escapeHtml(s.suite_name)}</strong></td>
                  <td class="text-info">${formatRate(s.metrics.utility_rate)}</td>
                  <td class="text-danger">${formatRate(config.run_attack === false ? null : s.metrics.attack_success_rate)}</td>
                  <td class="text-success">${formatRate(config.run_attack === false ? null : s.metrics.defense_success_rate)}</td>
                  <td>${s.task_counts.total_tasks}</td>
                  <td>${formatCount((s.overhead?.prompt_tokens || 0) + (s.sec_overhead?.prompt_tokens || 0))}</td>
                  <td>${formatCount((s.overhead?.completion_tokens || 0) + (s.sec_overhead?.completion_tokens || 0))}</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;

    const reportTab = new bootstrap.Tab($("#tab-report"));
    reportTab.show();
  } catch (err) {
    console.error("生成报告失败:", err);
  }
}

// =============================================
// 快捷对比模板
// =============================================
async function quickCompare(template) {
  const runs = state.allRuns;
  if (runs.length < 2) {
    alert("需要至少 2 个运行结果才能进行对比。请先运行一些测试！");
    return;
  }

  let runIds = [];
  const isOrigin = r => r.config?.origin === true || r.config?.origin === "true";

  switch (template) {
    case "baseline_vs_newframe":
      // 选一个 origin 和一个 newframe
      const baseline = runs.find(r => isOrigin(r));
      const nf = runs.find(r => !isOrigin(r) && r.config?.use_sandbox !== false && r.config?.use_security_checker !== false);
      if (baseline) runIds.push(baseline.run_id);
      if (nf) runIds.push(nf.run_id);
      if (runIds.length < 2) {
        // fallback: 取最近两个
        runIds = runs.slice(0, 2).map(r => r.run_id);
      }
      break;

    case "ablation_study":
      // 找 newframe 的不同消融配置
      const nfRuns = runs.filter(r => !isOrigin(r));
      // 优先: OursFull, NoSandbox, NoChecker
      const full = nfRuns.find(r => r.run_id.includes("OursFull") || (r.config?.use_sandbox !== false && r.config?.use_security_checker !== false));
      const noSB = nfRuns.find(r => r.config?.use_sandbox === false);
      const noSC = nfRuns.find(r => r.config?.use_security_checker === false);
      if (full) runIds.push(full.run_id);
      if (noSB) runIds.push(noSB.run_id);
      if (noSC) runIds.push(noSC.run_id);
      if (runIds.length < 2) {
        runIds = nfRuns.slice(0, 3).map(r => r.run_id);
      }
      break;

    case "defense_comparison":
      // 找 origin 中不同 defense 的
      const defRuns = runs.filter(r => isOrigin(r));
      runIds = defRuns.slice(0, 5).map(r => r.run_id);
      break;
  }

  if (runIds.length < 2) {
    alert(`模板 "${template}" 需要至少 2 个匹配的运行结果，当前只有 ${runIds.length} 个。`);
    return;
  }

  // 勾选对应 checkbox
  $$(".compare-cb").forEach(cb => {
    cb.checked = runIds.includes(cb.value);
  });

  // 自动执行对比
  await runComparison();
}

// =============================================
// 事件委托：标签页切换时自动加载数据
// =============================================
document.addEventListener("click", (e) => {
  if (e.target.matches("#tab-overview, #tab-overview *")) {
    const runId = $("#workspace-run").value || state.currentRunId;
    if (runId) loadOverview(runId);
  }
  if (e.target.matches("#tab-charts, #tab-charts *")) {
    if ($("#chart-data-source").value) refreshCharts();
  }
  if (e.target.matches("#tab-detail, #tab-detail *")) {
    if ($("#detail-data-source").value) refreshDetailTable();
  }
  if (e.target.matches("#tab-report, #tab-report *")) {
    if ($("#report-data-source").value) loadReport();
  }
});
