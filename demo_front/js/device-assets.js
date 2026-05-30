/**
 * 设备资产管理 - Tab切换 + 换绑弹窗
 */

// 设备分类 Tab 切换
function switchDeviceTab(type, el) {
  document.querySelectorAll('.device-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  // 静态演示
}

// 换绑弹窗
function openRebind(deviceId, deviceName, mac) {
  document.getElementById('rebindDeviceId').textContent = deviceId;
  document.getElementById('rebindOldMac').textContent = mac;
  document.getElementById('rebindModal').classList.add('active');
  document.getElementById('newMac').value = '';
}

function closeRebind() {
  document.getElementById('rebindModal').classList.remove('active');
}

function submitRebind() {
  const newMac = document.getElementById('newMac').value;
  if (!newMac.trim()) {
    alert('请输入新设备 MAC 地址');
    return;
  }
  closeRebind();
  alert('换绑成功！新 MAC: ' + newMac + '\n（静态演示，历史数据不会丢失）');
}

document.getElementById('rebindModal').addEventListener('click', function(e) {
  if (e.target === this) closeRebind();
});