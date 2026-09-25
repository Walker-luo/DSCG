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
    const isOrigin = e.target.value === "origin";
    $("#sec-model-group").style.display = isOrigin ? "none" : "block";
    $("#sec-connection-group").style.display = isOrigin ? "none" : "block";
    $("#defense-group").style.display = isOrigin ? "block" : "none";
    $("#ablation-group").style.display = isOrigin ? "none" : "block";
    updateRunPreview();
  });

  // 攻击模式切换
  $("#run-attack").addEventListener("change", (e) => {
    const isAttack = e.target.value === "true";
    $("#attack-type-group").style.display = isAttack ? "block" : "none";
    updateRunPreview();
  });

  // 启动测试
  $("#btn-run").addEventListener("click", startRun);
  $("#btn-stop").addEventListener("click", stopRun);

  // 日志过滤
  $("#filter-errors").addEventListener("change", toggleLogFilter);

  [
    "#model-id", "#sec-model-id", "#defense", "#use-sandbox",
    "#use-security-checker", "#max-user-tasks", "#max-injection-tasks",
    "#api-key", "#base-url", "#sec-api-key", "#sec-base-url",
    "#tool-metadata-path",
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
    sec_model_id: isOrigin ? null : ($("#sec-model-id").value || null),
    sec_provider: isOrigin ? null : (secOption?.dataset.provider || null),
    sec_api_key: isOrigin ? null : (customSecApiKey || null),
    sec_base_url: isOrigin ? null : (customSecBaseUrl || null),
    suites: suites,
    run_attack: $("#run-attack").value === "true",
    origin: isOrigin,
    defense: isOrigin && $("#defense").value ? $("#defense").value : null,
    attack_name: $("#attack-name").value,
    use_sandbox: !isOrigin && $("#use-sandbox").checked,
    use_security_checker: !isOrigin && $("#use-security-checker").checked,
    max_user_tasks: parseInt($("#max-user-tasks").value) || 0,
    max_injection_tasks: parseInt($("#max-injection-tasks").value) || 0,
    tool_metadata_path: $("#tool-metadata-path").value.trim() || null,
  };
}

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
  let defenseLabel = "Baseline";
  if (isOrigin) {
    defenseLabel = $("#defense")?.selectedOptions[0]?.textContent || "Baseline";
  } else if ($("#use-sandbox")?.checked && $("#use-security-checker")?.checked) {
    defenseLabel = "完整防御";
  } else if ($("#use-sandbox")?.checked) {
    defenseLabel = "仅沙箱";
  } else if ($("#use-security-checker")?.checked) {
    defenseLabel = "仅审计";
  } else {
    defenseLabel = "无防御";
  }

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

  if (config.suites.length === 0) {
    alert("请至少选择一个测试场景！");
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
    connectSSE(data.run_id);

  } catch (err) {
    console.error("启动测试失败:", err);
    alert("启动测试失败: " + err.message);
    state.isRunning = false;
    $("#btn-run").disabled = false;
    $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始测试';
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
  $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始测试';
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

  const es = new EventSource(`/api/stream/${runId}`);
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
  indicator.innerHTML = `<span class="status-dot"></span><span>${text}</span>`;
}

// =============================================
// 测试完成处理
// =============================================
function onRunComplete(msg) {
  state.isRunning = false;
  $("#btn-run").disabled = false;
  $("#btn-run").innerHTML = '<i class="bi bi-play-fill"></i> 开始测试';
  $("#btn-stop").style.display = "none";
  updateStatus("completed", "已完成");
  if ($("#live-context")) $("#live-context").textContent = "运行已完成";

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
  setTimeout(() => {
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
    state.allRuns = runs.sort((left, right) => {
      const rightTime = Date.parse(right.completed_at || "") || 0;
      const leftTime = Date.parse(left.completed_at || "") || 0;
      return rightTime - leftTime;
    });
    refreshDataSources();
  } catch (err) {
    console.error("加载运行列表失败:", err);
  }
}

function refreshDataSources() {
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
    sel.innerHTML += `<option value="${r.run_id}">${label} (${ts})</option>`;
  });
  const preferred = currentVal || state.currentRunId || state.allRuns[0]?.run_id;
  if (preferred && state.allRuns.some(r => r.run_id === preferred)) sel.value = preferred;
}

function updateCompareCheckboxes() {
  const container = $("#compare-run-checkboxes");
  if (!container) return;
  container.innerHTML = state.allRuns.map(r => {
    const label = r.config?.label || r.run_id?.slice(0, 12) || "Unknown";
    return `
      <div class="form-check form-check-inline">
        <input class="form-check-input compare-cb" type="checkbox"
               value="${r.run_id}" id="cmp-${r.run_id}">
        <label class="form-check-label" for="cmp-${r.run_id}">${label}</label>
      </div>
    `;
  }).join("");
}

// =============================================
// 概览仪表盘
// =============================================
async function loadOverview(runId) {
  if (!runId) {
    runId = $("#chart-data-source").value;
  }
  if (!runId) {
    alert("请先选择一个运行结果！");
    return;
  }

  try {
    const resp = await fetch(`/api/runs/${runId}`);
    const run = await resp.json();
    const agg = run.aggregate_metrics || {};

    const container = $("#overview-content");
    container.innerHTML = `
      <div class="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div><span class="section-kicker">Run summary</span><h5 class="mb-0">测试概览</h5></div>
        <code class="text-muted small">${runId}</code>
      </div>
      <div class="overview-cards">
        <div class="metric-card tsr">
          <div class="metric-icon"><i class="bi bi-check-circle"></i></div>
          <div class="metric-value">${agg.avg_utility_rate ?? "N/A"}%</div>
          <div class="metric-label">平均可用性 (TSR)</div>
        </div>
        <div class="metric-card asr">
          <div class="metric-icon"><i class="bi bi-shield-exclamation"></i></div>
          <div class="metric-value">${agg.avg_attack_success_rate ?? "N/A"}%</div>
          <div class="metric-label">平均攻击成功率 (ASR)</div>
        </div>
        <div class="metric-card defense">
          <div class="metric-icon"><i class="bi bi-shield-check"></i></div>
          <div class="metric-value">${agg.avg_defense_success_rate ?? "N/A"}%</div>
          <div class="metric-label">平均防御成功率</div>
        </div>
        <div class="metric-card tokens">
          <div class="metric-icon"><i class="bi bi-coin"></i></div>
          <div class="metric-value">${((agg.total_tokens || 0) / 1000000).toFixed(2)}M</div>
          <div class="metric-label">总 Token 消耗</div>
        </div>
      </div>

      <h6 class="mt-3 mb-2">各场景详情</h6>
      <div class="table-responsive">
        <table class="table table-dark table-hover">
          <thead>
            <tr>
              <th>场景</th>
              <th>Pipeline</th>
              <th>TSR (%)</th>
              <th>ASR (%)</th>
              <th>Defense (%)</th>
              <th>任务数</th>
              <th>Tokens</th>
            </tr>
          </thead>
          <tbody>
            ${(run.suites || []).map(s => `
              <tr>
                <td><strong>${s.suite_name}</strong></td>
                <td><small>${s.pipeline_name || "-"}</small></td>
                <td class="text-info">${s.metrics.utility_rate.toFixed(1)}</td>
                <td class="text-danger">${s.metrics.attack_success_rate.toFixed(1)}</td>
                <td class="text-success">${s.metrics.defense_success_rate.toFixed(1)}</td>
                <td>${s.task_counts.total_tasks}</td>
                <td>${(s.overhead.total_tokens / 1000).toFixed(1)}K</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;

    // 切换到概览面板
    const overviewTab = new bootstrap.Tab($("#tab-overview"));
    overviewTab.show();
  } catch (err) {
    console.error("加载概览失败:", err);
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
    const resp = await fetch(`/api/runs/${runId}`);
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
        <h6>各场景 Token 消耗</h6>
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
  const defenseData = suites.map(s => s.metrics.defense_success_rate);
  const asrData = suites.map(s => s.metrics.attack_success_rate);
  const promptTokens = suites.map(s => s.overhead.prompt_tokens);
  const completionTokens = suites.map(s => s.overhead.completion_tokens);
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
        pointBackgroundColor: asrData.map(v => v > 30 ? "#ed7474" : "#e9b35f"),
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
          label: "Prompt Tokens (K)",
          data: promptTokens.map(v => v / 1000),
          backgroundColor: "rgba(176, 147, 229, 0.68)",
          borderColor: "#b093e5",
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 24,
        },
        {
          label: "Completion Tokens (K)",
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
        max: 100,
        ticks: { color: "#a7b1ae", maxTicksLimit: 6, callback: value => `${value}%` },
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
    const resp = await fetch(`/api/runs/${runId}`);
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
              <td>${r.suite_name}</td>
              <td><code>${r.user_task_id}</code></td>
              <td><code>${r.injection_task_id}</code></td>
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
          <h6>Token 消耗对比 (M)</h6>
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
        label: "Total Tokens (M)",
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
    const resp = await fetch(`/api/runs/${runId}`);
    const run = await resp.json();

    // 设置下载链接
    const downloadBtn = $("#btn-download-report");
    downloadBtn.style.display = "inline-block";
    downloadBtn.href = `/api/report/${runId}`;

    // 渲染 HTML 报告
    const agg = run.aggregate_metrics || {};
    const config = run.config || {};

    const container = $("#report-content");
    container.innerHTML = `
      <div class="report-sheet">
        <div class="mb-3"><span class="section-kicker">Experiment report</span><h4>安全测试报告</h4></div>
        <hr style="border-color: var(--border-color);">

        <h6>测试配置</h6>
        <table class="table table-dark table-sm w-auto">
          <tr><td class="text-muted">运行 ID</td><td>${runId}</td></tr>
          <tr><td class="text-muted">完成时间</td><td>${run.completed_at || "N/A"}</td></tr>
          <tr><td class="text-muted">主模型</td><td>${config.model_id || "N/A"}</td></tr>
          <tr><td class="text-muted">审计模型</td><td>${config.sec_model_id || "无"}</td></tr>
          <tr><td class="text-muted">测试套件</td><td>${(config.suites || []).join(", ")}</td></tr>
          <tr><td class="text-muted">攻击模式</td><td>${config.run_attack ? "启用" : "禁用"}</td></tr>
          <tr><td class="text-muted">攻击类型</td><td>${config.attack_name || "N/A"}</td></tr>
          <tr><td class="text-muted">框架</td><td>${config.origin ? "原始模型" : "DSCG"}</td></tr>
          ${config.defense ? `<tr><td class="text-muted">AgentDojo 防御</td><td>${config.defense}</td></tr>` : ""}
          ${!config.origin ? `
            <tr><td class="text-muted">沙箱</td><td>${config.use_sandbox !== false ? "启用" : "禁用"}</td></tr>
            <tr><td class="text-muted">安全校验器</td><td>${config.use_security_checker !== false ? "启用" : "禁用"}</td></tr>
          ` : ""}
        </table>

        <h6 class="mt-3">聚合指标</h6>
        <div class="overview-cards">
          <div class="metric-card tsr">
            <div class="metric-value">${agg.avg_utility_rate ?? "N/A"}%</div>
            <div class="metric-label">平均可用性 (TSR)</div>
          </div>
          <div class="metric-card asr">
            <div class="metric-value">${agg.avg_attack_success_rate ?? "N/A"}%</div>
            <div class="metric-label">平均攻击成功率 (ASR)</div>
          </div>
          <div class="metric-card defense">
            <div class="metric-value">${agg.avg_defense_success_rate ?? "N/A"}%</div>
            <div class="metric-label">平均防御成功率</div>
          </div>
          <div class="metric-card tokens">
            <div class="metric-value">${((agg.total_tokens || 0) / 1000000).toFixed(2)}M</div>
            <div class="metric-label">总 Token 消耗</div>
          </div>
        </div>

        <h6 class="mt-3">分场景结果</h6>
        <div class="table-responsive">
          <table class="table table-dark table-hover">
            <thead>
              <tr><th>场景</th><th>TSR (%)</th><th>ASR (%)</th><th>Defense (%)</th>
                  <th>任务数</th><th>Prompt Tokens</th><th>Completion Tokens</th></tr>
            </thead>
            <tbody>
              ${(run.suites || []).map(s => `
                <tr>
                  <td><strong>${s.suite_name}</strong></td>
                  <td class="text-info">${s.metrics.utility_rate.toFixed(1)}</td>
                  <td class="text-danger">${s.metrics.attack_success_rate.toFixed(1)}</td>
                  <td class="text-success">${s.metrics.defense_success_rate.toFixed(1)}</td>
                  <td>${s.task_counts.total_tasks}</td>
                  <td>${(s.overhead.prompt_tokens / 1000).toFixed(1)}K</td>
                  <td>${(s.overhead.completion_tokens / 1000).toFixed(1)}K</td>
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
    const runId = state.currentRunId || $("#chart-data-source").value;
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
