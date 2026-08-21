// ─── i18n: 中英切换 (Chinese / English toggle) ───────────────────────────────
window.I18N_LANG = localStorage.getItem('lang') || 'en';

window.I18N = {
  zh: {
    // 导航 / Navigation
    'nav.overview': '概览',
    'nav.leaderboard': '排行榜',
    'nav.explorer': '模型详情',
    'nav.timeline': '时间线',
    'nav.compare': '对比',
    'theme.toggle': '切换主题',

    // 加载 / Loading
    'loading.text': '正在加载基准测试数据…',

    // 错误 / Error
    'error.title': '加载基准测试数据失败',
    'error.msg': '错误：{msg}。请确保 history.db 存在且通过 HTTP 方式访问本页面。',

    // 概览 / Overview
    'ov.title': '仪表盘概览',
    'ov.runs_limit': '运行次数：',
    'ov.limit.30': '30 次',
    'ov.limit.50': '50 次',
    'ov.limit.100': '100 次',
    'ov.limit.all': '全部',
    'card.model_intel': '模型智能指数',
    'card.value_frontier': '智能 vs. 吞吐（价值前沿）',
    'no_intel': '⚠️ 请提供 ARTIFICIAL_ANALYSIS_API_KEY 以加载基准分数',
    'no_scatter': '⚠️ 请提供 ARTIFICIAL_ANALYSIS_API_KEY 以加载价值前沿',
    'card.success_count': '每次运行成功数',
    'card.success_rate': '成功率趋势',
    'card.fastest': '最快模型 Top 10（平均）',
    'card.throughput': '最高吞吐 Top 10（tok/s）',
    'card.reliability': '模型可靠性',

    // 排行榜 / Leaderboard
    'lb.title': '模型排行榜',
    'lb.sub': '按综合评分排名 - 点击某行查看该模型详情',
    'lb.search_ph': '🔍 按模型名称筛选…',
    'th.rank': '#',
    'th.model': '模型',
    'th.score': '评分',
    'th.uptime': '在线率',
    'th.intelligence': '智能',
    'th.avgTime': '平均耗时',
    'th.avgTtft': '首字延迟',
    'th.bestTime': '最佳耗时',
    'th.avgTps': '吞吐',
    'th.wins': '胜场',
    'th.trend': '趋势',

    // 模型详情 / Explorer
    'ex.select_model': '选择模型',
    'ex.placeholder': '请选择模型…',
    'ex.search_ph': '🔍 搜索模型…',
    'ex.last_seen': '最近出现：{ts}',
    'card.radar': '模型能力拆解（雷达图）',
    'no_radar': '⚠️ 请提供 ARTIFICIAL_ANALYSIS_API_KEY 以查看能力雷达图',
    'card.compare_profile': '模型表现 vs. 全局平均',
    'no_comparison': '⚠️ 请提供 ARTIFICIAL_ANALYSIS_API_KEY 以查看对比数据',
    'card.resp_history': '响应时间历史',
    'card.error_breakdown': '错误分布',
    'no_errors': '🎉 100% 成功率 - 无错误！',
    'card.heatmap': '可用性热力图',
    'card.run_history': '运行历史（最近 20 次）',
    'th.timestamp': '时间',
    'th.status': '状态',
    'th.response_time': '响应时间',
    'th.tok_s': 'Tok/s',
    'th.error': '错误',

    // 时间线 / Timeline
    'tl.title': '运行时间线',
    'tl.filter.all': '全部',
    'tl.filter.24h': '最近 24 小时',
    'tl.filter.48h': '最近 48 小时',
    'tl.filter.7d': '最近 7 天',

    // 对比 / Compare
    'cmp.title': '模型对比',
    'cmp.sub': '一对一对比分析',
    'cmp.model_a': '模型 A',
    'cmp.model_b': '模型 B',
    'swap.title': '交换模型',
    'card.h2h': '一对一统计',
    'card.resp_overlay': '响应时间叠加',
    'card.win_timeline': '胜负时间线（每次运行）',

    // 错误分类 / Error categories
    'err.unknown': '未知',
    'err.timeout': '超时',
    'err.json': 'JSON 错误',
    'err.404': '未找到 (404)',
    'err.410': '已移除 (410)',
    'err.closed': '连接已关闭',
    'err.other': '其他错误',

    // 状态栏 / Nav status
    'nav.status': '{runs} 次运行 · {models} 个模型',

    // 下拉列表项 / Dropdown items
    'dropdown.stats': '在线率：{up} | 速度：{sp}',
    'dropdown.score': '评分：{score}',

    // KPI
    'kpi.total_runs': '总运行数',
    'kpi.avg_success': '平均成功率',
    'kpi.avg_best_resp': '平均最佳响应',
    'kpi.avg_best_tps': '平均最佳吞吐',
    'kpi.most_reliable': '最稳定',
    'kpi.sub_all': '覆盖全部运行与模型',
    'ov.sub': '{runs} 次基准运行 · {models} 个模型 · {from} 至 {to}',

    // 图表 / Charts
    'chart.success_count': '成功数',
    'chart.success_rate': '成功率',
    'chart.run_tooltip': '第 {n} 次运行: {label}',
    'chart.success_pct': '{v}% 成功率',
    'chart.avg': '平均：{v}s',
    'chart.tok_s': '{v} tok/s',
    'chart.intel_val': '智能：{v}',
    'chart.scatter': '{m}：速度 = {sp} t/s，智能 = {int}',
    'chart.axis_throughput': '吞吐量（tokens/秒）',
    'chart.axis_intel': '智能指数',
    'chart.resp_seconds': '响应时间 (秒)',
    'chart.failed': '失败',

    // 趋势 / Trend
    'trend.up': '上升',
    'trend.down': '下降',
    'trend.flat': '稳定',

    // 模型详情统计 / Explorer stats
    'stat.uptime': '在线率',
    'stat.intel': '智能指数',
    'stat.avg_resp': '平均响应',
    'stat.avg_ttft': '平均首字延迟',
    'stat.ttft_sub': '首字延迟',
    'stat.best_resp': '最佳响应',
    'stat.avg_tps': '平均吞吐',
    'stat.runs_sub': '{s}/{t} 次运行',

    // 雷达图 / Radar
    'radar.reliability': '可靠性 (%)',
    'radar.intelligence': '智能指数',
    'radar.avg_resp': '平均响应 (秒)',
    'radar.avg_tps': '平均吞吐 (t/s)',
    'radar.reasoning': '推理指数',
    'radar.coding': '代码指数',
    'radar.global': '全局平均',
    'radar.tooltip': '{label} {axis}: {v}',

    // 对比 tooltip
    'cmp.rel_tooltip': '{label} 可靠性：{v}% 在线率',
    'cmp.intel_tooltip': '{label} 智能：{v} 指数',
    'cmp.resp_tooltip': '{label} 平均响应：{v}s',
    'cmp.tps_tooltip': '{label} 平均吞吐：{v} t/s',

    // 热力图 / 运行历史 tooltip
    'hm.no_data': '第 {n} 次运行：无数据',
    'hm.ok': '{ts}: ✓ {t}s',
    'hm.fail': '{ts}: ✗ {err}',
    'run.ok': '✓ 正常',
    'run.fail': '✗ 失败',

    // 时间线卡片 / Timeline cards
    'tl.badge': '{n} 次运行',
    'tl.prompt': '提示词：{p}',
    'tl.th.model': '模型',
    'tl.th.status': '状态',
    'tl.th.resp': '响应时间',
    'tl.th.tok_s': 'Tok/s',
    'tl.th.error': '错误',

    // 对比指标表 / Compare metrics
    'm.uptime': '在线率',
    'm.intel': '智能指数',
    'm.avg_resp': '平均响应时间',
    'm.best_resp': '最佳响应时间',
    'm.avg_tps': '平均吞吐',
    'm.wins': '总胜场',
    'm.score': '评分',
    'm.h2h': '对战胜率',
    'h2h.metric': '指标',
    'cmp.overlay_fail': '{label}：失败',
    'cmp.win_per_run': '每轮胜者',
    'cmp.both_failed': '双方均失败',
    'cmp.won': '{m} 获胜'
  },

  en: {
    // 导航 / Navigation
    'nav.overview': 'Overview',
    'nav.leaderboard': 'Leaderboard',
    'nav.explorer': 'Explorer',
    'nav.timeline': 'Timeline',
    'nav.compare': 'Compare',
    'theme.toggle': 'Toggle Theme',

    // 加载 / Loading
    'loading.text': 'Loading benchmark data…',

    // 错误 / Error
    'error.title': 'Failed to load benchmark data',
    'error.msg': 'Error: {msg}. Make sure history.db exists and you\'re serving this page via HTTP.',

    // 概览 / Overview
    'ov.title': 'Dashboard Overview',
    'ov.runs_limit': 'Runs limit:',
    'ov.limit.30': '30 runs',
    'ov.limit.50': '50 runs',
    'ov.limit.100': '100 runs',
    'ov.limit.all': 'All',
    'card.model_intel': 'Model Intelligence Index',
    'card.value_frontier': 'Intelligence vs. Throughput (Value Frontier)',
    'no_intel': '⚠️ Supply ARTIFICIAL_ANALYSIS_API_KEY to load benchmark scores',
    'no_scatter': '⚠️ Supply ARTIFICIAL_ANALYSIS_API_KEY to load value frontier',
    'card.success_count': 'Success Count per Run',
    'card.success_rate': 'Success Rate Over Time',
    'card.fastest': 'Top 10 Fastest Models (Avg)',
    'card.throughput': 'Top 10 Throughput (tok/s)',
    'card.reliability': 'Model Reliability',

    // 排行榜 / Leaderboard
    'lb.title': 'Model Leaderboard',
    'lb.sub': 'Ranked by composite score - click a row to explore that model',
    'lb.search_ph': '🔍 Filter by model name…',
    'th.rank': '#',
    'th.model': 'Model',
    'th.score': 'Score',
    'th.uptime': 'Uptime',
    'th.intelligence': 'Intel',
    'th.avgTime': 'Avg Time',
    'th.avgTtft': 'TTFT',
    'th.bestTime': 'Best Time',
    'th.avgTps': 'Throughput',
    'th.wins': 'Wins',
    'th.trend': 'Trend',

    // 模型详情 / Explorer
    'ex.select_model': 'Select Model',
    'ex.placeholder': 'Select a model...',
    'ex.search_ph': '🔍 Search models...',
    'ex.last_seen': 'Last seen: {ts}',
    'card.radar': 'Model Capability Breakdown (Radar)',
    'no_radar': '⚠️ Supply ARTIFICIAL_ANALYSIS_API_KEY to view radar capabilities',
    'card.compare_profile': 'Model Performance vs. Global Average',
    'no_comparison': '⚠️ Supply ARTIFICIAL_ANALYSIS_API_KEY to view comparison stats',
    'card.resp_history': 'Response Time History',
    'card.error_breakdown': 'Error Breakdown',
    'no_errors': '🎉 100% Success Rate - No Errors!',
    'card.heatmap': 'Availability Heatmap',
    'card.run_history': 'Run History (last 20)',
    'th.timestamp': 'Timestamp',
    'th.status': 'Status',
    'th.response_time': 'Response Time',
    'th.tok_s': 'Tok/s',
    'th.error': 'Error',

    // 时间线 / Timeline
    'tl.title': 'Run Timeline',
    'tl.filter.all': 'All',
    'tl.filter.24h': 'Last 24h',
    'tl.filter.48h': 'Last 48h',
    'tl.filter.7d': 'Last 7d',

    // 对比 / Compare
    'cmp.title': 'Model Comparison',
    'cmp.sub': 'Head-to-head analysis',
    'cmp.model_a': 'Model A',
    'cmp.model_b': 'Model B',
    'swap.title': 'Swap models',
    'card.h2h': 'Head-to-Head Stats',
    'card.resp_overlay': 'Response Time Overlay',
    'card.win_timeline': 'Win Timeline (per run)',

    // 错误分类 / Error categories
    'err.unknown': 'Unknown',
    'err.timeout': 'Timeout',
    'err.json': 'JSON Error',
    'err.404': 'Not Found (404)',
    'err.410': 'Gone (410)',
    'err.closed': 'Connection Closed',
    'err.other': 'Other Error',

    // 状态栏 / Nav status
    'nav.status': '{runs} runs · {models} models',

    // 下拉列表项 / Dropdown items
    'dropdown.stats': 'Uptime: {up} | Speed: {sp}',
    'dropdown.score': 'Score: {score}',

    // KPI
    'kpi.total_runs': 'Total Runs',
    'kpi.avg_success': 'Avg Success Rate',
    'kpi.avg_best_resp': 'Avg Best Response',
    'kpi.avg_best_tps': 'Avg Best Throughput',
    'kpi.most_reliable': 'Most Reliable',
    'kpi.sub_all': 'across all runs & models',
    'ov.sub': '{runs} benchmark runs · {models} models · {from} to {to}',

    // 图表 / Charts
    'chart.success_count': 'Successes',
    'chart.success_rate': 'Success Rate',
    'chart.run_tooltip': 'Run {n}: {label}',
    'chart.success_pct': '{v}% success',
    'chart.avg': 'Avg: {v}s',
    'chart.tok_s': '{v} tok/s',
    'chart.intel_val': 'Intelligence: {v}',
    'chart.scatter': '{m}: Speed = {sp} t/s, Intel = {int}',
    'chart.axis_throughput': 'Throughput (tokens/sec)',
    'chart.axis_intel': 'Intelligence Index',
    'chart.resp_seconds': 'Response Time (s)',
    'chart.failed': 'Failed',

    // 趋势 / Trend
    'trend.up': 'Improving',
    'trend.down': 'Declining',
    'trend.flat': 'Stable',

    // 模型详情统计 / Explorer stats
    'stat.uptime': 'Uptime',
    'stat.intel': 'Intel Index',
    'stat.avg_resp': 'Avg Response',
    'stat.avg_ttft': 'Avg TTFT',
    'stat.ttft_sub': 'Time to 1st Token',
    'stat.best_resp': 'Best Response',
    'stat.avg_tps': 'Avg Throughput',
    'stat.runs_sub': '{s}/{t} runs',

    // 雷达图 / Radar
    'radar.reliability': 'Reliability (%)',
    'radar.intelligence': 'Intelligence Index',
    'radar.avg_resp': 'Avg Response (s)',
    'radar.avg_tps': 'Avg Throughput (t/s)',
    'radar.reasoning': 'Reasoning Index',
    'radar.coding': 'Coding Index',
    'radar.global': 'Global Average',
    'radar.tooltip': '{label} {axis}: {v}',

    // 对比 tooltip
    'cmp.rel_tooltip': '{label} Reliability: {v}% Uptime',
    'cmp.intel_tooltip': '{label} Intelligence: {v} Index',
    'cmp.resp_tooltip': '{label} Avg Response: {v}s',
    'cmp.tps_tooltip': '{label} Avg Throughput: {v} t/s',

    // 热力图 / 运行历史 tooltip
    'hm.no_data': 'Run {n}: No data',
    'hm.ok': '{ts}: ✓ {t}s',
    'hm.fail': '{ts}: ✗ {err}',
    'run.ok': '✓ OK',
    'run.fail': '✗ Fail',

    // 时间线卡片 / Timeline cards
    'tl.badge': '{n} runs',
    'tl.prompt': 'Prompt: {p}',
    'tl.th.model': 'Model',
    'tl.th.status': 'Status',
    'tl.th.resp': 'Response Time',
    'tl.th.tok_s': 'Tok/s',
    'tl.th.error': 'Error',

    // 对比指标表 / Compare metrics
    'm.uptime': 'Uptime',
    'm.intel': 'Intelligence Index',
    'm.avg_resp': 'Avg Response Time',
    'm.best_resp': 'Best Response Time',
    'm.avg_tps': 'Avg Throughput',
    'm.wins': 'Total Wins',
    'm.score': 'Score',
    'm.h2h': 'H2H Win Rate',
    'h2h.metric': 'Metric',
    'cmp.overlay_fail': '{label}: Failed',
    'cmp.win_per_run': 'Winner per run',
    'cmp.both_failed': 'Both failed',
    'cmp.won': '{m} won'
  }
};

// 语言元信息：新增一门语言 = 这里加一行 + I18N 里加一份字典，切换下拉会自动出现
window.LANG_META = {
  zh: { label: '中文', htmlLang: 'zh-CN', locale: 'zh-CN' },
  en: { label: 'EN',   htmlLang: 'en',    locale: 'en-US' },
};

// 翻译函数 / translation helper
window.t = function (key, vars) {
  const dict = window.I18N[window.I18N_LANG] || window.I18N.zh;
  let s = (dict[key] != null) ? dict[key] : (window.I18N.zh[key] != null ? window.I18N.zh[key] : key);
  if (vars && typeof vars === 'object') {
    for (const k in vars) {
      s = s.replace(new RegExp('\\{' + k + '\\}', 'g'), vars[k]);
    }
  }
  return s;
};

// 日期本地化 locale
window.getUiLocale = function () {
  const m = window.LANG_META[window.I18N_LANG];
  return m ? m.locale : 'en-US';
};

// 根据 I18N 中实际存在的语种自动生成切换下拉项；加新语言无需改这里
function populateLangSelect() {
  const sel = document.getElementById('lang-select');
  if (!sel) return;
  const cur = window.I18N_LANG;
  sel.innerHTML = '';
  Object.keys(window.I18N).forEach(code => {
    const meta = window.LANG_META[code] || { label: code };
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = meta.label;
    if (code === cur) opt.selected = true;
    sel.appendChild(opt);
  });
}

// 应用语言到所有静态标记元素
window.applyLang = function () {
  const lm = window.LANG_META[window.I18N_LANG];
  document.documentElement.lang = lm ? lm.htmlLang : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = window.t(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = window.t(el.getAttribute('data-i18n-title'));
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    el.placeholder = window.t(el.getAttribute('data-i18n-ph'));
  });
  populateLangSelect();
};

// 切换并重新渲染动态内容（图表/表格/下拉）
window.setLang = function (lang) {
  window.I18N_LANG = lang;
  try { localStorage.setItem('lang', lang); } catch (e) {}
  window.applyLang();
  if (typeof updateNavStatus === 'function') updateNavStatus();
  if (typeof switchTab === 'function' && typeof state !== 'undefined' && state) {
    // 关闭所有下拉，使其下次打开时以新语言渲染
    document.querySelectorAll('.custom-select-container.open').forEach(c => c.classList.remove('open'));
    switchTab(state.currentTab);
  }
};

window.toggleLang = function () {
  window.setLang(window.I18N_LANG === 'zh' ? 'en' : 'zh');
};
