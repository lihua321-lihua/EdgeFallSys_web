<template>
  <div class="page-device-assets">
    <h2 class="page-title">设备资产管理</h2>

    <!-- 设备分类 Tab -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="手环" name="BRACELET" />
      <el-tab-pane label="网关" name="GATEWAY" />
      <el-tab-pane label="摄像头" name="CAMERA" />
    </el-tabs>

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索设备编号/MAC..."
        clearable
        style="max-width: 240px"
        @input="handleSearch"
      />
      <div class="toolbar-actions">
        <el-button type="success" :icon="Upload" @click="triggerImport" :loading="importing">批量导入</el-button>
        <el-button type="warning" :icon="Download" @click="handleExport" :loading="exporting">导出CSV</el-button>
        <input
          ref="fileInputRef"
          type="file"
          accept=".csv"
          style="display: none"
          @change="onFileSelected"
        />
      </div>
    </div>

    <!-- 设备表格 -->
    <el-table :data="filteredDevices" stripe border style="width: 100%" :row-class-name="rowClassName">
      <el-table-column prop="device_sn" label="设备编号" width="120" />
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          {{ typeLabel(row.type) }}
        </template>
      </el-table-column>
      <el-table-column prop="mac" label="MAC/编号" width="160" />
      <el-table-column prop="village_name" label="所属村庄" width="100" />
      <el-table-column label="绑定老人" width="100">
        <template #default="{ row }">
          {{ row.bind_elder || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="在线状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_online ? 'success' : 'danger'" size="small">
            {{ row.is_online ? '在线' : '离线' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="电量" width="100">
        <template #default="{ row }">
          <span v-if="row.battery_level != null">
            <el-progress :percentage="row.battery_level" :stroke-width="8" :color="batteryColor(row.battery_level)" style="width: 80px" />
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="signal" label="信号/运行" width="120" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openRebindDialog(row)">换绑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 换绑弹窗 -->
    <el-dialog v-model="rebindVisible" title="设备换绑" width="420px">
      <el-form label-position="top">
        <el-form-item label="设备编号">
          <el-input :model-value="rebindDevice?.device_sn" disabled />
        </el-form-item>
        <el-form-item label="当前绑定">
          <el-input :model-value="rebindDevice?.bind_elder || '未绑定'" disabled />
        </el-form-item>
        <el-form-item label="新绑定老人ID">
          <el-input v-model="rebindElderId" placeholder="输入老人ID，如 ELD_101" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rebindVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRebind" :loading="rebinding">确认换绑</el-button>
      </template>
    </el-dialog>

    <!-- 导入进度弹窗 -->
    <el-dialog v-model="importDialogVisible" title="批量导入设备" width="500px" :close-on-click-modal="false" :show-close="!importing">
      <div v-if="importing">
        <p style="margin-bottom: 12px">正在导入数据，请稍候...</p>
        <el-progress :percentage="importProgress" :status="importProgress === 100 ? 'success' : ''" />
        <p style="margin-top: 8px; font-size: 12px; color: var(--color-text-secondary)">
          已处理 {{ importProcessed }} / {{ importTotal }} 条
        </p>
      </div>
      <div v-else-if="importResult">
        <el-result :icon="importResult.failCount > 0 ? 'warning' : 'success'" :title="importResultTitle">
          <template #sub-title>
            <p>成功导入：<strong style="color: #67C23A">{{ importResult.successCount }}</strong> 条</p>
            <p v-if="importResult.failCount > 0">失败：<strong style="color: #F56C6C">{{ importResult.failCount }}</strong> 条</p>
            <div v-if="importResult.errors.length" style="margin-top: 12px; text-align: left; max-height: 200px; overflow-y: auto">
              <p v-for="(err, i) in importResult.errors" :key="i" style="font-size: 12px; color: #F56C6C">
                第 {{ err.row }} 行：{{ err.reason }}
              </p>
            </div>
          </template>
        </el-result>
      </div>
      <template #footer>
        <el-button v-if="importing" type="danger" @click="cancelImport">取消导入</el-button>
        <el-button v-else @click="importDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 导出进度 -->
    <el-dialog v-model="exportDialogVisible" title="导出CSV" width="400px" :close-on-click-modal="false" :show-close="!exporting">
      <div v-if="exporting">
        <p style="margin-bottom: 12px">正在生成CSV文件...</p>
        <el-progress :percentage="exportProgress" :status="exportProgress === 100 ? 'success' : ''" />
      </div>
      <div v-else>
        <el-result icon="success" title="导出完成" sub-title="文件已开始下载" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * 设备资产管理 - Tab切换、换绑弹窗、批量导入、导出CSV
 */
import { ref, computed, onMounted } from 'vue'
import { getDevices, rebindDevice as rebindDeviceApi } from '@/api/devices'
import { useAuthStore } from '@/store/useAuthStore'
import { ElMessage } from 'element-plus'
import { Upload, Download } from '@element-plus/icons-vue'

const authStore = useAuthStore()

const devices = ref([])
const activeTab = ref('all')
const keyword = ref('')
const rebindVisible = ref(false)
const rebindDevice = ref(null)
const rebindElderId = ref('')
const rebinding = ref(false)

// 导入相关状态
const fileInputRef = ref(null)
const importing = ref(false)
const importDialogVisible = ref(false)
const importProgress = ref(0)
const importProcessed = ref(0)
const importTotal = ref(0)
const importResult = ref(null)
let importCancelled = false

// 导出相关状态
const exporting = ref(false)
const exportDialogVisible = ref(false)
const exportProgress = ref(0)

const importResultTitle = computed(() => {
  if (!importResult.value) return ''
  const { successCount, failCount } = importResult.value
  if (failCount === 0) return `全部导入成功（${successCount} 条）`
  return `部分导入成功（${successCount} 成功，${failCount} 失败）`
})

const filteredDevices = computed(() => {
  let list = devices.value
  if (activeTab.value !== 'all') {
    list = list.filter(d => d.type === activeTab.value)
  }
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(d => d.device_sn.toLowerCase().includes(kw) || d.mac.toLowerCase().includes(kw))
  }
  return list
})

function typeLabel(type) {
  return { BRACELET: '手环', GATEWAY: '网关', CAMERA: '摄像头' }[type] || type
}

function batteryColor(level) {
  if (level < 20) return '#F56C6C'
  if (level < 50) return '#E6A23C'
  return '#67C23A'
}

function rowClassName({ row }) {
  if (!row.is_online) return 'row-danger'
  if (row.battery_level != null && row.battery_level < 20) return 'row-warning'
  return ''
}

function handleTabChange() {}

let searchTimer = null
function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {}, 300)
}

function openRebindDialog(device) {
  rebindDevice.value = device
  rebindElderId.value = ''
  rebindVisible.value = true
}

async function submitRebind() {
  if (!rebindElderId.value) {
    ElMessage.warning('请输入新绑定老人ID')
    return
  }
  rebinding.value = true
  try {
    await rebindDeviceApi({
      device_sn: rebindDevice.value.device_sn,
      elder_id: rebindElderId.value,
    })
    ElMessage.success('换绑成功')
    rebindDevice.value.bind_elder_id = rebindElderId.value
    rebindVisible.value = false
  } catch (e) {
    ElMessage.error('换绑失败，请重试')
  } finally {
    rebinding.value = false
  }
}

async function loadDevices() {
  try {
    const res = await getDevices()
    devices.value = res.items || []
  } catch (e) {
    console.error('加载设备列表失败', e)
  }
}

// ========== 批量导入 ==========

const REQUIRED_FIELDS = ['device_sn', 'type', 'mac']
const VALID_TYPES = ['BRACELET', 'GATEWAY', 'CAMERA']

function triggerImport() {
  if (!['admin', 'super_admin'].includes(authStore.role)) {
    ElMessage.error('仅管理员可执行批量导入')
    return
  }
  fileInputRef.value?.click()
}

function onFileSelected(e) {
  const file = e.target.files?.[0]
  if (!file) return
  // 重置 input 以便再次选择同一文件
  e.target.value = ''

  // 文件大小校验（2MB）
  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 2MB')
    return
  }
  // 文件类型校验
  if (!file.name.toLowerCase().endsWith('.csv')) {
    ElMessage.error('仅支持 CSV 格式文件')
    return
  }

  const reader = new FileReader()
  reader.onload = (evt) => {
    const text = evt.target.result
    processImport(text)
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  reader.readAsText(file, 'UTF-8')
}

function parseCSV(text) {
  const lines = text.split(/\r?\n/).filter(line => line.trim())
  if (lines.length < 2) return { headers: [], rows: [] }

  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = []
  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',').map(v => v.trim().replace(/^"|"$/g, ''))
    if (values.length === headers.length) {
      const row = {}
      headers.forEach((h, idx) => { row[h] = values[idx] })
      rows.push({ _row: i + 1, ...row })
    }
  }
  return { headers, rows }
}

function validateRow(row) {
  const errors = []
  for (const field of REQUIRED_FIELDS) {
    if (!row[field]) {
      errors.push(`必填字段 ${field} 为空`)
    }
  }
  if (row.type && !VALID_TYPES.includes(row.type)) {
    errors.push(`type 字段值无效，应为 ${VALID_TYPES.join('/')}`)
  }
  return errors
}

async function processImport(text) {
  const { headers, rows } = parseCSV(text)

  // 表头校验
  const missingFields = REQUIRED_FIELDS.filter(f => !headers.includes(f))
  if (missingFields.length) {
    ElMessage.error(`CSV 缺少必填列：${missingFields.join(', ')}`)
    return
  }

  importCancelled = false
  importing.value = true
  importDialogVisible.value = true
  importProgress.value = 0
  importProcessed.value = 0
  importTotal.value = rows.length
  importResult.value = null

  const result = { successCount: 0, failCount: 0, errors: [] }

  for (let i = 0; i < rows.length; i++) {
    if (importCancelled) {
      result.errors.push({ row: rows[i]._row, reason: '用户取消导入' })
      result.failCount += rows.length - i
      break
    }

    const rowErrors = validateRow(rows[i])
    if (rowErrors.length) {
      result.failCount++
      result.errors.push({ row: rows[i]._row, reason: rowErrors.join('；') })
    } else {
      // Mock 环境：模拟成功导入
      result.successCount++
      devices.value.push({
        device_sn: rows[i].device_sn,
        type: rows[i].type,
        mac: rows[i].mac,
        village_name: rows[i].village_name || '',
        bind_elder: rows[i].bind_elder || null,
        is_online: rows[i].is_online === 'true',
        battery_level: rows[i].battery_level ? Number(rows[i].battery_level) : null,
        signal: rows[i].signal || '-',
      })
    }

    importProcessed.value = i + 1
    importProgress.value = Math.round(((i + 1) / rows.length) * 100)

    // 让 UI 有机会更新
    if (i % 10 === 0) {
      await new Promise(r => setTimeout(r, 0))
    }
  }

  importResult.value = result
  importing.value = false
}

function cancelImport() {
  importCancelled = true
}

// ========== 导出 CSV ==========

async function handleExport() {
  if (!['admin', 'super_admin'].includes(authStore.role)) {
    ElMessage.error('仅管理员可执行导出操作')
    return
  }

  exporting.value = true
  exportDialogVisible.value = true
  exportProgress.value = 0

  const dataToExport = filteredDevices.value
  if (dataToExport.length === 0) {
    ElMessage.warning('当前无数据可导出')
    exporting.value = false
    exportDialogVisible.value = false
    return
  }

  const columns = [
    { key: 'device_sn', label: '设备编号' },
    { key: 'type', label: '类型' },
    { key: 'mac', label: 'MAC/编号' },
    { key: 'village_name', label: '所属村庄' },
    { key: 'bind_elder', label: '绑定老人' },
    { key: 'is_online', label: '在线状态' },
    { key: 'battery_level', label: '电量' },
    { key: 'signal', label: '信号/运行' },
  ]

  // UTF-8 BOM
  const BOM = '\uFEFF'
  const headerLine = columns.map(c => c.label).join(',')
  const rows = []

  for (let i = 0; i < dataToExport.length; i++) {
    const row = dataToExport[i]
    const line = columns.map(c => {
      let val = row[c.key]
      if (c.key === 'type') val = typeLabel(val) || val
      if (c.key === 'is_online') val = val ? '在线' : '离线'
      if (val == null) val = ''
      // 脱敏：MAC 地址部分隐藏
      if (c.key === 'mac' && typeof val === 'string' && val.length > 8) {
        val = val.substring(0, 4) + '****' + val.substring(val.length - 4)
      }
      // CSV 转义
      const str = String(val)
      return str.includes(',') || str.includes('"') || str.includes('\n')
        ? `"${str.replace(/"/g, '""')}"`
        : str
    }).join(',')
    rows.push(line)

    exportProgress.value = Math.round(((i + 1) / dataToExport.length) * 80)
    if (i % 50 === 0) {
      await new Promise(r => setTimeout(r, 0))
    }
  }

  const csvContent = BOM + headerLine + '\n' + rows.join('\n')
  exportProgress.value = 90

  // 流式下载
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const now = new Date()
  const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  link.href = url
  link.download = `设备列表_${dateStr}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  exportProgress.value = 100
  exporting.value = false
}

onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.page-device-assets {
  padding: 0;
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-md);
}

.toolbar {
  margin-bottom: var(--spacing-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

:deep(.row-danger) {
  background: var(--color-danger-bg) !important;
}

:deep(.row-warning) {
  background: var(--color-warning-bg) !important;
}
</style>
