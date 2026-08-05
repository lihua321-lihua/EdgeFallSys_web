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

        <!-- 密码重置申请（来自登录页"忘记密码"提交） -->
        <div v-if="resetRequests.length > 0" class="reset-requests">
          <div class="reset-title">密码重置申请（待处理 {{ resetRequests.length }} 条）</div>
          <el-table :data="resetRequests" stripe border size="small" style="width: 100%">
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="display_name" label="姓名" width="120" />
            <el-table-column prop="requested_at" label="申请时间" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="handleResetRequest(row)">重置为123456</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-table v-loading="loading" :data="filteredAccounts" stripe border style="width: 100%">
            <el-table-column prop="username" label="用户名" width="140">
              <template #default="{ row }">
                <strong>{{ row.username }}</strong>
              </template>
            </el-table-column>
            <el-table-column label="所属村" width="100">
              <template #default="{ row }">
                {{ row.village_name || '—' }}
              </template>
            </el-table-column>
            <el-table-column label="角色" width="140">
              <template #default="{ row }">
                <el-tag :type="roleTagType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'active' ? '正常' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
                <el-button
                  v-if="row.role !== 'super_admin'"
                  :type="row.status === 'active' ? 'danger' : 'success'"
                  link
                  size="small"
                  @click="toggleDisable(row)"
                >
                  {{ row.status === 'active' ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <!-- 编辑账号弹窗 -->
    <el-dialog v-model="editDialogVisible" :title="'编辑账号 - ' + editingUser?.username" width="420px">
      <el-form label-position="top">
        <el-form-item label="显示名称">
          <el-input v-model="editForm.display_name" placeholder="输入显示名称" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="村级网格员" value="village_grid" />
            <el-option label="村医" value="village_doctor" />
            <el-option label="管理员" value="admin" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属村">
          <el-select v-model="editForm.village_id" placeholder="选择村庄" style="width: 100%">
            <el-option label="桂花村" :value="1" />
            <el-option label="杨柳村" :value="2" />
            <el-option label="石门村" :value="3" />
            <el-option label="桃花村" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="修改密码（留空不修改）">
          <el-input v-model="editForm.password" type="password" placeholder="输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增账号弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增账号" width="420px">
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="newAccount.username" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="newAccount.password" type="password" placeholder="输入密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="newAccount.display_name" placeholder="输入显示名称" />
        </el-form-item>
        <el-form-item label="所属村">
          <el-select v-model="newAccount.village_id" placeholder="选择村庄" style="width: 100%">
            <el-option label="桂花村" :value="1" />
            <el-option label="杨柳村" :value="2" />
            <el-option label="石门村" :value="3" />
            <el-option label="桃花村" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newAccount.role" placeholder="选择角色" style="width: 100%">
            <el-option label="村级网格员" value="village_grid" />
            <el-option label="村医" value="village_doctor" />
            <el-option label="管理员" value="admin" />
            <el-option label="超级管理员" value="super_admin" />
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
 * 数据来源：后端 /api/v1/admin/accounts 接口
 */
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAccounts, createAccount, updateAccount, toggleAccountStatus, getResetRequests, resetPassword } from '@/api/accounts'

const loading = ref(false)
const selectedVillage = ref('全部')
const editDialogVisible = ref(false)
const addDialogVisible = ref(false)
const editingUser = ref(null)
const editForm = ref({ display_name: '', role: '', village_id: null, password: '' })
const newAccount = ref({ username: '', password: '', display_name: '', village_id: null, role: 'village_grid' })

const villages = ['桂花村', '杨柳村', '石门村', '桃花村']
const villageIdMap = { '桂花村': 1, '杨柳村': 2, '石门村': 3, '桃花村': 4 }

const treeData = ref([
  {
    label: '桂花镇',
    children: [
      { label: '全部' },
      ...villages.map(v => ({ label: v })),
      { label: '其他' },
    ],
  },
])

const accounts = ref([])
const resetRequests = ref([])

const filteredAccounts = computed(() => {
  if (selectedVillage.value === '全部') return accounts.value
  if (selectedVillage.value === '其他') {
    // 未分配村庄的账号（所属村显示为 "—"）
    return accounts.value.filter(a => !a.village_name)
  }
  return accounts.value.filter(a => a.village_name === selectedVillage.value)
})

function roleTagType(role) {
  return {
    'village_grid': 'info',
    'village_doctor': 'success',
    'admin': 'warning',
    'super_admin': 'danger',
  }[role] || 'info'
}

function roleLabel(role) {
  return {
    'village_grid': '村级网格员',
    'village_doctor': '村医',
    'admin': '管理员',
    'super_admin': '超级管理员',
  }[role] || role
}

function handleNodeClick(node) {
  if (!node.children) {
    selectedVillage.value = node.label
  }
}

async function fetchAccounts() {
  loading.value = true
  try {
    const res = await getAccounts()
    accounts.value = res.items || []
  } catch (e) {
    ElMessage.error('获取账号列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchResetRequests() {
  try {
    const res = await getResetRequests()
    resetRequests.value = res.items || []
  } catch (e) {
    // 静默失败，不影响账号列表展示
  }
}

async function handleResetRequest(row) {
  if (!row.account_id) {
    ElMessage.warning('该申请未关联有效账号，无法重置')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认将「${row.display_name || row.username}」的密码重置为初始密码 123456？`,
      '修改密码',
      { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  try {
    const res = await resetPassword(row.account_id)
    ElMessage.success(`已重置为初始密码：${res.new_password}，请告知用户登录后及时修改`)
    await fetchResetRequests()
  } catch (e) {
    ElMessage.error(e?.message || '重置失败')
  }
}

function openEditDialog(user) {
  editingUser.value = user
  editForm.value = {
    display_name: user.display_name,
    role: user.role,
    village_id: user.village_id,
    password: '',
  }
  editDialogVisible.value = true
}

async function saveEdit() {
  if (!editingUser.value) return
  try {
    const data = { ...editForm.value }
    if (!data.password) delete data.password
    await updateAccount(editingUser.value.id, data)
    ElMessage.success('账号已更新')
    editDialogVisible.value = false
    await fetchAccounts()
  } catch (e) {
    ElMessage.error(e?.detail || '更新失败')
  }
}

async function toggleDisable(user) {
  const newStatus = user.status === 'active' ? 'disabled' : 'active'
  try {
    await toggleAccountStatus(user.id, { status: newStatus })
    ElMessage.success(newStatus === 'disabled' ? '已禁用' : '已启用')
    await fetchAccounts()
  } catch (e) {
    ElMessage.error(e?.detail || '操作失败')
  }
}

function openAddDialog() {
  newAccount.value = {
    username: '',
    password: '',
    display_name: '',
    village_id: villageIdMap[selectedVillage.value] || null,
    role: 'village_grid',
  }
  addDialogVisible.value = true
}

async function addAccount() {
  const { username, password, display_name, role, village_id } = newAccount.value
  if (!username || !password || !display_name || !role) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await createAccount({ username, password, display_name, role, village_id })
    ElMessage.success('账号已创建')
    addDialogVisible.value = false
    await fetchAccounts()
  } catch (e) {
    ElMessage.error(e?.detail || '创建失败')
  }
}

onMounted(() => {
  fetchAccounts()
  fetchResetRequests()
})
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
.reset-requests {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.reset-title {
  font-size: 14px;
  font-weight: 600;
  color: #d48806;
  margin-bottom: 8px;
}
</style>
