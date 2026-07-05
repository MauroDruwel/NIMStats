// ─── Custom Dropdown Logic ───────────────────────────────────────────────────
function createCustomDropdown(containerId, options, activeValue, onChangeCallback) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const trigger = container.querySelector('.custom-select-trigger');
  const triggerContent = trigger.querySelector('.trigger-content');
  const dropdown = container.querySelector('.custom-select-dropdown');
  const searchInput = dropdown.querySelector('.dropdown-search-input');
  const list = dropdown.querySelector('.dropdown-list');

  // Helper to set trigger content based on selection
  function updateTrigger(val) {
    if (!val) {
      triggerContent.innerHTML = 'Select a model...';
      return;
    }
    const pm = providerMeta(val);
    const short = shortModel(val);
    const score = state.modelStats[val]?.score || 0;
    const scoreColor = score >= 60 ? 'var(--success)' : score >= 40 ? 'var(--warning)' : 'var(--danger)';
    
    triggerContent.innerHTML = `
      ${providerChip(val, true)}
      <span style="font-weight:600;font-size:13px">${short}</span>
      <span style="font-size:10px;font-weight:700;background:var(--bg-card2);padding:1px 5px;border-radius:4px;color:${scoreColor};font-family:'JetBrains Mono'">Score: ${score}</span>
    `;
  }

  // Initial set
  updateTrigger(activeValue);

  // Toggle open
  trigger.onclick = (e) => {
    e.stopPropagation();
    // Close other dropdowns
    document.querySelectorAll('.custom-select-container').forEach(c => {
      if (c.id !== containerId) c.classList.remove('open');
    });
    container.classList.toggle('open');
    if (container.classList.contains('open')) {
      searchInput.value = '';
      renderList('');
      searchInput.focus();
    }
  };

  // Close when clicking outside
  window.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      container.classList.remove('open');
    }
  });

  // Search filter
  searchInput.oninput = (e) => {
    renderList(e.target.value);
  };
  searchInput.onclick = (e) => {
    e.stopPropagation(); // prevent closing dropdown
  };

  // Render items
  function renderList(filterText) {
    const term = filterText.toLowerCase();
    const filtered = options.filter(opt => {
      const short = shortModel(opt).toLowerCase();
      const prov = providerMeta(opt).name.toLowerCase();
      return short.includes(term) || prov.includes(term);
    });

    list.innerHTML = filtered.map(opt => {
      const s = state.modelStats[opt] || {};
      const short = shortModel(opt);
      const isSelected = opt === activeValue;
      const uptimePct = (s.uptime * 100).toFixed(0) + '%';
      const avgSpeed = s.avgTime ? (s.avgTime / 1000).toFixed(2) + 's' : '—';
      const scoreColor = s.score >= 60 ? 'var(--success)' : s.score >= 40 ? 'var(--warning)' : 'var(--danger)';
      const scoreBg = s.score >= 60 ? 'var(--success-dim)' : s.score >= 40 ? 'rgba(253,214,99,0.08)' : 'var(--danger-dim)';

      return `
        <li class="dropdown-item${isSelected ? ' selected' : ''}" data-value="${opt}">
          <div class="dropdown-item-left">
            <div class="dropdown-item-name">${short}</div>
            <div class="dropdown-item-details">
              ${providerChip(opt, true)}
              <span class="dropdown-item-stats">Up: ${uptimePct} | Speed: ${avgSpeed}</span>
            </div>
          </div>
          <span class="dropdown-item-score-badge" style="background:${scoreBg};color:${scoreColor}">Score: ${s.score || 0}</span>
        </li>
      `;
    }).join('');

    // Bind click events on items
    list.querySelectorAll('.dropdown-item').forEach(item => {
      item.onclick = (e) => {
        e.stopPropagation();
        const selectedVal = item.dataset.value;
        updateTrigger(selectedVal);
        container.classList.remove('open');
        onChangeCallback(selectedVal);
      };
    });
  }
}

// ─── Dropdown Populations ───────────────────────────────────────────────────
function populateExplorerSelect() {
  const sorted = [...state.modelNames].sort((a,b) => (state.modelStats[b]?.score || 0) - (state.modelStats[a]?.score || 0));
  createCustomDropdown('explorer-custom-select', sorted, state.explorerModel, (val) => {
    state.explorerModel = val;
    renderExplorer();
  });
}

function populateCompareSelects() {
  const sorted = [...state.modelNames].sort((a,b) => (state.modelStats[b]?.score || 0) - (state.modelStats[a]?.score || 0));
  
  createCustomDropdown('compare-a-custom-select', sorted, state.compareModelA, (val) => {
    state.compareModelA = val;
    renderCompare();
  });

  createCustomDropdown('compare-b-custom-select', sorted, state.compareModelB, (val) => {
    state.compareModelB = val;
    renderCompare();
  });

  const swapBtn = document.getElementById('swap-btn');
  if (swapBtn) {
    const newSwap = swapBtn.cloneNode(true);
    swapBtn.parentNode.replaceChild(newSwap, swapBtn);
    newSwap.addEventListener('click', () => {
      const tmp = state.compareModelA;
      state.compareModelA = state.compareModelB;
      state.compareModelB = tmp;
      populateCompareSelects();
      renderCompare();
    });
  }
}

// ─── Sliding Indicator Helpers ───────────────────────────────────────────────
function updateSlidingIndicator(btn) {
  const parent = btn.closest('.filter-btns');
  if (!parent) return;
  let indicator = parent.querySelector('.sliding-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.className = 'sliding-indicator';
    parent.appendChild(indicator);
  }
  indicator.style.left = btn.offsetLeft + 'px';
  indicator.style.width = btn.offsetWidth + 'px';
  indicator.style.height = btn.offsetHeight + 'px';
  indicator.style.top = btn.offsetTop + 'px';
}

function updateAllIndicators() {
  document.querySelectorAll('.filter-btns').forEach(container => {
    const activeBtn = container.querySelector('.filter-btn.active');
    if (activeBtn) {
      updateSlidingIndicator(activeBtn);
    }
  });
}

// ─── Tab Navigation ───────────────────────────────────────────────────────────
function switchTab(tabName) {
  state.currentTab = tabName;
  document.querySelectorAll('section[data-tab]').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`section[data-tab="${tabName}"]`)?.classList.add('active');
  document.querySelector(`.nav-tab[data-goto="${tabName}"]`)?.classList.add('active');

  if (tabName === 'overview') renderOverview();
  if (tabName === 'leaderboard') renderLeaderboard();
  if (tabName === 'explorer') renderExplorer();
  if (tabName === 'timeline') renderTimeline();
  if (tabName === 'compare') renderCompare();

  // Re-align sliding indicators after tab switches and renders complete
  setTimeout(updateAllIndicators, 50);
}

// ─── Initialization Helpers ──────────────────────────────────────────────────
function initTheme() {
  const toggleBtn = document.getElementById('theme-toggle');
  if (!toggleBtn) return;

  const savedTheme = localStorage.getItem('theme') || 'dark';
  if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
  }

  updateChartThemeColors();

  toggleBtn.addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    const newTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', newTheme);

    updateChartThemeColors();
    switchTab(state.currentTab);
  });
}

function initLimitFilters() {
  document.querySelectorAll('.filter-btn[data-limit]').forEach(btn => {
    if (btn.dataset.limit === state.limit) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }

    btn.addEventListener('click', () => {
      const newLimit = btn.dataset.limit;
      state.limit = newLimit;

      // Sync active state of buttons across all tabs
      document.querySelectorAll('.filter-btn[data-limit]').forEach(b => {
        if (b.dataset.limit === newLimit) {
          b.classList.add('active');
          updateSlidingIndicator(b);
        } else {
          b.classList.remove('active');
        }
      });

      recomputeStats();
      switchTab(state.currentTab);
    });
  });
}

// ─── Initialization ───────────────────────────────────────────────────────────
async function init() {
  try {
    initTheme();
    const SQL = await initSqlJs({
      locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
    });

    const res = await fetch('history.db');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = await res.arrayBuffer();
    state.db = new SQL.Database(new Uint8Array(buf));

    const data = loadFromDb(state.db);

    const processed = processData(data);
    state.rawRuns = processed.runs; // chronological (oldest first)
    state.modelNames = processed.modelNames;
    state.modelIntel = data.modelIntel || {};

    // Set initial limit and compute initial stats
    state.limit = '50';
    recomputeStats();

    // Default explorerModel
    if (!state.explorerModel || !state.modelNames.includes(state.explorerModel)) {
      state.explorerModel = state.modelNames[0] || '';
    }

    // Default compare models
    const sortedModels = [...state.modelNames].sort((a,b) => (state.modelStats[b]?.score || 0) - (state.modelStats[a]?.score || 0));
    const defaultA = 'qwen/qwen3-coder-480b-a35b-instruct';
    const defaultB = 'nvidia/nemotron-3-super-120b-a12b';
    state.compareModelA = state.modelNames.includes(defaultA) ? defaultA : (sortedModels[0] || '');
    state.compareModelB = state.modelNames.includes(defaultB) ? defaultB : (sortedModels[1] || sortedModels[0] || '');

    // Nav status
    document.getElementById('nav-status').textContent =
      `${state.rawRuns.length} runs · ${state.modelNames.length} models`;

    // Populate selects
    populateExplorerSelect();
    populateCompareSelects();

    // Init leaderboard sort
    initLeaderboardSort();

    // Limit filters
    initLimitFilters();

    // Timeline filters
    document.querySelectorAll('.filter-btn[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn[data-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        updateSlidingIndicator(btn);
        state.timelineFilter = btn.dataset.filter;
        renderTimeline();
      });
    });

    // Nav tabs
    document.querySelectorAll('.nav-tab[data-goto]').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.goto));
    });

    // Initial render
    renderOverview();

    // Show app
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').classList.add('visible');

    // Align sliding indicators once DOM is visible, and bind resize handlers
    setTimeout(updateAllIndicators, 100);
    window.addEventListener('resize', updateAllIndicators);

  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').classList.add('visible');
    document.getElementById('error-state').style.display = 'flex';
    document.getElementById('error-msg').textContent = `Error: ${err.message}. Make sure history.db exists and you're serving via HTTP.`;
    console.error('Failed to load data:', err);
  }
}

init();
