/**
 * 走访任务清单 - 状态筛选 + 反馈弹窗交互
 */

// 筛选切换
function filterTasks(status, el) {
  // 更新 tab 激活状态
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');

  // 显示/隐藏卡片
  const cards = document.querySelectorAll('.task-card');
  cards.forEach(card => {
    if (status === 'all') {
      card.style.display = 'flex';
    } else if (status === 'pending') {
      card.style.display = card.classList.contains('completed') ? 'none' : 'flex';
    } else if (status === 'done') {
      card.style.display = card.classList.contains('completed') ? 'flex' : 'none';
    }
  });
}

// 反馈弹窗
let currentTaskCard = null;
function openFeedback(elderName, cardEl) {
  currentTaskCard = cardEl;
  document.getElementById('feedbackElderName').textContent = elderName;
  document.getElementById('feedbackModal').classList.add('active');
  document.getElementById('feedbackText').value = '';
}

function closeFeedback() {
  document.getElementById('feedbackModal').classList.remove('active');
}

function submitFeedback() {
  const text = document.getElementById('feedbackText').value;
  if (!text.trim()) {
    alert('请填写走访反馈内容');
    return;
  }
  // 静态演示：标记为已完成
  if (currentTaskCard) {
    currentTaskCard.classList.add('completed');
    // 更新状态标签
    const statusEl = currentTaskCard.querySelector('.task-status');
    if (statusEl) {
      statusEl.textContent = '已完成';
      statusEl.className = 'task-status tag tag-success';
    }
    // 更新按钮
    const btn = currentTaskCard.querySelector('.btn');
    if (btn) btn.textContent = '已反馈';
  }
  closeFeedback();
  alert('反馈已提交（静态演示）');
}

// 弹窗遮罩关闭
document.getElementById('feedbackModal').addEventListener('click', function(e) {
  if (e.target === this) closeFeedback();
});