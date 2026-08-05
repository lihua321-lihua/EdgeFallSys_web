<template>
  <div class="page-handled-records">
    <div class="page-title-row">
      <h2>处理记录</h2>
      <p class="page-subtitle">查看已处理紧急工单与已完成走访任务的详细处理信息</p>
    </div>

    <el-tabs v-model="activeTab" class="records-tabs" @tab-change="handleTabChange">
      <!-- ============ 紧急工单处理记录 ============ -->
      <el-tab-pane label="紧急工单处理记录" name="alerts">
        <div v-if="alerts.length" class="record-list">
          <div
            v-for="alert in alerts"
            :key="alert.event_id"
            class="record-card"
            @click="openDetail(alert, 'alert')"
          >
            <div class="record-header">
              <span class="record-elder">👤 {{ alert.elder_name }}</span>
              <div class="record-tags">
                <el-tag :type="alert.level === 'CRITICAL' ? 'danger' : 'warning'" size="small">
                  {{ typeLabel(alert.type) }}
                </el-tag>
                <el-tag type="success" size="small">{{ actionLabel(alert.action_type) }}</el-tag>
              </div>
            </div>
            <div class="record-meta">
              <span>事件编号：{{ alert.event_id }}</span>
              <span>发生位置：{{ alert.payload?.location || '—' }}</span>
            </div>
            <div class="record-meta">
              <span>处理人：{{ alert.handler_name || '未记录' }}</span>
              <span>处理时间：{{ formatUnix(alert.handle_time) }}</span>
            </div>
            <div v-if="alert.remark" class="record-remark">备注：{{ alert.remark }}</div>
            <div v-if="alert.medical_judgment" class="record-remark medical">
              医疗判断：{{ alert.medical_judgment }}
              <el-tag v-if="alert.need_transfer" type="danger" size="small" style="margin-left: 8px">已送医转诊</el-tag>
            </div>
          </div>
        </div>
        <EmptyState v-else icon="✅" text="暂无已处理工单" />
      </el-tab-pane>

      <!-- ============ 走访/随访任务完成记录 ============ -->
      <el-tab-pane :label="taskLabel + '任务完成记录'" name="tasks">
        <div v-if="tasks.length" class="record-list">
          <div
            v-for="task in tasks"
            :key="task.task_id"
            class="record-card"
            @click="openDetail(task, 'task')"
          >
            <div class="record-header">
              <span class="record-elder">👤 {{ task.elder_name }}</span>
              <el-tag type="success" size="small">已完成</el-tag>
            </div>
            <div class="record-meta">
              <span>任务编号：{{ task.task_id }}</span>
              <span>创建时间：{{ task.create_time || '—' }}</span>
            </div>
            <div class="record-meta">
              <span>处理人：{{ task.handler_name || '未记录' }}</span>
              <span>完成时间：{{ task.handle_time || '未记录' }}</span>
            </div>
            <div v-if="task.feedback" class="record-remark">处理结果：{{ task.feedback }}</div>
          </div>
        </div>
        <EmptyState v-else icon="✅" :text="'暂无已完成' + taskLabel + '任务'" />
      </el-tab-pane>
    </el-tabs>
  </div>

  <!-- 详情弹窗 -->
  <el-dialog v-model="detailVisible" :title="detailTitle" width="560px">
    <el-descriptions v-if="detailType === 'alert'" :column="1" border>
      <el-descriptions-item label="事件编号">{{ current?.event_id }}</el-descriptions-item>
      <el-descriptions-item label="老人姓名">{{ current?.elder_name }}</el-descriptions-item>
      <el-descriptions-item label="告警类型">{{ typeLabel(current?.type) }}</el-descriptions-item>
      <el-descriptions-item label="告警级别">{{ current?.level }}</el-descriptions-item>
      <el-descriptions-item label="发生位置">{{ current?.payload?.location || '—' }}</el-descriptions-item>
      <el-descriptions-item label="告警标题">{{ current?.payload?.title || '—' }}</el-descriptions-item>
      <el-descriptions-item label="AI预判">{{ current?.payload?.ai_diagnosis || '—' }}</el-descriptions-item>
      <el-descriptions-item label="发生时间">{{ formatUnix(current?.create_time) }}</el-descriptions-item>
      <el-descriptions-item label="处理人">{{ current?.handler_name || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="处理时间">{{ formatUnix(current?.handle_time) }}</el-descriptions-item>
      <el-descriptions-item label="处理结果">{{ actionLabel(current?.action_type) }}</el-descriptions-item>
      <el-descriptions-item label="处理备注">{{ current?.remark || '—' }}</el-descriptions-item>
      <el-descriptions-item v-if="current?.medical_judgment" label="医疗判断">
        {{ current.medical_judgment }}
        <el-tag v-if="current?.need_transfer" type="danger" size="small" style="margin-left: 8px">需送医转诊</el-tag>
      </el-descriptions-item>
    </el-descriptions>
    <el-descriptions v-else :column="1" border>
      <el-descriptions-item label="任务编号">{{ current?.task_id }}</el-descriptions-item>
      <el-descriptions-item label="老人姓名">{{ current?.elder_name }}</el-descriptions-item>
      <el-descriptions-item label="触发原因">{{ current?.trigger_reason || '—' }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ current?.create_time || '—' }}</el-descriptions-item>
      <el-descriptions-item label="处理人">{{ current?.handler_name || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="完成时间">{{ current?.handle_time || '未记录' }}</el-descriptions-item>
      <el-descriptions-item label="处理结果/备注">{{ current?.feedback || '—' }}</el-descriptions-item>
    </el-descriptions>
    <template #footer>
      <el-button @click="detailVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 处理记录 - 已处理紧急工单 + 已完成走访任务的详细处理信息查看
 * P0 修正：按角色分化文案（走访/随访），新增医疗判断字段展示
 */
import { ref, computed, onMounted } from 'vue'
import { getAlerts } from '@/api/alerts'
import { getVisitTasks } from '@/api/tasks'
import { useAuthStore } from '@/store/useAuthStore'
import EmptyState from '@/components/EmptyState.vue'

const authStore = useAuthStore()

// P0: 角色文案
const isDoctor = computed(() => authStore.role === 'village_doctor')
const taskLabel = computed(() => isDoctor.value ? '随访' : '走访')

const activeTab = ref('alerts')
const alerts = ref([])
const tasks = ref([])
const detailVisible = ref(false)
const current = ref(null)
const detailType = ref('alert')

const loaded = { alerts: false, tasks: false }

const detailTitle = computed(() =>
  detailType.value === 'alert' ? '工单处理详情' : `${taskLabel.value}任务详情`
)

const TYPE_MAP = { FALL_DETECTED: '跌倒报警', SCAM_ALERT: '诈骗预警', INTRUSION_ALERT: '入侵预警' }
// P0: 新增 MEDICAL_JUDGE（村医医疗判断）
const ACTION_MAP = {
  VISITED: '已上门',
  CALLED_FAMILY: '已联系家属',
  FALSE_ALARM: '误报',
  MEDICAL_JUDGE: '医疗判断',
  TRANSFER: '已转派',
}

function typeLabel(type) { return TYPE_MAP[type] || '异常告警' }
function actionLabel(action) { return ACTION_MAP[action] || '—' }

function formatUnix(ts) {
  if (!ts) return '未记录'
  const d = new Date(ts * 1000)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function loadAlerts() {
  try {
    const res = await getAlerts({ status: 'resolved' })
    alerts.value = res || []
    loaded.alerts = true
  } catch (e) {
    // 错误由 request.js 拦截器统一提示
  }
}

async function loadTasks() {
  try {
    const res = await getVisitTasks({ status: 'completed' })
    tasks.value = res?.items || []
    loaded.tasks = true
  } catch (e) {
    // 错误由 request.js 拦截器统一提示
  }
}

function handleTabChange(name) {
  if (name === 'alerts' && !loaded.alerts) loadAlerts()
  if (name === 'tasks' && !loaded.tasks) loadTasks()
}

function openDetail(row, type) {
  current.value = row
  detailType.value = type
  detailVisible.value = true
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped>
.page-handled-records {
  padding: 0;
}

.page-title-row {
  margin-bottom: var(--spacing-md);
}

.page-title-row h2 {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

.records-tabs {
  background: transparent;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.record-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-md) var(--spacing-lg);
  box-shadow: var(--shadow-card);
  border-left: 4px solid var(--color-success);
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.record-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-xs);
}

.record-elder {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
}

.record-tags {
  display: flex;
  gap: 6px;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
  margin-top: 4px;
}

.record-remark {
  margin-top: 6px;
  padding: 6px 10px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-base);
  color: var(--color-text);
  line-height: 1.6;
}

.record-remark.medical {
  background: #f6ffed;
  border-left: 3px solid #52c41a;
  color: #237804;
}

@media (max-width: 768px) {
  .record-card {
    padding: var(--spacing-sm) var(--spacing-md);
  }
  .record-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
}
</style>
