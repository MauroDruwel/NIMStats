// ─── Constants ───────────────────────────────────────────────────────────────
const PROVIDER_META = {
  'deepseek-ai': { name: 'DeepSeek', color: '#4d9de0' },
  'z-ai':        { name: 'Z-AI',     color: '#11a883' },
  'minimaxai':   { name: 'MiniMax',  color: '#7c3aed' },
  'nvidia':      { name: 'NVIDIA',   color: '#76b900' },
  'moonshotai':  { name: 'Moonshot', color: '#0891b2' },
  'openai':      { name: 'OpenAI',   color: '#2563eb' },
  'google':      { name: 'Google',   color: '#ea4335' },
  'qwen':        { name: 'Qwen',     color: '#d97706' },
  'mistralai':   { name: 'Mistral',  color: '#7e22ce' },
  'meta':        { name: 'Meta',     color: '#1877f2' },
};

const MODEL_PALETTE = [
  '#76b900','#00c8ff','#ff6b35','#a855f7','#22c55e',
  '#f59e0b','#ec4899','#06b6d4','#84cc16','#6366f1',
  '#10b981','#3b82f6','#ef4444','#8b5cf6','#14b8a6',
  '#eab308','#d946ef','#fb923c','#e11d48','#64748b'
];

const CHART_DEFAULTS = {
  tooltip: {
    backgroundColor: '#1a1a2e',
    borderColor: '#2a2a40',
    borderWidth: 1,
    titleColor: '#e2e2f0',
    bodyColor: '#8888aa',
    padding: 12,
    cornerRadius: 8,
    displayColors: true
  }
};

Chart.defaults.color = '#9aa0a6';
Chart.defaults.borderColor = '#282a31';
Chart.defaults.font.family = "'Outfit', sans-serif";

// ─── State ────────────────────────────────────────────────────────────────────
const state = {
  db: null,
  rawRuns: [],
  runs: [],
  modelNames: [],
  modelStats: {},
  charts: {},
  currentTab: 'overview',
  explorerModel: '',
  compareModelA: '',
  compareModelB: '',
  lbSort: { col: 'score', dir: 'desc' },
  lbFilter: '',
  timelineFilter: 'all',
  limit: '50'
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
function avg(arr) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function fmtMs(ms) {
  if (ms == null) return '—';
  return (ms / 1000).toFixed(2) + 's';
}

function fmtTps(tps) {
  if (tps == null || tps <= 0) return '—';
  return tps.toFixed(1) + ' t/s';
}

function fmtPct(v) {
  return (v * 100).toFixed(1) + '%';
}

function shortModel(m) {
  return m.split('/')[1] || m;
}

function getProvider(m) {
  return m.split('/')[0];
}

function providerMeta(m) {
  const p = getProvider(m);
  return PROVIDER_META[p] || { name: p, color: '#666688' };
}

function providerChip(m, small) {
  const pm = providerMeta(m);
  const s = small ? 'font-size:10px;padding:1px 6px' : 'font-size:11px;padding:2px 8px';
  return `<span class="provider-chip" style="background:${pm.color}22;color:${pm.color};border:1px solid ${pm.color}44;${s}">${pm.name}</span>`;
}

function fmtTimestamp(ts) {
  const d = new Date(ts);
  return d.toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
}

function fmtTimestampShort(ts) {
  const d = new Date(ts);
  const mo = d.toLocaleString('en', { month: 'short' });
  const day = d.getDate();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${mo}${day} ${hh}:${mm}`;
}

function categorizeError(err) {
  if (!err) return 'Unknown';
  if (err.includes('timed out')) return 'Timeout';
  if (err.includes('JSON')) return 'JSON Error';
  if (err.includes('404')) return 'Not Found (404)';
  if (err.includes('410')) return 'Gone (410)';
  if (err.includes('closed connection')) return 'Connection Closed';
  return 'Other Error';
}

function modelColor(model) {
  const idx = state.modelNames.indexOf(model);
  return MODEL_PALETTE[idx % MODEL_PALETTE.length];
}

function sparklineSVG(values, width = 80, height = 24, color = '#76b900') {
  const valid = values.filter(v => v !== null);
  if (valid.length < 2) return `<svg width="${width}" height="${height}"></svg>`;
  const min = Math.min(...valid), max = Math.max(...valid);
  const range = max - min || 1;
  const pts = [];
  let lastX = 0, lastY = 0;
  values.forEach((v, i) => {
    if (v === null) return;
    const x = (i / (values.length - 1)) * width;
    const y = height - 2 - ((v - min) / range) * (height - 4);
    pts.push([x, y]);
    lastX = x; lastY = y;
  });
  if (pts.length < 2) return `<svg width="${width}" height="${height}"></svg>`;
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  return `<svg width="${width}" height="${height}" style="overflow:visible"><path d="${d}" stroke="${color}" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="2.5" fill="${color}"/></svg>`;
}

function destroyChart(key) {
  if (state.charts[key]) {
    state.charts[key].destroy();
    delete state.charts[key];
  }
}

function animateCounter(el, target, duration = 1200, decimals = 0, suffix = '') {
  const start = performance.now();
  const update = (now) => {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const ease = 1 - Math.pow(1 - progress, 3);
    const val = target * ease;
    el.textContent = (decimals ? val.toFixed(decimals) : Math.round(val)) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
