<template>
  <div class="village-layout">
    <header class="village-header">
      <div class="header-left">
        <AppLogo :size="28" />
        <span class="header-title">EdgeFall 养老守护系统</span>
      </div>
      <div class="header-right">
        <span class="header-user"><strong>{{ authStore.displayName }}</strong> {{ roleLabel }}</span>
        <router-link v-if="authStore.isAdminRole" to="/admin/dashboard" class="switch-link">
          管理后台
        </router-link>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </header>
    <nav class="village-tabs">
      <router-link to="/village/alert-board" class="tab-item">
        紧急工单
        <span v-if="alertStore.pendingCount > 0" class="tab-badge">{{ alertStore.pendingCount }}</span>
      </router-link>
      <router-link to="/village/elder-roster" class="tab-item">老人名册</router-link>
      <router-link to="/village/visit-tasks" class="tab-item">走访任务</router-link>
    </nav>
    <main class="village-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
/**
 * 村委会端布局 - 顶部Tab导航、未读告警徽章、用户信息
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
.village-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

/* 顶栏 */
.village-header {
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

.village-header .header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.village-header .header-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.village-header .header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.village-header .header-user {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.village-header .header-user strong {
  color: var(--color-text);
  margin-right: 4px;
}

.switch-link {
  color: var(--color-primary);
  font-size: var(--font-size-base);
  text-decoration: none;
}

.switch-link:hover {
  text-decoration: underline;
}

/* Tab 导航 */
.village-tabs {
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  padding: 0 var(--spacing-lg);
  gap: 0;
}

.village-tabs .tab-item {
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

.village-tabs .tab-item:hover {
  color: var(--color-primary);
}

.village-tabs .tab-item.router-link-exact-active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

.village-tabs .tab-badge {
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
.village-content {
  flex: 1;
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .village-header {
    padding: 0 var(--spacing-md);
  }
  .village-header .header-title {
    font-size: var(--font-size-village);
  }
  .village-tabs {
    padding: 0 var(--spacing-md);
    overflow-x: auto;
  }
  .village-tabs .tab-item {
    padding: 12px var(--spacing-md);
    font-size: 14px;
    white-space: nowrap;
  }
  .village-content {
    padding: var(--spacing-md);
  }
}
</style>
