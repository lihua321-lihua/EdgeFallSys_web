<template>
  <div class="page-alert-board">
    <div class="page-title-row">
      <h2>紧急工单台</h2>
    </div>

    <!-- 工单汇总 -->
    <div class="alert-summary">
      <span class="summary-item summary-danger">跌倒报警：{{ fallCount }} 条</span>
      <span class="summary-item summary-warning">高危预警：{{ highCount }} 条</span>
    </div>

    <!-- 告警列表 -->
    <div v-if="alerts.length" class="alert-list">
      <div
        v-for="alert in alerts"
        :key="alert.event_id"
        :class="['alert-card', alert.level === 'CRITICAL' ? 'card-danger' : 'card-warning']"
      >
        <div class="alert-badge">
          <span class="badge-icon">{{ alert.level === 'CRITICAL' ? '⚠' : '⚡' }}</span>
        </div>
        <div class="alert-info">
          <div class="info-row">
            <span class="elder-name">{{ alert.elder_name }}</span>
            <span :class="['alert-type', alert.level === 'CRITICAL' ? 'type-danger' : 'type-warning']">
              {{ typeLabel(alert.type) }}
            </span>
          </div>
          <div class="info-sub">
            <span>发生位置：<span class="location">{{ alert.payload?.location }}</span></span>
            <span>事件编号：{{ alert.event_id }}</span>
          </div>
        </div>
        <div class="alert-time">{{ formatTime(alert.create_time) }}</div>
        <div class="alert-action">
          <el-button
            v-if="alert.type === 'FALL_DETECTED'"
            type="primary"
            size="large"
            plain
            style="margin-bottom: 8px"
            @click="openRescueBriefing(alert)"
          >
            🚑 救援简报
          </el-button>
          <el-button
            :type="alert.level === 'CRITICAL' ? 'danger' : 'warning'"
            size="large"
            @click="openProcessDialog(alert)"
          >
            {{ isGridWorker ? '现场处置' : isDoctor ? '医疗判断' : '接单处理' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <EmptyState v-else icon="☕" text="暂无待处理工单" />
  </div>

  <!-- 处理弹窗 - P0 按角色分化 -->
  <el-dialog
    v-model="dialogVisible"
    :title="dialogTitle"
    width="480px"
    :close-on-click-modal="false"
  >
    <!-- 网格员：现场处置 -->
    <template v-if="isGridWorker">
      <p class="process-tip">请选择现场处置方式：</p>
      <el-radio-group v-model="processType" class="process-options">
        <el-radio value="VISITED" border>已上门</el-radio>
        <el-radio value="CALLED_FAMILY" border>已联系家属</el-radio>
        <el-radio value="FALSE_ALARM" border>误报</el-radio>
      </el-radio-group>
      <el-input
        v-model="remark"
        type="textarea"
        placeholder="现场情况备注（可选）"
        :rows="3"
        style="margin-top: 16px"
      />
    </template>

    <!-- 村医：医疗判断 -->
    <template v-else-if="isDoctor">
      <p class="process-tip">请填写医疗判断：</p>
      <el-input
        v-model="medicalJudgment"
        type="textarea"
        placeholder="医疗判断（必填）：如生命体征评估、是否需送医、用药建议等"
        :rows="4"
        style="margin-top: 8px"
      />
      <div style="margin-top: 12px">
        <el-checkbox v-model="needTransfer">需要送医转诊</el-checkbox>
      </div>
    </template>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitProcess" :loading="submitting">确认提交</el-button>
    </template>
  </el-dialog>

  <!-- AI 救援简报弹窗 - 跌倒事件 9 模块结构化简报 -->
  <el-dialog
    v-model="rescueDialogVisible"
    title="🚑 AI 智能救援简报"
    width="720px"
    :close-on-click-modal="false"
  >
    <div v-if="rescueLoading" class="rescue-loading">
      <el-icon class="is-loading" style="font-size: 24px"><Loading /></el-icon>
      <span style="margin-left: 8px">正在生成救援简报，请稍候...</span>
    </div>
    <template v-else-if="rescueReport">
      <div class="rescue-meta">
        <el-tag :type="rescueReport.source === 'qwen' ? 'success' : 'info'" size="small">
          {{ rescueReport.source === 'qwen' ? 'AI 大模型生成' : '本地模板兜底' }}
        </el-tag>
        <span class="rescue-time">生成时间：{{ rescueReport.created_at }}</span>
        <el-button-group style="margin-left: auto">
          <el-button size="small" @click="downloadRescue('json')">下载 JSON</el-button>
          <el-button size="small" @click="downloadRescue('txt')">下载 TXT</el-button>
        </el-button-group>
      </div>
      <el-collapse v-model="rescueActiveKeys" class="rescue-collapse">
        <el-collapse-item
          v-for="(item, idx) in rescueModules"
          :key="item.key"
          :name="item.key"
          :title="`${idx + 1}. ${item.title}`"
        >
          <p class="rescue-content">{{ rescueReport.report[item.key] || '（无）' }}</p>
        </el-collapse-item>
      </el-collapse>
    </template>
    <EmptyState v-else icon="📋" text="暂无救援简报" />
    <template #footer>
      <el-button @click="rescueDialogVisible = false">关闭</el-button>
      <el-button type="primary" @click="regenerateRescue" :loading="rescueLoading">重新生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 紧急工单台 - 告警列表、WebSocket实时推送、工单处理弹窗
 * P0 修正：按角色分化处理操作
 *   - 网格员（village_grid）：现场处置（VISITED/CALLED_FAMILY/FALSE_ALARM）+ 备注
 *   - 村医（village_doctor）：医疗判断（MEDICAL_JUDGE）+ 是否送医
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getAlerts, resolveAlert } from '@/api/alerts'
import { generateRescueBriefing, getAiReports, getAiReport, downloadAiReport } from '@/api/ai'
import { useAlertStore } from '@/store/useAlertStore'
import { useAuthStore } from '@/store/useAuthStore'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import EmptyState from '@/components/EmptyState.vue'

const alertStore = useAlertStore()
const authStore = useAuthStore()

const alerts = ref([])
const dialogVisible = ref(false)
const currentAlert = ref(null)
const processType = ref('VISITED')
const remark = ref('')
const submitting = ref(false)

// P0: 村医医疗判断专用字段
const medicalJudgment = ref('')
const needTransfer = ref(false)

// AI 救援简报（跌倒事件 9 模块）
const rescueDialogVisible = ref(false)
const rescueLoading = ref(false)
const rescueReport = ref(null)
const rescueActiveAlert = ref(null)
const rescueActiveKeys = ref([])
const rescueModules = [
  { key: 'event_overview', title: '事件概述' },
  { key: 'injury_assessment', title: '伤势评估' },
  { key: 'vital_signs_reading', title: '生命体征解读' },
  { key: 'first_aid_by_group', title: '分人群现场急救方案' },
  { key: 'medication_risk', title: '用药风险提醒' },
  { key: 'transfer_precautions', title: '就医转运注意事项' },
  { key: 'contact_priority', title: '联系人通知排序' },
  { key: 'observation_72h', title: '72小时观察重点' },
  { key: 'home_fall_prevention', title: '居家环境防跌倒优化建议' },
]

// P0: 角色判断
const isGridWorker = computed(() => authStore.role === 'village_grid')
const isDoctor = computed(() => authStore.role === 'village_doctor')

const dialogTitle = computed(() => {
  const roleTag = isGridWorker.value ? '现场处置' : isDoctor.value ? '医疗判断' : '工单处理'
  return `${roleTag} - ${currentAlert.value?.elder_name || ''}`
})

const fallCount = computed(() => alerts.value.filter(a => a.type === 'FALL_DETECTED').length)
const highCount = computed(() => alerts.value.filter(a => a.level === 'HIGH').length)

// 监听 alertStore 新告警，实时插入列表头部
const stopWatch = watch(
  () => alertStore.currentAlert,
  (newAlert) => {
    if (!newAlert) return
    const exists = alerts.value.find(a => a.event_id === newAlert.event_id)
    if (!exists) {
      alerts.value.unshift(newAlert)
      alertStore.setPendingCount(alerts.value.length)
    }
  }
)

function typeLabel(type) {
  const map = { FALL_DETECTED: '跌倒报警', SCAM_ALERT: '诈骗预警', INTRUSION_ALERT: '入侵预警' }
  return map[type] || '异常告警'
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function loadAlerts() {
  try {
    const res = await getAlerts({ status: 'pending' })
    alerts.value = res || []
    alertStore.setPendingCount(alerts.value.length)
  } catch (e) {
    console.error('加载告警失败', e)
  }
}

function openProcessDialog(alert) {
  currentAlert.value = alert
  // P0: 按角色重置表单
  processType.value = 'VISITED'
  remark.value = ''
  medicalJudgment.value = ''
  needTransfer.value = false
  dialogVisible.value = true
}

async function submitProcess() {
  if (!currentAlert.value) return
  submitting.value = true
  try {
    const payload = { handler_name: '当前用户' }

    if (isGridWorker.value) {
      // 网格员：现场处置
      payload.action_type = processType.value
      payload.remark = remark.value
    } else if (isDoctor.value) {
      // 村医：医疗判断
      if (!medicalJudgment.value.trim()) {
        ElMessage.warning('医疗判断不能为空')
        submitting.value = false
        return
      }
      payload.action_type = 'MEDICAL_JUDGE'
      payload.medical_judgment = medicalJudgment.value
      payload.need_transfer = needTransfer.value
    }

    await resolveAlert(currentAlert.value.event_id, payload)
    ElMessage.success('工单处理成功')
    alerts.value = alerts.value.filter(a => a.event_id !== currentAlert.value.event_id)
    alertStore.setPendingCount(alerts.value.length)
    dialogVisible.value = false
  } catch (e) {
    // 错误明细（如"工单已处理，不可重复操作"、角色越权 403）由 request.js 拦截器统一提示
  } finally {
    submitting.value = false
  }
}

// ============ AI 救援简报 ============
async function openRescueBriefing(alert) {
  rescueActiveAlert.value = alert
  rescueDialogVisible.value = true
  rescueReport.value = null
  rescueActiveKeys.value = ['event_overview', 'injury_assessment']
  // 先查该告警是否已有救援简报（按 event_id 关联）
  try {
    const list = await getAiReports({ elder_id: alert.elder_id, report_type: 'rescue_briefing', limit: 20 })
    const existing = (list?.items || []).find(r => r.event_id === alert.event_id)
    if (existing) {
      await loadRescueReport(existing.report_id)
      return
    }
  } catch (e) {
    // 查询失败不阻断，继续生成
  }
  await generateRescue()
}

async function generateRescue() {
  const alert = rescueActiveAlert.value
  if (!alert) return
  rescueLoading.value = true
  try {
    const data = await generateRescueBriefing({
      elder_id: alert.elder_id,
      event_id: alert.event_id,
      confidence: 0.9,  // 前端触发默认达标，后端断网/未配置自动走兜底
      fall_data: {
        fall_location: alert.payload?.location || '',
        fall_time: formatTime(alert.create_time),
      },
    })
    rescueReport.value = data
  } catch (e) {
    ElMessage.error('救援简报生成失败')
  } finally {
    rescueLoading.value = false
  }
}

async function regenerateRescue() {
  rescueReport.value = null
  await generateRescue()
}

async function loadRescueReport(reportId) {
  rescueLoading.value = true
  try {
    const data = await getAiReport(reportId)
    rescueReport.value = data
  } catch (e) {
    ElMessage.error('加载救援简报失败')
  } finally {
    rescueLoading.value = false
  }
}

async function downloadRescue(format) {
  if (!rescueReport.value?.report_id) return
  try {
    await downloadAiReport(rescueReport.value.report_id, format)
    ElMessage.success(`已下载 ${format.toUpperCase()} 文件`)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

onMounted(() => {
  loadAlerts()
})

onUnmounted(() => {
  stopWatch()
})
</script>

<style scoped>
.page-alert-board {
  padding: 0;
}

.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.page-title-row h2 {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

/* 汇总 */
.alert-summary {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.alert-summary .summary-item {
  padding: var(--spacing-sm) var(--spacing-lg);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  font-weight: 500;
}

.alert-summary .summary-danger {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.alert-summary .summary-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

/* 告警列表 */
.alert-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.alert-card {
  display: flex;
  align-items: center;
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-md) var(--spacing-lg);
  box-shadow: var(--shadow-card);
  border-left: 4px solid var(--color-border);
  transition: transform 0.15s, box-shadow 0.15s;
  gap: var(--spacing-md);
}

.alert-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.alert-card.card-danger {
  border-left-color: var(--color-danger);
  background: linear-gradient(90deg, var(--color-danger-bg) 0%, #fff 8%);
}

.alert-card.card-warning {
  border-left-color: var(--color-warning);
  background: linear-gradient(90deg, var(--color-warning-bg) 0%, #fff 8%);
}

.alert-card .alert-badge {
  flex-shrink: 0;
  width: 48px;
  text-align: center;
}

.alert-card .alert-badge .badge-icon {
  font-size: 28px;
  display: block;
}

.alert-card .alert-info {
  flex: 1;
  min-width: 0;
}

.alert-card .alert-info .info-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
}

.alert-card .alert-info .elder-name {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.alert-card .alert-info .alert-type {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.alert-card .alert-info .alert-type.type-danger {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.alert-card .alert-info .alert-type.type-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.alert-card .alert-info .info-sub {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.alert-card .alert-info .info-sub .location {
  color: var(--color-primary);
  font-weight: 500;
}

.alert-card .alert-time {
  flex-shrink: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  text-align: right;
  min-width: 70px;
}

.alert-card .alert-action {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 4px;
}

/* 处理弹窗 */
.process-tip {
  margin-bottom: var(--spacing-md);
  color: var(--color-text-secondary);
}

.process-options {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.process-options .el-radio {
  margin-right: 0;
}

/* AI 救援简报弹窗 */
.rescue-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
  color: var(--color-text-secondary);
}

.rescue-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--color-border-light);
  font-size: 12px;
  color: var(--color-text-secondary);
}

.rescue-collapse {
  max-height: 480px;
  overflow-y: auto;
}

.rescue-content {
  margin: 0;
  line-height: 1.8;
  color: var(--color-text);
  font-size: var(--font-size-base);
  white-space: pre-wrap;
}

/* 响应式 */
@media (max-width: 768px) {
  .alert-card {
    flex-wrap: wrap;
    padding: var(--spacing-sm) var(--spacing-md);
    gap: var(--spacing-sm);
  }
  .alert-card .alert-badge {
    width: 36px;
  }
  .alert-card .alert-badge .badge-icon {
    font-size: 22px;
  }
  .alert-card .alert-info .info-sub {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .alert-card .alert-time {
    text-align: left;
  }
  .alert-summary {
    flex-direction: column;
  }
  .process-options {
    flex-direction: column;
  }
}
</style>
