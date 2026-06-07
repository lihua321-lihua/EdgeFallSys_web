<template>
  <div class="page-visit-tasks">
    <div class="page-title-row">
      <h2>关怀走访任务清单</h2>
    </div>

    <!-- 状态筛选 -->
    <el-radio-group v-model="filter" class="filter-tabs" @change="handleFilter">
      <el-radio-button value="all">全部 ({{ tasks.length }})</el-radio-button>
      <el-radio-button value="pending">待走访 ({{ pendingCount }})</el-radio-button>
      <el-radio-button value="completed">已完成 ({{ completedCount }})</el-radio-button>
    </el-radio-group>

    <!-- 任务卡片列表 -->
    <div v-if="filteredTasks.length" class="task-list">
      <div
        v-for="task in filteredTasks"
        :key="task.task_id"
        :class="['task-card', task.status === 'completed' ? 'completed' : '']"
      >
        <div class="task-header">
          <span class="task-id">#{{ task.task_id }}</span>
          <el-tag :type="task.status === 'completed' ? 'success' : 'danger'" size="small">
            {{ task.status === 'completed' ? '已完成' : '待走访' }}
          </el-tag>
        </div>
        <div class="task-elder">👤 {{ task.elder_name }}</div>
        <div class="task-reason">{{ task.trigger_reason }}</div>
        <div class="task-footer">
          <span class="task-date">{{ task.create_time }}</span>
          <el-button
            v-if="task.status === 'pending'"
            type="primary"
            size="small"
            @click="openFeedback(task)"
          >
            填写反馈
          </el-button>
          <el-button v-else size="small" disabled>已反馈</el-button>
        </div>
      </div>
    </div>

    <EmptyState v-else icon="📋" text="暂无走访任务" />
  </div>

  <!-- 反馈弹窗 -->
  <el-dialog
    v-model="dialogVisible"
    :title="'走访反馈 - ' + currentTask?.elder_name"
    width="480px"
    :close-on-click-modal="false"
  >
    <p style="margin-bottom: 8px; color: var(--color-text-secondary);">请描述走访情况：</p>
    <el-input
      v-model="feedback"
      type="textarea"
      placeholder="例如：老人感冒卧床，已通知村医拿药..."
      :rows="4"
    />
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitFeedback" :loading="submitting">提交反馈</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 走访任务清单 - 状态筛选、反馈弹窗交互
 */
import { ref, computed, onMounted } from 'vue'
import { getVisitTasks, submitTaskFeedback } from '@/api/tasks'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'

const tasks = ref([])
const filter = ref('all')
const dialogVisible = ref(false)
const currentTask = ref(null)
const feedback = ref('')
const submitting = ref(false)

const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)
const completedCount = computed(() => tasks.value.filter(t => t.status === 'completed').length)

const filteredTasks = computed(() => {
  if (filter.value === 'all') return tasks.value
  return tasks.value.filter(t => t.status === filter.value)
})

function handleFilter() {
  // computed 自动过滤
}

async function loadTasks() {
  try {
    const res = await getVisitTasks()
    tasks.value = res.items || []
  } catch (e) {
    console.error('加载走访任务失败', e)
  }
}

function openFeedback(task) {
  currentTask.value = task
  feedback.value = ''
  dialogVisible.value = true
}

async function submitFeedback() {
  if (!currentTask.value) return
  submitting.value = true
  try {
    await submitTaskFeedback(currentTask.value.task_id, { feedback: feedback.value })
    ElMessage.success('反馈提交成功')
    currentTask.value.status = 'completed'
    currentTask.value.feedback = feedback.value
    dialogVisible.value = false
  } catch (e) {
    ElMessage.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.page-visit-tasks {
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

.filter-tabs {
  margin-bottom: var(--spacing-md);
}

/* 任务卡片 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.task-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  padding: var(--spacing-md) var(--spacing-lg);
  box-shadow: var(--shadow-card);
  border-left: 4px solid var(--color-danger);
  transition: transform 0.15s, box-shadow 0.15s;
}

.task-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.task-card.completed {
  border-left-color: var(--color-success);
  opacity: 0.75;
}

.task-card .task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-xs);
}

.task-card .task-id {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-family: monospace;
}

.task-card .task-elder {
  font-size: var(--font-size-village);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

.task-card .task-reason {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-sm);
}

.task-card .task-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.task-card .task-date {
  font-size: 12px;
  color: var(--color-text-light);
}

/* 响应式 */
@media (max-width: 768px) {
  .task-card {
    padding: var(--spacing-sm) var(--spacing-md);
  }
}
</style>
