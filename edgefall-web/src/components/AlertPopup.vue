<template>
  <el-dialog
    v-model="visible"
    :title="isProcessing ? '工单处理' : '⚠️ 紧急告警'"
    :close-on-click-modal="false"
    :show-close="false"
    :close-on-press-escape="false"
    width="520px"
    top="15vh"
  >
    <!-- 告警信息展示（未点击接单时） -->
    <div v-if="!isProcessing && alertStore.currentAlert" class="alert-popup-body">
      <div class="alert-elder">{{ alertStore.currentAlert.elder_name }}</div>
      <div class="alert-title">{{ alertStore.currentAlert.payload?.title }}</div>
      <div class="alert-location">📍 {{ alertStore.currentAlert.payload?.location }}</div>
      <div v-if="alertStore.currentAlert.payload?.ai_diagnosis" class="alert-ai">
        🧠 AI预判：{{ alertStore.currentAlert.payload.ai_diagnosis }}
      </div>
      <el-button type="danger" size="large" style="width:100%;margin-top:20px"
        @click="handleAccept">
        接单处理
      </el-button>
    </div>

    <!-- 处理表单（点击接单后） -->
    <div v-else-if="isProcessing">
      <el-radio-group v-model="actionType" class="process-radios">
        <el-radio value="VISITED" border>已上门</el-radio>
        <el-radio value="CALLED_FAMILY" border>已联系家属</el-radio>
        <el-radio value="FALSE_ALARM" border>误报</el-radio>
      </el-radio-group>
      <el-input v-model="remark" type="textarea" placeholder="备注（可选）"
        style="margin-top:16px" :rows="3" />
      <el-button type="primary" size="large" style="width:100%;margin-top:16px"
        @click="handleSubmit" :loading="submitting">
        确认提交
      </el-button>
    </div>
  </el-dialog>
</template>

<script setup>
/**
 * 告警弹窗组件 - WebSocket实时告警接单/处理、警报音播放
 */
import { ref, computed, watch } from 'vue'
import { useAlertStore } from '@/store/useAlertStore'
import { resolveAlert } from '@/api/alerts'
import { ElMessage } from 'element-plus'

const alertStore = useAlertStore()
const visible = computed(() => !!alertStore.currentAlert)
const isProcessing = computed(() => alertStore.isProcessing)

const actionType = ref('VISITED')
const remark = ref('')
const submitting = ref(false)

let audio = null

// 弹窗打开时播放警报
watch(visible, (val) => {
  if (val) {
    try {
      audio = new Audio('/alert.mp3')
      audio.loop = true
      audio.play()
    } catch (e) { /* 浏览器可能阻止自动播放 */ }
  } else {
    if (audio) { audio.pause(); audio.currentTime = 0; audio = null; }
  }
})

function handleAccept() {
  alertStore.startProcessing()
  // 点击接单后暂停警报，待提交
  if (audio) { audio.pause(); }
}

async function handleSubmit() {
  submitting.value = true
  try {
    await resolveAlert(alertStore.currentAlert.event_id, {
      handler_name: '当前用户',
      action_type: actionType.value,
      remark: remark.value,
    })
    ElMessage.success('工单处理成功')
    actionType.value = 'VISITED'
    remark.value = ''
    alertStore.dismissCurrent()
  } catch (e) {
    ElMessage.error('处理失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.alert-popup-body {
  text-align: center;
}

.alert-elder {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-danger);
  margin-bottom: var(--spacing-sm);
}

.alert-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

.alert-location {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
}

.alert-ai {
  font-size: var(--font-size-base);
  color: var(--color-primary);
  background: var(--color-primary-light);
  background: rgba(64, 158, 255, 0.08);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  margin-top: var(--spacing-sm);
}

.process-radios {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.process-radios .el-radio {
  margin-right: 0;
}
</style>
