function updateChartThemeColors() {
  const isLight = document.body.classList.contains('light-theme');
  Chart.defaults.color = isLight ? '#5f6368' : '#9aa0a6';
  Chart.defaults.borderColor = isLight ? '#e8eaed' : '#282a31';
  CHART_DEFAULTS.tooltip.backgroundColor = isLight ? '#ffffff' : '#1f2026';
  CHART_DEFAULTS.tooltip.borderColor = isLight ? '#dadce0' : '#3c3d48';
  CHART_DEFAULTS.tooltip.titleColor = isLight ? '#202124' : '#f1f3f4';
  CHART_DEFAULTS.tooltip.bodyColor = isLight ? '#5f6368' : '#9aa0a6';
}
