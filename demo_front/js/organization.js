/**
 * 组织架构 - 树节点展开折叠 + 角色配置
 */

// 树节点展开/折叠
function toggleTree(nodeEl) {
  nodeEl.classList.toggle('expanded');
}

// 点击村级节点选中
function selectVillage(name, el) {
  document.querySelectorAll('.node-children .node-label').forEach(n => n.classList.remove('active'));
  el.classList.add('active');
}

// 角色配置弹窗
function openRoleConfig(username) {
  document.getElementById('roleUsername').textContent = username;
  document.getElementById('roleModal').classList.add('active');
}

function closeRoleModal() {
  document.getElementById('roleModal').classList.remove('active');
}

function saveRole() {
  const selected = document.querySelector('input[name="userRole"]:checked');
  if (!selected) {
    alert('请选择角色');
    return;
  }
  closeRoleModal();
  alert('角色已更新为：' + selected.value + '\n（静态演示）');
}

document.getElementById('roleModal').addEventListener('click', function(e) {
  if (e.target === this) closeRoleModal();
});