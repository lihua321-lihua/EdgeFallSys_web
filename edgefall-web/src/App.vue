<template>
  <!-- 全局告警弹窗：覆盖在任何页面之上 -->
  <AlertPopup />

  <!-- 路由出口 -->
  <router-view />
</template>

<script setup>
/**
 * 应用根组件 - WebSocket初始化、全局告警弹窗
 */
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/useAuthStore'
import { useAlertStore } from '@/store/useAlertStore'
import wsClient from '@/utils/websocket'
import AlertPopup from '@/components/AlertPopup.vue'

const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()

// 登录后初始化 WebSocket
watch(() => authStore.isLoggedIn, (val) => {
  if (val) {
    wsClient.connect(authStore.token)
    // 注册告警消息监听（消息类型与后端接口文档一致）
    wsClient.on('fall_alert', (msg) => {
      alertStore.addAlert(msg)
    })
    wsClient.on('scam_alert', (msg) => {
      alertStore.addAlert(msg)
    })
    wsClient.on('intrusion_alert', (msg) => {
      alertStore.addAlert(msg)
    })
    wsClient.on('device_offline', (msg) => {
      console.warn('设备离线:', msg)
    })
    wsClient.on('device_low_battery', (msg) => {
      console.warn('设备低电量:', msg)
    })
    wsClient.on('task_assigned', (msg) => {
      console.log('新走访任务派发:', msg)
    })
  } else {
    wsClient.disconnect()
    router.push('/login')
  }
})
</script>
