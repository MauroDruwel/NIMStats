// ─── Overview Tab ─────────────────────────────────────────────────────────────
function renderOverview() {
  const { runs, modelNames, modelStats } = state;

  // KPIs
  const totalRuns = runs.length;
  const allUptimes = modelNames.map(m => modelStats[m].uptime);
  const avgSuccessRate = avg(allUptimes) * 100;

  let bestTimeModel = null, bestTimeVal = Infinity;
  let bestTpsModel = null, bestTpsVal = 0;
  for (const m of modelNames) {
    const s = modelStats[m];
    if (s.avgTime != null && s.avgTime < bestTimeVal) { bestTimeVal = s.avgTime; bestTimeModel = m; }
    if (s.avgTps != null && s.avgTps > bestTpsVal) { bestTpsVal = s.avgTps; bestTpsModel = m; }
  }
  const mostReliable = [...modelNames].sort((a, b) => modelStats[b].uptime - modelStats[a].uptime)[0];

  const kpiData = [
    { icon: '🔁', label: 'Total Runs', val: totalRuns, sub: `${runs[0]?.timestamp?.slice(0,10)} → ${runs[runs.length-1]?.timestamp?.slice(0,10)}`, decimals: 0 },
    { icon: '✅', label: 'Avg Success Rate', val: avgSuccessRate, suffix: '%', decimals: 1, sub: 'across all runs & models' },
    { icon: '⚡', label: 'Avg Best Response', val: bestTimeVal / 1000, suffix: 's', decimals: 2, sub: bestTimeModel ? shortModel(bestTimeModel) : '' },
    { icon: '🚀', label: 'Avg Best Throughput', val: bestTpsVal, suffix: ' t/s', decimals: 1, sub: bestTpsModel ? shortModel(bestTpsModel) : '' },
    { icon: '🏅', label: 'Most Reliable', val: (modelStats[mostReliable]?.uptime || 0) * 100, suffix: '%', decimals: 1, sub: mostReliable ? shortModel(mostReliable) : '' },
  ];

  const kpiGrid = document.getElementById('kpi-grid');
  kpiGrid.innerHTML = kpiData.map(k => `
    <div class="kpi-card">
      <div class="kpi-icon">${k.icon}</div>
      <div class="kpi-value" id="kpi-val-${k.label.replace(/\s/g,'_')}">0${k.suffix||''}</div>
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join('');

  kpiData.forEach(k => {
    const el = document.getElementById('kpi-val-' + k.label.replace(/\s/g,'_'));
    if (el) animateCounter(el, k.val, 1400, k.decimals || 0, k.suffix || '');
  });

  document.getElementById('overview-sub').textContent =
    `${totalRuns} benchmark runs · ${modelNames.length} models · ${runs[0]?.timestamp?.slice(0,10)} to ${runs[runs.length-1]?.timestamp?.slice(0,10)}`;

  // Charts
  const labels = runs.map(r => fmtTimestampShort(r.timestamp));
  const successCounts = runs.map(r => r.summary?.successCount ?? r.models.filter(m => m.success).length);
  const successRates = runs.map(r => {
    const total = r.summary?.totalModels || r.models.length;
    const succ = r.summary?.successCount ?? r.models.filter(m => m.success).length;
    return (succ / total) * 100;
  });

  destroyChart('successCount');
  state.charts.successCount = new Chart(document.getElementById('chart-success-count'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Successes',
        data: successCounts,
        borderColor: '#76b900',
        backgroundColor: 'rgba(118,185,0,0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
        title: (items) => `Run ${items[0].dataIndex + 1}: ${labels[items[0].dataIndex]}`
      }}},
      scales: {
        x: { display: false },
        y: { min: 0, max: 20, grid: {}, ticks: { stepSize: 5 } }
      }
    }
  });

  destroyChart('successRate');
  state.charts.successRate = new Chart(document.getElementById('chart-success-rate'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Success %',
        data: successRates,
        borderColor: '#00c8ff',
        backgroundColor: 'rgba(0,200,255,0.06)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
        label: (item) => `${item.raw.toFixed(1)}% success`
      }}},
      scales: {
        x: { display: false },
        y: { min: 0, max: 100, grid: {}, ticks: { callback: v => v + '%' } }
      }
    }
  });

  // Top 10 Fastest
  const modelsWithTime = modelNames
    .filter(m => modelStats[m].avgTime != null)
    .sort((a, b) => modelStats[a].avgTime - modelStats[b].avgTime)
    .slice(0, 10);

  destroyChart('fastest');
  state.charts.fastest = new Chart(document.getElementById('chart-fastest'), {
    type: 'bar',
    data: {
      labels: modelsWithTime.map(m => shortModel(m)),
      datasets: [{
        data: modelsWithTime.map(m => modelStats[m].avgTime / 1000),
        backgroundColor: modelsWithTime.map((m, i) => i === 0 ? '#76b900' : '#76b90055'),
        borderColor: modelsWithTime.map((m, i) => i === 0 ? '#76b900' : '#76b90088'),
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
        label: (item) => `Avg: ${item.raw.toFixed(2)}s`
      }}},
      scales: {
        x: { grid: {}, ticks: { callback: v => v + 's' } },
        y: { grid: { display: false }, ticks: { font: { size: 11 } } }
      }
    }
  });

  // Top 10 Throughput
  const modelsWithTps = modelNames
    .filter(m => modelStats[m].avgTps != null)
    .sort((a, b) => modelStats[b].avgTps - modelStats[a].avgTps)
    .slice(0, 10);

  destroyChart('throughput');
  state.charts.throughput = new Chart(document.getElementById('chart-throughput'), {
    type: 'bar',
    data: {
      labels: modelsWithTps.map(m => shortModel(m)),
      datasets: [{
        data: modelsWithTps.map(m => modelStats[m].avgTps),
        backgroundColor: modelsWithTps.map((m, i) => i === 0 ? '#00c8ff' : '#00c8ff44'),
        borderColor: modelsWithTps.map((m, i) => i === 0 ? '#00c8ff' : '#00c8ff88'),
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
        label: (item) => `${item.raw.toFixed(1)} tok/s`
      }}},
      scales: {
        x: { grid: {}, ticks: { callback: v => v + ' t/s' } },
        y: { grid: { display: false }, ticks: { font: { size: 11 } } }
      }
    }
  });

  // Reliability pills
  const grid = document.getElementById('reliability-grid');
  const sorted = [...modelNames].sort((a, b) => modelStats[b].uptime - modelStats[a].uptime);
  grid.innerHTML = sorted.map(m => {
    const u = modelStats[m].uptime;
    const cls = u >= 0.7 ? 'green' : u >= 0.4 ? 'yellow' : 'red';
    return `<div class="rel-pill ${cls}"><span class="dot"></span>${shortModel(m)} <span style="opacity:0.7">${(u*100).toFixed(0)}%</span></div>`;
  }).join('');
}

// ─── Leaderboard Tab ──────────────────────────────────────────────────────────
function renderLeaderboard() {
  const { modelNames, modelStats } = state;
  const scores = [...modelNames].sort((a, b) => modelStats[b].score - modelStats[a].score);
  const ranks = {};
  scores.forEach((m, i) => { ranks[m] = i + 1; });

  state.lbData = modelNames.map(m => ({ model: m, rank: ranks[m], ...modelStats[m] }));
  renderLbTable();
}

function renderLbTable() {
  const { lbData, lbSort, lbFilter } = state;
  if (!lbData) return;

  let rows = [...lbData];
  if (lbFilter) {
    rows = rows.filter(r => r.model.toLowerCase().includes(lbFilter.toLowerCase()));
  }

  rows.sort((a, b) => {
    let av = a[lbSort.col], bv = b[lbSort.col];
    if (av == null) av = lbSort.dir === 'asc' ? Infinity : -Infinity;
    if (bv == null) bv = lbSort.dir === 'asc' ? Infinity : -Infinity;
    return lbSort.dir === 'asc' ? av - bv : bv - av;
  });

  const tbody = document.getElementById('lb-body');
  tbody.innerHTML = rows.map((r, i) => {
    const uptimePct = (r.uptime * 100).toFixed(1);
    const colorVar = r.uptime >= 0.7 ? 'var(--success)' : r.uptime >= 0.4 ? 'var(--warning)' : 'var(--danger)';
    const scoreVar = r.score >= 60 ? 'var(--success)' : r.score >= 40 ? 'var(--warning)' : 'var(--danger)';
    const trendHtml = r.trend === 'up'
      ? `<span class="trend-indicator trend-up" title="Improving">↑</span>`
      : r.trend === 'down'
      ? `<span class="trend-indicator trend-down" title="Declining">↓</span>`
      : `<span class="trend-indicator trend-flat" title="Stable">→</span>`;
    const last10 = r.responseTimes.slice(-10);
    const spark = sparklineSVG(last10, 72, 22, modelColor(r.model));
    const isTop3 = r.rank <= 3;

    return `<tr data-model="${r.model}">
      <td><span class="rank-num${isTop3?' top3':''}">${r.rank}</span></td>
      <td><div class="model-name-cell">${providerChip(r.model, true)}<span class="model-name-text" title="${r.model}">${shortModel(r.model)}</span>${trendHtml}</div></td>
      <td><div class="score-cell"><span class="score-num" style="color:${scoreVar}">${r.score}</span></div></td>
      <td><div class="uptime-cell"><span class="uptime-val" style="color:${colorVar}">${uptimePct}%</span><div class="uptime-bar"><div class="uptime-fill" style="width:${uptimePct}%;background:${colorVar}"></div></div></div></td>
      <td class="mono" style="font-weight:600;color:var(--blue)">${r.intelligence ? r.intelligence.toFixed(0) : '—'}</td>
      <td class="mono">${r.avgTime ? (r.avgTime/1000).toFixed(2)+'s' : '—'}</td>
      <td class="mono">${r.bestTime ? (r.bestTime/1000).toFixed(2)+'s' : '—'}</td>
      <td class="mono">${r.avgTps ? r.avgTps.toFixed(1)+' t/s' : '—'}</td>
      <td class="mono text-accent">${r.wins}</td>
      <td>${spark}</td>
    </tr>`;
  }).join('');

  // Row click → explorer
  tbody.querySelectorAll('tr[data-model]').forEach(row => {
    row.addEventListener('click', () => {
      state.explorerModel = row.dataset.model;
      switchTab('explorer');
    });
  });
}

function initLeaderboardSort() {
  document.querySelectorAll('#lb-table thead th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (col === 'model' || col === 'trend') return;
      if (state.lbSort.col === col) {
        state.lbSort.dir = state.lbSort.dir === 'desc' ? 'asc' : 'desc';
      } else {
        state.lbSort.col = col;
        state.lbSort.dir = 'desc';
      }
      document.querySelectorAll('#lb-table thead th').forEach(t => t.classList.remove('sorted'));
      th.classList.add('sorted');
      th.querySelector('.sort-arrow').textContent = state.lbSort.dir === 'desc' ? '↓' : '↑';
      renderLbTable();
    });
  });

  document.getElementById('lb-search').addEventListener('input', e => {
    state.lbFilter = e.target.value;
    renderLbTable();
  });
}

// ─── Explorer Tab ─────────────────────────────────────────────────────────────
function renderExplorer() {
  const model = state.explorerModel;
  const s = state.modelStats[model];
  const pm = providerMeta(model);
  if (!s) return;

  // Update custom select trigger value
  populateExplorerSelect();

  // Header
  document.getElementById('explorer-header').innerHTML = `
    ${providerChip(model)}
    <h2>${shortModel(model)}</h2>
    <span style="font-size:12px;color:var(--text-dim);margin-left:auto">
      Last seen: ${s.lastSeen ? fmtTimestamp(s.lastSeen) : '—'}
    </span>
  `;

  // Stats
  const uptimeColor = s.uptime >= 0.7 ? 'var(--success)' : s.uptime >= 0.4 ? 'var(--warning)' : 'var(--danger)';
  document.getElementById('explorer-stats').innerHTML = `
    <div class="stat-card"><div class="stat-val" style="color:${uptimeColor}">${(s.uptime*100).toFixed(1)}%</div><div class="stat-label">Uptime</div><div class="stat-sub">${s.successCount}/${s.totalRuns} runs</div></div>
    <div class="stat-card"><div class="stat-val" style="color:var(--purple)">${s.intelligence ? s.intelligence.toFixed(0) : '—'}</div><div class="stat-label">Intel Index</div><div class="stat-sub">Artificial Analysis</div></div>
    <div class="stat-card"><div class="stat-val">${s.avgTime ? (s.avgTime/1000).toFixed(2)+'s' : '—'}</div><div class="stat-label">Avg Response</div></div>
    <div class="stat-card"><div class="stat-val text-accent">${s.bestTime ? (s.bestTime/1000).toFixed(2)+'s' : '—'}</div><div class="stat-label">Best Response</div></div>
    <div class="stat-card"><div class="stat-val" style="color:var(--blue)">${s.avgTps ? s.avgTps.toFixed(1)+' t/s' : '—'}</div><div class="stat-label">Avg Throughput</div></div>
  `;

  // Slicing to exclude runs prior to model existence (removes leading grey heatmap cells/empty charts)
  const firstActiveIdx = s.results.findIndex(r => r !== null);
  const activeResults = firstActiveIdx >= 0 ? s.results.slice(firstActiveIdx) : s.results;
  const activeRuns = firstActiveIdx >= 0 ? state.runs.slice(firstActiveIdx) : state.runs;
  const activeResponseTimes = firstActiveIdx >= 0 ? s.responseTimes.slice(firstActiveIdx) : s.responseTimes;

  // Response time chart
  const labels = activeRuns.map(r => fmtTimestampShort(r.timestamp));
  const timeData = activeResponseTimes.map(v => v != null ? v / 1000 : null);

  destroyChart('explorerTime');
  state.charts.explorerTime = new Chart(document.getElementById('chart-explorer-time'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Response Time (s)',
        data: timeData,
        borderColor: modelColor(model),
        backgroundColor: modelColor(model) + '14',
        fill: true,
        tension: 0.2,
        spanGaps: false,
        pointRadius: timeData.map(v => v != null ? 3 : 0),
        pointHoverRadius: 5,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
        label: (item) => item.raw != null ? `${item.raw.toFixed(2)}s` : 'Failed'
      }}},
      scales: {
        x: { display: false },
        y: { grid: {}, ticks: { callback: v => v + 's' } }
      }
    }
  });

  // Error breakdown
  destroyChart('explorerErrors');
  const errorCanvas = document.getElementById('chart-explorer-errors');
  const noErrors = document.getElementById('explorer-no-errors');
  const errorKeys = Object.keys(s.errors);
  if (errorKeys.length === 0) {
    errorCanvas.style.display = 'none';
    noErrors.style.display = 'block';
  } else {
    errorCanvas.style.display = 'block';
    noErrors.style.display = 'none';
    const errorColors = ['#ef4444','#f59e0b','#a855f7','#3b82f6','#06b6d4','#64748b'];
    state.charts.explorerErrors = new Chart(errorCanvas, {
      type: 'doughnut',
      data: {
        labels: errorKeys,
        datasets: [{
          data: errorKeys.map(k => s.errors[k]),
          backgroundColor: errorColors.slice(0, errorKeys.length).map(c => c + 'cc'),
          borderColor: errorColors.slice(0, errorKeys.length),
          borderWidth: 1,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 10, font: { size: 11 } } },
          tooltip: CHART_DEFAULTS.tooltip,
        }
      }
    });
  }

  // Heatmap — dynamic columns, sliced to skip runs before introduction
  const hm = document.getElementById('explorer-heatmap');
  const reversed = [...activeResults].reverse(); // newest first
  const hmCols = Math.ceil(Math.sqrt(reversed.length));
  hm.style.gridTemplateColumns = `repeat(${hmCols}, 1fr)`;
  hm.innerHTML = reversed.map((r, i) => {
    const runIdx = activeResults.length - 1 - i;
    const globalRunIdx = firstActiveIdx >= 0 ? firstActiveIdx + runIdx : runIdx;
    if (!r) return `<div class="heatmap-cell miss" title="Run ${globalRunIdx+1}: No data"></div>`;
    const ts = fmtTimestamp(activeRuns[runIdx]?.timestamp || '');
    if (r.success) return `<div class="heatmap-cell pass" title="${ts}: ✓ ${(r.responseTime/1000).toFixed(2)}s"></div>`;
    return `<div class="heatmap-cell fail" title="${ts}: ✗ ${r.error||'Error'}"></div>`;
  }).join('');

  // Run history table
  const tbody = document.getElementById('explorer-run-table');
  const last20 = activeResults.map((r, i) => ({ r, i })).slice(-20).reverse();
  tbody.innerHTML = last20.map(({ r, i }) => {
    if (!r) return `<tr><td class="mono text-dim">${fmtTimestamp(activeRuns[i]?.timestamp||'')}</td><td>—</td><td>—</td><td>—</td></tr>`;
    const tps = (r.success && r.responseTime > 0) ? (r.tokensGenerated / (r.responseTime / 1000)).toFixed(1) : null;
    return `<tr>
      <td class="mono" style="font-size:11px">${fmtTimestamp(activeRuns[i]?.timestamp||'')}</td>
      <td><span class="status-badge ${r.success?'ok':'fail'}">${r.success?'✓ OK':'✗ Fail'}</span></td>
      <td class="mono">${r.success ? (r.responseTime/1000).toFixed(2)+'s' : '—'}</td>
      <td class="mono">${tps ? tps+' t/s' : '—'}</td>
    </tr>`;
  }).join('');
}

// ─── Timeline Tab ─────────────────────────────────────────────────────────────
function renderTimeline() {
  const runs = state.rawRuns;
  const filter = state.timelineFilter;
  const now = new Date(runs[runs.length - 1]?.timestamp || Date.now());

  let filtered = [...runs].reverse(); // most recent first
  if (filter === '24h') {
    const cutoff = new Date(now); cutoff.setHours(cutoff.getHours() - 24);
    filtered = filtered.filter(r => new Date(r.timestamp) >= cutoff);
  } else if (filter === '48h') {
    const cutoff = new Date(now); cutoff.setHours(cutoff.getHours() - 48);
    filtered = filtered.filter(r => new Date(r.timestamp) >= cutoff);
  } else if (filter === '7d') {
    const cutoff = new Date(now); cutoff.setDate(cutoff.getDate() - 7);
    filtered = filtered.filter(r => new Date(r.timestamp) >= cutoff);
  }

  document.getElementById('timeline-badge').textContent = `${filtered.length} runs`;

  const container = document.getElementById('run-cards');
  container.innerHTML = filtered.map((run, idx) => {
    const total = run.summary?.totalModels || run.models.length;
    const succ = run.summary?.successCount ?? run.models.filter(m => m.success).length;
    const pct = succ / total;
    const badgeCls = pct >= 0.6 ? 'green' : pct >= 0.4 ? 'yellow' : 'red';
    const fastest = run.summary?.fastestModel ? shortModel(run.summary.fastestModel) : '—';
    const fastestTime = run.summary?.fastestTime ? (run.summary.fastestTime/1000).toFixed(2)+'s' : '';

    return `<div class="run-card" data-run-idx="${idx}">
      <div class="run-card-header">
        <span class="run-card-time">${fmtTimestamp(run.timestamp)}</span>
        <span class="run-success-badge ${badgeCls}">${succ}/${total}</span>
        <span class="run-fastest">⚡ <span>${fastest}</span>${fastestTime ? ' · '+fastestTime : ''}</span>
        <span class="run-expand-arrow">▼</span>
      </div>
      <div class="run-card-body">
        <div class="run-prompt">Prompt: ${escHtml((run.prompt||'').slice(0,120))}${(run.prompt||'').length > 120 ? '…' : ''}</div>
        <table class="run-detail-table">
          <thead><tr><th>Model</th><th>Status</th><th>Response Time</th><th>Tok/s</th><th>Error</th></tr></thead>
          <tbody>${run.models.map(m => {
            const tps = (m.success && m.responseTime > 0) ? (m.tokensGenerated / (m.responseTime / 1000)).toFixed(1) : null;
            const cls = m.success ? 'text-green' : 'text-red';
            return `<tr>
              <td>${providerChip(m.model, true)}<span style="font-size:12px">${shortModel(m.model)}</span></td>
              <td><span class="${cls}" style="font-size:12px;font-weight:600">${m.success ? '✓' : '✗'}</span></td>
              <td class="mono">${m.success && m.responseTime ? (m.responseTime/1000).toFixed(2)+'s' : '—'}</td>
              <td class="mono">${tps ? tps+' t/s' : '—'}</td>
              <td style="font-size:11px;color:var(--text-dim);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${m.error ? escHtml(m.error) : ''}</td>
            </tr>`;
          }).join('')}</tbody>
        </table>
      </div>
    </div>`;
  }).join('');

  container.querySelectorAll('.run-card').forEach(card => {
    card.querySelector('.run-card-header').addEventListener('click', () => {
      card.classList.toggle('expanded');
    });
  });
}

// ─── Compare Tab ──────────────────────────────────────────────────────────────
function renderCompare() {
  const modelA = state.compareModelA;
  const modelB = state.compareModelB;
  const sA = state.modelStats[modelA];
  const sB = state.modelStats[modelB];
  if (!sA || !sB) return;

  // Head-to-head wins (when both succeed)
  let winsA = 0, winsB = 0, bothSucceeded = 0;
  state.runs.forEach((run, i) => {
    const rA = sA.results[i];
    const rB = sB.results[i];
    if (rA && rA.success && rB && rB.success) {
      bothSucceeded++;
      if (rA.responseTime < rB.responseTime) winsA++;
      else winsB++;
    }
  });

  const metrics = [
    { label: 'Uptime', a: (sA.uptime*100).toFixed(1)+'%', b: (sB.uptime*100).toFixed(1)+'%', higherBetter: true, av: sA.uptime, bv: sB.uptime },
    { label: 'Intelligence Index', a: sA.intelligence ? sA.intelligence.toFixed(0) : '—', b: sB.intelligence ? sB.intelligence.toFixed(0) : '—', higherBetter: true, av: sA.intelligence, bv: sB.intelligence },
    { label: 'Avg Response Time', a: sA.avgTime ? (sA.avgTime/1000).toFixed(2)+'s' : '—', b: sB.avgTime ? (sB.avgTime/1000).toFixed(2)+'s' : '—', higherBetter: false, av: sA.avgTime, bv: sB.avgTime },
    { label: 'Best Response Time', a: sA.bestTime ? (sA.bestTime/1000).toFixed(2)+'s' : '—', b: sB.bestTime ? (sB.bestTime/1000).toFixed(2)+'s' : '—', higherBetter: false, av: sA.bestTime, bv: sB.bestTime },
    { label: 'Avg Throughput', a: sA.avgTps ? sA.avgTps.toFixed(1)+' t/s' : '—', b: sB.avgTps ? sB.avgTps.toFixed(1)+' t/s' : '—', higherBetter: true, av: sA.avgTps, bv: sB.avgTps },
    { label: 'Total Wins', a: sA.wins, b: sB.wins, higherBetter: true, av: sA.wins, bv: sB.wins },
    { label: 'Score', a: sA.score, b: sB.score, higherBetter: true, av: sA.score, bv: sB.score },
    { label: 'H2H Win Rate', a: bothSucceeded ? (winsA/bothSucceeded*100).toFixed(1)+'%' : '—', b: bothSucceeded ? (winsB/bothSucceeded*100).toFixed(1)+'%' : '—', higherBetter: true, av: winsA, bv: winsB },
  ];

  const colorA = modelColor(modelA);
  const colorB = modelColor(modelB);

  document.getElementById('h2h-table').innerHTML = `
    <thead><tr>
      <td class="h2h-val-a" style="color:${colorA};font-size:13px;padding:10px 16px;text-align:center">${providerChip(modelA, true)} ${shortModel(modelA)}</td>
      <td class="h2h-metric">Metric</td>
      <td class="h2h-val-b" style="color:${colorB};font-size:13px;padding:10px 16px;text-align:center">${providerChip(modelB, true)} ${shortModel(modelB)}</td>
    </tr></thead>
    <tbody>${metrics.map(m => {
      let clsA = 'h2h-val-a', clsB = 'h2h-val-b';
      if (m.av != null && m.bv != null) {
        const aWins = m.higherBetter ? m.av > m.bv : m.av < m.bv;
        const bWins = m.higherBetter ? m.bv > m.av : m.bv < m.av;
        if (aWins) clsA += ' winner';
        if (bWins) clsB += ' winner';
      }
      return `<tr class="h2h-row">
        <td class="${clsA}" style="padding:10px 16px">${m.a}</td>
        <td class="h2h-metric" style="padding:10px 16px">${m.label}</td>
        <td class="${clsB}" style="padding:10px 16px">${m.b}</td>
      </tr>`;
    }).join('')}</tbody>
  `;

  // Overlay chart
  const labels = state.runs.map(r => fmtTimestampShort(r.timestamp));
  destroyChart('compareTime');
  state.charts.compareTime = new Chart(document.getElementById('chart-compare-time'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: shortModel(modelA),
          data: sA.responseTimes.map(v => v != null ? v/1000 : null),
          borderColor: colorA,
          backgroundColor: colorA + '14',
          fill: false,
          tension: 0.2,
          spanGaps: false,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
        {
          label: shortModel(modelB),
          data: sB.responseTimes.map(v => v != null ? v/1000 : null),
          borderColor: colorB,
          backgroundColor: colorB + '14',
          fill: false,
          tension: 0.2,
          spanGaps: false,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, font: { size: 11 } } },
        tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
          label: (item) => item.raw != null ? `${item.dataset.label}: ${item.raw.toFixed(2)}s` : `${item.dataset.label}: Failed`
        }}
      },
      scales: {
        x: { display: false },
        y: { grid: {}, ticks: { callback: v => v + 's' } }
      }
    }
  });

  // Win timeline
  const winData = state.runs.map((run, i) => {
    const rA = sA.results[i], rB = sB.results[i];
    if (!rA?.success && !rB?.success) return null;
    if (rA?.success && !rB?.success) return 1;
    if (!rA?.success && rB?.success) return -1;
    return rA.responseTime < rB.responseTime ? 1 : -1;
  });

  const isLight = document.body.classList.contains('light-theme');
  const neutralColor = isLight ? '#dadce0' : '#202127';

  destroyChart('compareWins');
  state.charts.compareWins = new Chart(document.getElementById('chart-compare-wins'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Winner per run',
        data: winData,
        backgroundColor: winData.map(v => v == null ? neutralColor : v > 0 ? colorA + 'cc' : colorB + 'cc'),
        borderColor: winData.map(v => v == null ? neutralColor : v > 0 ? colorA : colorB),
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { ...CHART_DEFAULTS.tooltip, callbacks: {
          label: (item) => {
            if (item.raw == null) return 'Both failed';
            return item.raw > 0 ? `${shortModel(modelA)} won` : `${shortModel(modelB)} won`;
          }
        }}
      },
      scales: {
        x: { display: false },
        y: {
          min: -1.2,
          max: 1.2,
          grid: {
            color: isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.05)',
            lineWidth: 1,
            drawBorder: false
          },
          ticks: {
            stepSize: 1,
            callback: (value) => {
              if (value === 1) return shortModel(modelA);
              if (value === -1) return shortModel(modelB);
              return '';
            },
            font: {
              size: 10,
              weight: '600'
            }
          }
        }
      }
    }
  });
}
