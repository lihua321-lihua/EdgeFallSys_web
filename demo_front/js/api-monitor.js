/**
 * API 监控台 - 时间范围切换
 */

function switchTimeRange(range, el) {
  document.querySelectorAll('.time-range-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  // 静态演示：模拟数据切换
  const dataMap = {
    'day': { tokens: '45,678', calls: '1,234', pct: '24.7' },
    'week': { tokens: '312,456', calls: '8,765', pct: '58.3' },
    'month': { tokens: '456,789', calls: '35,210', pct: '45.6' }
  };
  const d = dataMap[range];
  if (d) {
    document.querySelector('.token-table td:first-child').textContent = d.tokens;
  }
}