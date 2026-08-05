<template>
  <div class="grid-layout">
    <header class="grid-header">
      <div class="header-left">
        <AppLogo :size="28" />
        <span class="header-title">EdgeFall 养老守护系统</span>
        <span class="header-end-tag">网格员端</span>
      </div>
      <div class="header-right">
        <span class="header-user"><strong>{{ authStore.displayName }}</strong> {{ roleLabel }}</span>
        <el-button text @click="router.push('/change-password')">修改密码</el-button>
        <el-button text @click="handleLogout">退出</el-button>
      </div>
    </header>
    <nav class="grid-tabs">
      <router-link to="/grid/alert-board" class="tab-item">
        紧急工单
        <span v-if="alertStore.pendingCount > 0" class="tab-badge">{{ alertStore.pendingCount }}</span>
      </router-link>
      <router-link to="/grid/elder-roster" class="tab-item">老人名册</router-link>
      <router-link to="/grid/visit-tasks" class="tab-item">走访任务</router-link>
      <router-link to="/grid/handled-records" class="tab-item">处理记录</router-link>
      <router-link to="/grid/ai-chat" class="tab-item">AI助手</router-link>
    </nav>
    <main class="grid-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
/**
 * 网格员端布局 - P0 拆分自 VillageLayout
 * 定位：基层信息采集 + 告警第一响应（现场处置）
 * 路由前缀：/grid/*
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
.grid-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-bg);
}

/* 顶栏 */
.grid-header {
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

.grid-header .header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.grid-header .header-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
}

.grid-header .header-end-tag {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-primary);
  background: var(--color-primary-bg, #e6f4ff);
  padding: 2px 8px;
  border-radius: 10px;
  margin-left: 4px;
}

.grid-header .header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.grid-header .header-user {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.grid-header .header-user strong {
  color: var(--color-text);
  margin-right: 4px;
}

/* Tab 导航 */
.grid-tabs {
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  padding: 0 var(--spacing-lg);
  gap: 0;
}

.grid-tabs .tab-item {
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

.grid-tabs .tab-item:hover {
  color: var(--color-primary);
}

.grid-tabs .tab-item.router-link-exact-active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 600;
}

.grid-tabs .tab-badge {
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
.grid-content {
  flex: 1;
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 响应式 */
@media (max-width: 768px) {
  .grid-header {
    padding: 0 var(--spacing-md);
  }
  .grid-header .header-title {
    font-size: var(--font-size-village);
  }
  .grid-tabs {
    padding: 0 var(--spacing-md);
    overflow-x: auto;
  }
  .grid-tabs .tab-item {
    padding: 12px var(--spacing-md);
    font-size: 14px;
    white-space: nowrap;
  }
  .grid-content {
    padding: var(--spacing-md);
  }
}
</style>
