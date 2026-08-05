<template>
  <div class="doctor-layout">
    <header class="doctor-header">
      <div class="header-left">
        <AppLogo :size="28" />
        <span class="header-title">EdgeFall 养老守护系统</span>
        <span class="header-end-tag">村医端</span>
      </div>
      <div class="header-right">
        <span class="header-user"><strong>{{ authStore.displayName }}</strong> {{ roleLabel }}</span>
        <el-button text @click="router.push('/change-password')">修改密码</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </header>
    <nav class="doctor-tabs">
      <router-link to="/doctor/alert-board" class="tab-item">
        紧急工单
        <span v-if="alertStore.pendingCount > 0" class="tab-badge">{{ alertStore.pendingCount }}</span>
      </router-link>
      <router-link to="/doctor/elder-roster" class="tab-item">老人名册</router-link>
      <router-link to="/doctor/visit-tasks" class="tab-item">随访任务</router-link>
      <router-link to="/doctor/handled-records" class="tab-item">处理记录</router-link>
      <router-link to="/doctor/ai-chat" class="tab-item">AI助手</router-link>
    </nav>
    <main class="doctor-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
/**
 * 村医端布局 - P0 拆分自 VillageLayout
 * 定位：基层健康守护 + 医疗判断
 * 路由前缀：/doctor/*
 * 注：走访任务在村医端显示为"随访任务"
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/useAuthStore'
import { useAlertStore } from '@/store/useAlertStore'
import AppLogo from '@/components/AppLogo.vue'

const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()

const roleLabel = computed(() => {
  const map = { village_grid: '网格员', village_doctor: '村医', admin: '管理员', super_admin: '超管' }
  return map[authStore.role] || ''
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.doctor-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

/* 顶栏 */
.doctor-header {
  height: var(--header-height);
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.doctor-header .header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.doctor-header .header-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.doctor-header .header-end-tag {
  font-size: 12px;
  font-weight: 500;
  color: #52c41a;
  background: #f6ffed;
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 4px;
  border: 1px solid #d9f7be;
}

.doctor-header .header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.doctor-header .header-user {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.doctor-header .header-user strong {
  color: var(--color-text);
  margin-right: 4px;
}

/* Tab 导航 */
.doctor-tabs {
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  padding: 0 var(--spacing-lg);
  gap: 0;
}

.doctor-tabs .tab-item {
  padding: 14px var(--spacing-lg);
  font-size: var(--font-size-village);
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  position: relative;
}

.doctor-tabs .tab-item:hover {
  color: var(--color-primary);
}

.doctor-tabs .tab-item.router-link-exact-active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

.doctor-tabs .tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  background: var(--color-danger);
  color: #fff;
  line-height: 1;
}

/* 内容区 */
.doctor-content {
  flex: 1;
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .doctor-header {
    padding: 0 var(--spacing-md);
  }
  .doctor-header .header-title {
    font-size: var(--font-size-village);
  }
  .doctor-tabs {
    padding: 0 var(--spacing-md);
    overflow-x: auto;
  }
  .doctor-tabs .tab-item {
    padding: 12px var(--spacing-md);
    font-size: 14px;
    white-space: nowrap;
  }
  .doctor-content {
    padding: var(--spacing-md);
  }
}
</style>
