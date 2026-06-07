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
            :type="alert.level === 'CRITICAL' ? 'danger' : 'warning'"
            size="large"
            @click="openProcessDialog(alert)"
          >
            接单处理
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <EmptyState v-else icon="☕" text="暂无待处理工单" />
  </div>

  <!-- 处理弹窗 -->
  <el-dialog
    v-model="dialogVisible"
    :title="'工单处理 - ' + currentAlert?.elder_name"
    width="480px"
    :close-on-click-modal="false"
  >
    <p class="process-tip">请选择处理方式：</p>
    <el-radio-group v-model="processType" class="process-options">
      <el-radio value="VISITED" border>已上门</el-radio>
      <el-radio value="CALLED_FAMILY" border>已联系家属</el-radio>
      <el-radio value="FALSE_ALARM" border>误报</el-radio>
    </el-radio-group>
    <el-input
      v-model="remark"
      type="textarea"
      placeholder="备注（可选）"
      :rows="3"
      style="margin-top: 16px"
    />
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitProcess" :loading="submitting">确认提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 紧急工单台 - 告警列表、WebSocket实时推送、工单处理弹窗
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getAlerts, resolveAlert } from '@/api/alerts'
import { useAlertStore } from '@/store/useAlertStore'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'

const alertStore = useAlertStore()

const alerts = ref([])
const dialogVisible = ref(false)
const currentAlert = ref(null)
const processType = ref('VISITED')
const remark = ref('')
const submitting = ref(false)

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
  processType.value = 'VISITED'
  remark.value = ''
  dialogVisible.value = true
}

async function submitProcess() {
  if (!currentAlert.value) return
  submitting.value = true
  try {
    await resolveAlert(currentAlert.value.event_id, {
      handler_name: '当前用户',
      action_type: processType.value,
      remark: remark.value,
    })
    ElMessage.success('工单处理成功')
    alerts.value = alerts.value.filter(a => a.event_id !== currentAlert.value.event_id)
    alertStore.setPendingCount(alerts.value.length)
    dialogVisible.value = false
  } catch (e) {
    ElMessage.error('处理失败，请重试')
  } finally {
    submitting.value = false
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
