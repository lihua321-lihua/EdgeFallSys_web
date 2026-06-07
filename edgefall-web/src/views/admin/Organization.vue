<template>
  <div class="page-organization">
    <h2 class="page-title">组织架构与账号管理</h2>

    <el-row :gutter="16">
      <!-- 左侧组织树 -->
      <el-col :xs="24" :sm="8" :md="6">
        <div class="org-tree">
          <div class="tree-title">组织架构</div>
          <div class="tree-body">
            <el-tree
              :data="treeData"
              :props="{ children: 'children', label: 'label' }"
              default-expand-all
              highlight-current
              @node-click="handleNodeClick"
            />
          </div>
        </div>
      </el-col>

      <!-- 右侧账号管理 -->
      <el-col :xs="24" :sm="16" :md="18">
        <div class="org-accounts">
          <div class="accounts-header">
            <h3>账号管理 - {{ selectedVillage }}</h3>
            <el-button type="primary" size="small" @click="openAddDialog">+ 新增账号</el-button>
          </div>

          <el-table :data="filteredAccounts" stripe border style="width: 100%">
            <el-table-column prop="username" label="用户名" width="140">
              <template #default="{ row }">
                <strong>{{ row.username }}</strong>
              </template>
            </el-table-column>
            <el-table-column prop="village" label="所属村" width="100" />
            <el-table-column label="角色" width="140">
              <template #default="{ row }">
                <el-tag :type="roleTagType(row.role)" size="small">{{ row.role }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_login" label="最后登录" width="160" />
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openRoleDialog(row)">编辑</el-button>
                <el-button v-if="row.role !== '超级管理员'" type="danger" link size="small" @click="toggleDisable(row)">
                  {{ row.disabled ? '启用' : '禁用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <!-- 角色配置弹窗 -->
    <el-dialog v-model="roleDialogVisible" :title="'角色配置 - ' + currentUser?.username" width="420px">
      <p style="margin-bottom: var(--spacing-md); color: var(--color-text-secondary);">请选择角色：</p>
      <el-radio-group v-model="selectedRole">
        <el-radio value="村级网格员">村级网格员</el-radio>
        <el-radio value="村医">村医</el-radio>
        <el-radio value="超级管理员">超级管理员</el-radio>
      </el-radio-group>
      <el-alert
        title="村级网格员：查看本村工单+走访任务 | 村医：仅查看健康档案 | 超级管理员：全盘数据"
        type="info"
        :closable="false"
        style="margin-top: var(--spacing-md);"
      />
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增账号弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增账号" width="420px">
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="newAccount.username" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="所属村">
          <el-select v-model="newAccount.village" placeholder="选择村庄" style="width: 100%">
            <el-option v-for="v in villages" :key="v" :label="v" :value="v" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newAccount.role" placeholder="选择角色" style="width: 100%">
            <el-option label="村级网格员" value="村级网格员" />
            <el-option label="村医" value="村医" />
            <el-option label="超级管理员" value="超级管理员" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addAccount">确认新增</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 组织架构 - 树节点展开折叠、角色配置、账号管理
 */
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const selectedVillage = ref('桂花村')
const roleDialogVisible = ref(false)
const addDialogVisible = ref(false)
const currentUser = ref(null)
const selectedRole = ref('')
const newAccount = ref({ username: '', village: '', role: '' })

const villages = ['桂花村', '杨柳村', '石门村', '桃花村']

const treeData = ref([
  {
    label: '桂花镇',
    children: villages.map(v => ({ label: v })),
  },
])

const accounts = ref([
  { username: 'zhang_grid', village: '桂花村', role: '村级网格员', last_login: '2026-05-25 14:30', disabled: false },
  { username: 'wang_grid', village: '桂花村', role: '村级网格员', last_login: '2026-05-25 09:15', disabled: false },
  { username: 'li_doctor', village: '桂花村', role: '村医', last_login: '2026-05-24 16:45', disabled: false },
  { username: 'admin_wang', village: '—', role: '超级管理员', last_login: '2026-05-25 15:00', disabled: false },
])

const filteredAccounts = computed(() => {
  if (selectedVillage.value === '全部') return accounts.value
  return accounts.value.filter(a => a.village === selectedVillage.value || a.village === '—')
})

function roleTagType(role) {
  return { '村级网格员': 'info', '村医': 'success', '超级管理员': 'warning' }[role] || 'info'
}

function handleNodeClick(node) {
  if (!node.children) {
    selectedVillage.value = node.label
  }
}

function openRoleDialog(user) {
  currentUser.value = user
  selectedRole.value = user.role
  roleDialogVisible.value = true
}

function saveRole() {
  if (currentUser.value) {
    currentUser.value.role = selectedRole.value
    ElMessage.success('角色已更新')
  }
  roleDialogVisible.value = false
}

function toggleDisable(user) {
  user.disabled = !user.disabled
  ElMessage.success(user.disabled ? '已禁用' : '已启用')
}

function openAddDialog() {
  newAccount.value = { username: '', village: selectedVillage.value, role: '村级网格员' }
  addDialogVisible.value = true
}

function addAccount() {
  if (!newAccount.value.username || !newAccount.value.village || !newAccount.value.role) {
    ElMessage.warning('请填写完整信息')
    return
  }
  accounts.value.push({
    ...newAccount.value,
    last_login: '-',
    disabled: false,
  })
  ElMessage.success('账号已创建')
  addDialogVisible.value = false
}
</script>

<style scoped>
.page-organization {
  padding: 0;
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-lg);
}

.org-tree {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.tree-title {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.tree-body {
  padding: var(--spacing-md);
}

.org-accounts {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: var(--spacing-lg);
}

.accounts-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.accounts-header h3 {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}
</style>
