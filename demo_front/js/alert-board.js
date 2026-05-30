/**
 * 紧急工单台 - 交互逻辑
 * 处理弹窗、当前时间刷新
 */

// 更新页面时间显示
function updateCurrentTime() {
  const el = document.getElementById('currentTime');
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  }
}
setInterval(updateCurrentTime, 30000);
updateCurrentTime();

// 处理弹窗 - 打开
let currentAlertCard = null;
function openProcessDialog(elderName, alertId) {
  currentAlertCard = document.getElementById(alertId);
  document.getElementById('processElderName').textContent = elderName;
  document.getElementById('processModal').classList.add('active');
  // 重置选项
  document.querySelector('input[name="processType"]').checked = false;
  document.getElementById('processNote').value = '';
}

// 处理弹窗 - 关闭
function closeProcessDialog() {
  document.getElementById('processModal').classList.remove('active');
}

// 处理弹窗 - 提交(静态演示)
function submitProcess() {
  const selected = document.querySelector('input[name="processType"]:checked');
  if (!selected) {
    alert('请选择处理类型');
    return;
  }
  // 静态演示：直接关闭弹窗并隐藏卡片
  if (currentAlertCard) {
    currentAlertCard.style.display = 'none';
  }
  closeProcessDialog();
  updateAlertCount();
}

// 更新工单计数
function updateAlertCount() {
  const visibleCards = document.querySelectorAll('.alert-card[style*="display: none"], .alert-card[style*="display:none"]');
  const total = document.querySelectorAll('.alert-card').length;
  const remaining = total - visibleCards.length;
  
  const badge = document.querySelector('.tab-badge');
  if (badge) {
    if (remaining === 0) {
      badge.style.display = 'none';
    } else {
      badge.style.display = 'inline-flex';
      badge.textContent = remaining;
    }
  }

  // 如果全部处理完，显示空状态
  if (remaining === 0) {
    document.getElementById('emptyState').style.display = 'flex';
  }
}

// 点击弹窗遮罩关闭
document.getElementById('processModal').addEventListener('click', function(e) {
  if (e.target === this) closeProcessDialog();
});