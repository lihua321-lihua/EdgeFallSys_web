/**
 * 告警状态管理 - WebSocket告警队列、弹窗控制、待处理计数
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAlertStore = defineStore('alert', () => {
  const queue = ref([])
  const currentAlert = ref(null)
  const isProcessing = ref(false)
  const pendingCount = ref(0)

  const unreadCount = computed(() => queue.value.length + (currentAlert.value ? 1 : 0))

  function addAlert(payload) {
    const exists = queue.value.find(a => a.event_id === payload.event_id)
                   || currentAlert.value?.event_id === payload.event_id
    if (exists) return

    if (!currentAlert.value) {
      currentAlert.value = payload
    } else {
      queue.value.push(payload)
    }
    queue.value.sort((a, b) => {
      const order = { 'CRITICAL': 0, 'HIGH': 1 }
      return (order[a.level] ?? 2) - (order[b.level] ?? 2)
    })
  }

  function dismissCurrent() {
    currentAlert.value = null
    isProcessing.value = false
    if (queue.value.length > 0) {
      currentAlert.value = queue.value.shift()
    }
  }

  function startProcessing() {
    isProcessing.value = true
  }

  function setPendingCount(count) {
    pendingCount.value = count
  }

  return { queue, currentAlert, isProcessing, unreadCount, pendingCount, addAlert, dismissCurrent, startProcessing, setPendingCount }
})
