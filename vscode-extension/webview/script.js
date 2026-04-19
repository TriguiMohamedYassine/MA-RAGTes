const vscode = acquireVsCodeApi();

const state = {
  snapshot: null,
  selectedContract: null,
  selectedUserStoryPath: "",
  selectedEnvironment: "simulation",
  selectedRunId: "",
  selectedRunDetails: null,
  filters: {
    query: "",
    status: "all",
    sort: "newest",
  },
  pipelineSteps: [
    { key: "test_designer", label: "Designer" },
    { key: "generator_normal", label: "Generator" },
    { key: "executor", label: "Executor" },
    { key: "analyzer", label: "Analyzer" },
    { key: "evaluator", label: "Evaluator" },
  ],
};

const dom = {
  selectContractBtn: document.getElementById('selectContractBtn'),
  selectUserStoryBtn: document.getElementById('selectUserStoryBtn'),
  submitBtn: document.getElementById('submitBtn'),
  openContractBtn: document.getElementById('openContractBtn'),
  latestResultBtn: document.getElementById('latestResultBtn'),
  openDashboardBtn: document.getElementById('openDashboardBtn'),
  refreshHistoryBtn: document.getElementById('refreshHistoryBtn'),
  environmentSelect: document.getElementById('environmentSelect'),
  userStoryInput: document.getElementById('userStoryInput'),
  contractInfo: document.getElementById('contractInfo'),
  statusBadge: document.getElementById('statusBadge'),
  statusMessage: document.getElementById('statusMessage'),
  progressFill: document.getElementById('progressFill'),
  pipelineTimeline: document.getElementById('pipelineTimeline'),
  runMeta: document.getElementById('runMeta'),
  quickSummary: document.getElementById('quickSummary'),
  resultError: document.getElementById('resultError'),
  historyList: document.getElementById('historyList'),
  historySearch: document.getElementById('historySearch'),
  historyStatusFilter: document.getElementById('historyStatusFilter'),
  historySort: document.getElementById('historySort'),
  runDetailsMeta: document.getElementById('runDetailsMeta'),
  runDetailsError: document.getElementById('runDetailsError'),
  runDetailsCode: document.getElementById('runDetailsCode'),
  runDetailsLogs: document.getElementById('runDetailsLogs'),
};

document.addEventListener('DOMContentLoaded', () => {
  wireEvents();
  requestInitialData();
});

function wireEvents() {
  dom.selectContractBtn?.addEventListener('click', () => vscode.postMessage({ type: 'select-contract' }));
  dom.selectUserStoryBtn?.addEventListener('click', () => vscode.postMessage({ type: 'select-user-story' }));
  dom.submitBtn?.addEventListener('click', handleSubmit);
  dom.openContractBtn?.addEventListener('click', handleOpenContractFile);
  dom.latestResultBtn?.addEventListener('click', () => vscode.postMessage({ type: 'open-latest-result' }));
  dom.openDashboardBtn?.addEventListener('click', () => vscode.postMessage({ type: 'open-dashboard' }));
  dom.refreshHistoryBtn?.addEventListener('click', refreshHistory);
  dom.historyRefreshBtn?.addEventListener('click', refreshHistory);
  dom.rerunBtn?.addEventListener('click', handleRerun);
  dom.copyCodeBtn?.addEventListener('click', handleCopyTestCode);
  dom.copyCodeInlineBtn?.addEventListener('click', handleCopyTestCode);
  dom.downloadReportBtn?.addEventListener('click', handleDownloadReport);

  dom.environmentSelect?.addEventListener('change', () => {
    state.selectedEnvironment = dom.environmentSelect.value;
    renderRunMeta();
  });

  dom.historySearch?.addEventListener('input', () => {
    state.filters.query = dom.historySearch.value.trim().toLowerCase();
    renderHistory();
  });

  dom.historyStatusFilter?.addEventListener('change', () => {
    state.filters.status = dom.historyStatusFilter.value;
    renderHistory();
  });

  dom.historySort?.addEventListener('change', () => {
    state.filters.sort = dom.historySort.value;
    renderHistory();
  });

  window.addEventListener('message', handleMessage);
}

function requestInitialData() {
  vscode.postMessage({ type: 'request-initial-data' });
  vscode.postMessage({ type: 'get-settings' });
}

function handleMessage(event) {
  const message = event.data;

  switch (message.type) {
    case 'dashboard-state':
      applySnapshot(message.snapshot);
      break;
    case 'settings-loaded':
      applySettings(message);
      break;
    case 'contract-selected':
      state.selectedContract = message.contract || null;
      renderContract();
      renderRunMeta();
      break;
    case 'user-story-selected':
      state.selectedUserStoryPath = message.filePath || "";
      if (dom.userStoryInput) {
        dom.userStoryInput.value = message.text || '';
      }
      break;
    case 'environment-selected':
      state.selectedEnvironment = message.environment || state.selectedEnvironment;
      if (dom.environmentSelect) {
        dom.environmentSelect.value = state.selectedEnvironment;
      }
      renderRunMeta();
      break;
    case 'run-progress':
      applyRunProgress(message.status);
      break;
    case 'run-details':
      if (message.runId) {
        state.selectedRunId = message.runId;
      }
      state.selectedRunDetails = message.details || null;
      renderSelectedRunDetails();
      renderQuickSummary();
      break;
    case 'focus-run':
      state.selectedRunId = message.runId || "";
      renderSelectedRunDetails();
      break;
    case 'focus-section':
      focusSection(message.section);
      break;
    case 'error':
      showError(message.message || 'Unknown error');
      break;
  }
}

function applySnapshot(snapshot) {
  state.snapshot = snapshot || null;
  state.selectedContract = snapshot?.contract || state.selectedContract;
  state.selectedRunId = snapshot?.selectedRunId || '';
  if (!state.selectedRunId || state.selectedRunDetails?.run_id !== state.selectedRunId) {
    state.selectedRunDetails = null;
  }
  state.selectedEnvironment = snapshot?.lastEnvironment || state.selectedEnvironment || 'simulation';

  if (dom.environmentSelect) {
    dom.environmentSelect.value = state.selectedEnvironment;
  }



  renderContract();
  const initialStatus = snapshot?.apiHealthy === false ? 'error' : 'idle';
  const initialMessage = snapshot?.apiHealthy === false
    ? 'API is unreachable on http://localhost:8000.'
    : 'Ready to submit a contract.';
  renderStatus(initialStatus, initialMessage);
  renderTimeline(null);
  renderHistory();
  renderQuickSummary();
  renderSelectedRunDetails();
}

function applySettings(settings) {
  if (settings?.defaultEnvironment) {
    state.selectedEnvironment = settings.defaultEnvironment;
    if (dom.environmentSelect) {
      dom.environmentSelect.value = state.selectedEnvironment;
    }
  }
  renderRunMeta();
}

function applyRunProgress(run) {
  if (!run) {
    return;
  }

  state.selectedRunId = run.run_id || state.selectedRunId;
  if (run.contract_name && !state.selectedContract) {
    state.selectedContract = {
      name: run.contract_name,
      path: run.contract_name,
      size: '-',
      modified: '-'
    };
  }

  renderStatus(run.status, buildStatusMessage(run));
  renderTimeline(run);
  renderRunMeta(run);
  renderHistory();
  renderQuickSummary();
}

function handleSubmit() {
  const contract = state.selectedContract;
  if (!contract) {
    vscode.postMessage({ type: 'select-contract' });
    return;
  }

  const environment = dom.environmentSelect?.value || state.selectedEnvironment || 'simulation';
  const userStory = dom.userStoryInput?.value?.trim() || '';
  state.selectedEnvironment = environment;

  vscode.postMessage({
    type: 'submit-contract',
    environment,
    userStory,
    contractName: contract.name || 'UnknownContract',
    contractPath: contract.path || '',
  });

  renderStatus('submitting', `Submitting ${contract.name || 'contract'} to ${environment}...`);
}

function handleRerun() {
  handleSubmit();
}

function handleDownloadReport() {
  if (!state.selectedRunDetails && !state.snapshot?.latestRun) {
    showError('No run available to export.');
    return;
  }

  vscode.postMessage({
    type: 'download-report',
    runId: state.selectedRunId || state.snapshot?.latestRun?.run_id || '',
  });
}

function handleCopyTestCode() {
  const code = dom.runDetailsCode?.textContent || '';
  const placeholder = 'No generated test code available.';
  const textToCopy = code.trim() === placeholder ? '' : code;

  vscode.postMessage({
    type: 'copy-test-code',
    text: textToCopy,
  });

  setCopyButtonFeedback(dom.copyCodeBtn, textToCopy, 'Copy test code');
  setCopyButtonFeedback(dom.copyCodeInlineBtn, textToCopy, 'Copy');
}

function setCopyButtonFeedback(button, textToCopy, fallbackLabel) {
  if (!button) {
    return;
  }

  const original = button.textContent;
  button.textContent = textToCopy ? 'Copied' : 'No code';
  button.disabled = true;
  setTimeout(() => {
    button.textContent = original || fallbackLabel;
    button.disabled = false;
  }, 900);
}

function handleOpenContractFile() {
  const contract = state.selectedContract || state.snapshot?.contract;
  if (!contract?.path || contract.path === '-') {
    showError('Select a contract first.');
    return;
  }

  vscode.postMessage({
    type: 'open-contract-file',
    path: contract.path,
  });
}

function refreshHistory() {
  vscode.postMessage({ type: 'refresh-history' });
}

function renderContract() {
  const contract = state.selectedContract || state.snapshot?.contract;
  if (!contract) {
    dom.contractInfo.innerHTML = '<p class="placeholder">No contract selected. Open a .sol file or use Select contract.</p>';
    return;
  }

  dom.contractInfo.innerHTML = `
    <div class="data-row"><span>Name</span><strong>${escapeHtml(contract.name || 'UnknownContract')}</strong></div>
    <div class="data-row"><span>Path</span><strong>${escapeHtml(contract.path || '-')}</strong></div>
    <div class="data-row"><span>Size</span><strong>${escapeHtml(contract.size || '-')}</strong></div>
    <div class="data-row"><span>Modified</span><strong>${escapeHtml(contract.modified || '-')}</strong></div>
  `;
}

function renderStatus(status, message) {
  const normalized = normalizeStatus(status);
  dom.statusBadge.textContent = normalized;
  dom.statusBadge.className = `status-pill status-${normalized}`;
  dom.statusMessage.textContent = message || '';
}

function renderTimeline(run) {
  const steps = state.pipelineSteps;
  const status = normalizeStatus(run?.status);
  const currentNode = normalizeNode(run?.current_node || '');
  const timelineSteps = getTimelineSteps(steps, currentNode, status);

  const doneCount = timelineSteps.filter((step) => step.state === 'done').length;
  const activeCount = timelineSteps.filter((step) => step.state === 'active').length;
  const progress = status === 'done'
    ? 100
    : ((doneCount + (activeCount * 0.5)) / Math.max(1, timelineSteps.length)) * 100;

  dom.progressFill.style.width = `${progress}%`;
  dom.pipelineTimeline.innerHTML = timelineSteps.map((step) => {
    return `<div class="timeline-step timeline-${step.state}"><span>${escapeHtml(step.label)}</span></div>`;
  }).join('');
}

function getTimelineSteps(steps, currentNode, status) {
  const timeline = steps.map((step) => ({
    key: step.key,
    label: step.label,
    state: 'pending',
  }));

  if (status === 'done') {
    timeline.forEach((step) => { step.state = 'done'; });
    return timeline;
  }

  if (!currentNode) {
    return timeline;
  }

  const linearIndex = timeline.findIndex((step) => step.key === currentNode);
  if (linearIndex >= 0) {
    timeline.forEach((step, index) => {
      if (index < linearIndex) step.state = 'done';
      if (index === linearIndex) step.state = status === 'error' ? 'pending' : 'active';
    });
    return timeline;
  }

  // Corrector loop behavior: Generator is replaced by Corrector,
  // and next nodes return to pending until the new loop executes them.
  if (currentNode === 'corrector') {
    const designer = timeline.find((step) => step.key === 'test_designer');
    const generator = timeline.find((step) => step.key === 'generator_normal');
    const executor = timeline.find((step) => step.key === 'executor');
    const analyzer = timeline.find((step) => step.key === 'analyzer');
    const evaluator = timeline.find((step) => step.key === 'evaluator');

    if (designer) designer.state = 'done';
    if (generator) {
      generator.label = 'Corrector';
      generator.state = 'active';
    }
    if (executor) executor.state = 'pending';
    if (analyzer) analyzer.state = 'pending';
    if (evaluator) evaluator.state = 'pending';
  }

  return timeline;
}

function renderRunMeta(run = state.selectedRunDetails) {
  const selectedEnvironment = state.selectedEnvironment || 'simulation';
  const runId = run?.run_id || '-';
  const contractName = run?.contract_name || state.selectedContract?.name || '-';
  const status = displayStatusLabel(normalizeStatus(run?.status));
  const duration = formatDuration(run, { allowLatestFallback: false });

  dom.runMeta.innerHTML = `
    <div class="mini-chip">Run ID: <strong>${escapeHtml(runId)}</strong></div>
    <div class="mini-chip">Contract: <strong>${escapeHtml(contractName)}</strong></div>
    <div class="mini-chip">Status: <strong>${escapeHtml(status)}</strong></div>
    <div class="mini-chip">Environment: <strong>${escapeHtml(selectedEnvironment)}</strong></div>
    <div class="mini-chip">Duration: <strong>${escapeHtml(duration)}</strong></div>
  `;
}

function renderQuickSummary() {
  const run = state.selectedRunDetails;
  if (!run) {
    dom.quickSummary.innerHTML = '<p class="placeholder">Select a run to see details.</p>';
    dom.resultError.classList.add('hidden');
    return;
  }

  const summary = run.summary || {};
  const coverage = summary.coverage || {};
  const total = Number(summary.total || 0);
  const passed = Number(summary.passed || 0);
  const failed = Number(summary.failed || 0);
  const duration = formatDuration(run);

  dom.quickSummary.innerHTML = [
    card('Tests', `${passed}/${total}`, 'Success / total'),
    card('Failed', String(failed), 'Execution errors'),
    card('Coverage', `${Number(coverage.statements || 0).toFixed(1)}%`, 'Statements'),
    card('Duration', duration, 'Elapsed time'),
  ].join('');

  if (run.error) {
    dom.resultError.textContent = run.error;
    dom.resultError.classList.remove('hidden');
  } else {
    dom.resultError.classList.add('hidden');
  }
}

function renderHistory() {
  const runs = Array.isArray(state.snapshot?.history) ? [...state.snapshot.history] : [];
  const selectedStatus = normalizeFilterStatus(state.filters.status);

  const filtered = runs
    .filter((run) => {
      const contractName = String(run.contract_name || '').toLowerCase();
      const matchesQuery = !state.filters.query || contractName.includes(state.filters.query);
      const matchesStatus = selectedStatus === 'all' || normalizeStatus(run.status) === selectedStatus;
      return matchesQuery && matchesStatus;
    })
    .sort((a, b) => {
      const left = toTimestamp(a.started_at);
      const right = toTimestamp(b.started_at);
      return state.filters.sort === 'oldest' ? left - right : right - left;
    });

  if (!filtered.length) {
    dom.historyList.innerHTML = '<p class="placeholder">No runs match the current filters.</p>';
    return;
  }

  dom.historyList.innerHTML = filtered.map((run) => {
    const isSelected = run.run_id === state.selectedRunId;
    const status = normalizeStatus(run.status);
    return `
      <button class="history-item ${isSelected ? 'selected' : ''}" data-run-id="${escapeHtml(run.run_id)}" type="button">
        <div class="history-top">
          <strong>${escapeHtml(run.contract_name || 'UnknownContract')}</strong>
          <span class="status-pill status-${status}">${escapeHtml(displayStatusLabel(status))}</span>
        </div>
        <div class="history-meta">
          <span>${escapeHtml(run.run_id)}</span>
          <span>${escapeHtml(formatDate(run.started_at))}</span>
          <span>${escapeHtml(formatDuration(run))}</span>
        </div>
        ${run.error ? `<div class="history-error">${escapeHtml(run.error)}</div>` : ''}
      </button>
    `;
  }).join('');

  dom.historyList.querySelectorAll('[data-run-id]').forEach((item) => {
    item.addEventListener('click', () => {
      const runId = item.getAttribute('data-run-id');
      if (!runId) {
        return;
      }
      state.selectedRunId = runId;
      vscode.postMessage({ type: 'select-run', runId });
      renderHistory();
    });
  });
}

function renderSelectedRunDetails() {
  const run = state.selectedRunDetails;
  if (!run) {
    dom.runDetailsMeta.innerHTML = '<p class="placeholder">Select a run to inspect details.</p>';
    dom.runDetailsCode.textContent = '';
    dom.runDetailsLogs.textContent = '';
    dom.runDetailsError.classList.add('hidden');
    return;
  }

  const summary = run.summary || {};
  const coverage = summary.coverage || {};
  const testCode = run.test_code || run.testCode || '';
  const analyzer = run.analyzer_report || {};
  const testReport = run.test_report || {};
  const status = normalizeStatus(run.status);
  const detailCards = [
    card('Run ID', run.run_id || '-', 'Identifier'),
    card('Status', displayStatusLabel(status), 'Current state'),
    card('Contract', run.contract_name || '-', 'Target contract'),
    card('Duration', formatDuration(run), 'Execution time'),
    card('Coverage', `${Number(coverage.statements || 0).toFixed(1)}%`, 'Statements'),
  ];

  if (run.error) {
    detailCards.push(card('Error', run.error, 'Latest failure'));
  }

  dom.runDetailsMeta.innerHTML = detailCards.join('');

  dom.runDetailsCode.textContent = testCode || 'No generated test code available.';

  const logs = [];
  if (run.error) logs.push(`Error: ${run.error}`);
  if (summary.evaluation_reason) logs.push(`Evaluation: ${summary.evaluation_reason}`);
  if (analyzer.failures && analyzer.failures.length) logs.push(`Analyzer failures: ${analyzer.failures.length}`);
  if (testReport && Object.keys(testReport).length) logs.push(JSON.stringify(testReport, null, 2));
  dom.runDetailsLogs.textContent = logs.length ? logs.join('\n\n') : 'No logs available.';

  if (run.error) {
    dom.runDetailsError.textContent = run.error;
    dom.runDetailsError.classList.remove('hidden');
  } else {
    dom.runDetailsError.classList.add('hidden');
  }
}

function showError(message) {
  dom.statusBadge.textContent = 'error';
  dom.statusBadge.className = 'status-pill status-error';
  dom.statusMessage.textContent = message;
}

function focusSection(section) {
  const target = document.getElementById(`${section}Section`);
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function card(title, value, subtitle) {
  return `
    <div class="metric-card">
      <div class="metric-title">${escapeHtml(title)}</div>
      <div class="metric-value">${escapeHtml(value)}</div>
      <div class="metric-subtitle">${escapeHtml(subtitle)}</div>
    </div>
  `;
}

function buildStatusMessage(run) {
  const status = normalizeStatus(run.status);
  const currentNode = normalizeNode(run.current_node || '');
  const node = currentNode ? ` · ${currentNode}` : '';
  if (status === 'running') {
    return `Pipeline running${node}`;
  }
  if (status === 'done') {
    return `Pipeline completed${node}`;
  }
  return run.error || `Pipeline failed${node}`;
}

function normalizeStatus(status) {
  if (!status) return 'idle';
  if (status === 'completed') return 'done';
  if (status === 'failed') return 'error';
  if (status === 'pending') return 'running';
  return String(status).toLowerCase();
}

function normalizeFilterStatus(status) {
  if (status === 'completed') return 'done';
  if (status === 'failed') return 'error';
  return normalizeStatus(status);
}

function displayStatusLabel(status) {
  if (status === 'done') return 'completed';
  if (status === 'error') return 'failed';
  return status || 'idle';
}

function normalizeNode(node) {
  if (!node) return '';
  if (node === 'starting') return 'test_designer';
  if (node === 'increment') return 'corrector';
  if (node === 'generator_corrector') return 'corrector';
  if (node === 'finished') return 'evaluator';
  return String(node).toLowerCase();
}

function formatDuration(run, options = {}) {
  const allowLatestFallback = options.allowLatestFallback !== false;
  const resolvedRun = resolveRunForTiming(run, allowLatestFallback);
  if (!resolvedRun) return '-';

  const start = toTimestamp(resolvedRun.started_at);
  const end = resolvedRun.finished_at ? toTimestamp(resolvedRun.finished_at) : (resolvedRun.status === 'running' ? Date.now() : 0);
  if (!start || !end) return '-';
  const durationMs = Math.max(0, end - start);
  const seconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${remaining}s`;
  }
  return `${remaining}s`;
}

function resolveRunForTiming(run, allowLatestFallback = true) {
  if (!run) {
    return allowLatestFallback ? (state.snapshot?.latestRun || null) : null;
  }

  const hasTiming = Boolean(run.started_at);
  if (hasTiming) {
    return run;
  }

  const runId = run.run_id || state.selectedRunId;
  if (!runId) {
    return run;
  }

  const history = Array.isArray(state.snapshot?.history) ? state.snapshot.history : [];
  const historyRun = history.find((item) => item.run_id === runId);
  return historyRun || run;
}

function toTimestamp(value) {
  if (!value) return 0;
  const parsed = new Date(value).getTime();
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString('en-US');
}

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

