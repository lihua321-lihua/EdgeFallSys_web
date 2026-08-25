<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="sidebar-logo">
        <AppLogo :size="32" />
        <div class="logo-text-wrap">
          <span class="logo-brand">EdgeFall</span>
          <span class="logo-sub">管理后台</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/admin/dashboard" class="nav-item">
          <span class="nav-icon">📊</span> 仪表盘
        </router-link>
        <router-link to="/admin/device-assets" class="nav-item">
          <span class="nav-icon">📱</span> 设备管理
        </router-link>
        <router-link to="/admin/organization" class="nav-item">
          <span class="nav-icon">🏢</span> 组织架构
        </router-link>
        <router-link to="/admin/api-monitor" class="nav-item">
          <span class="nav-icon">📡</span> API监控
        </router-link>
        <router-link to="/admin/cameras" class="nav-item">
          <span class="nav-icon">📷</span> 摄像头
        </router-link>
        <router-link to="/admin/ai-chat" class="nav-item">
          <span class="nav-icon">🤖</span> AI助手
        </router-link>
      </nav>
    </aside>
    <div class="admin-main">
      <header class="admin-header">
        <div class="header-right">
          <span class="header-user"><strong>{{ authStore.displayName }}</strong> {{ roleLabel }}</span>
          <!-- P0 修正：取消 admin 直接进入村委会端的快捷链接（C-04 管理不下沉）
               管理员如需查看基层数据，应通过 /admin/* 下的只读视图访问 -->
          <el-button text @click="router.push('/change-password')">修改密码</el-button>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </header>
      <main class="admin-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
/**
 * 管理员端布局 - 侧边栏导航、用户信息、退出登录
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/useAuthStore'
import AppLogo from '@/components/AppLogo.vue'

const router = useRouter()
const authStore = useAuthStore()

const roleLabel = computed(() => {
  const map = { admin: '管理员', super_admin: '超管' }
  return map[authStore.role] || ''
})

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

/* 侧边栏 */
.admin-sidebar {
  width: var(--sidebar-width);
  background: var(--color-sidebar);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 200;
  overflow-y: auto;
}

.sidebar-logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-lg);
  gap: var(--spacing-sm);
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.sidebar-logo .logo-text-wrap {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.sidebar-logo .logo-brand {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.5px;
}

.sidebar-logo .logo-sub {
  font-size: 11px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.55);
  margin-top: 2px;
  letter-spacing: 1px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--spacing-xs) 0;
}

.sidebar-nav .nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 14px var(--spacing-lg);
  color: rgba(255,255,255,0.65);
  text-decoration: none;
  font-size: var(--font-size-base);
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.sidebar-nav .nav-item:hover {
  color: #fff;
  background: rgba(255,255,255,0.05);
}

.sidebar-nav .nav-item.router-link-exact-active {
  color: #fff;
  background: rgba(64,158,255,0.15);
  border-left-color: var(--color-primary);
}

.sidebar-nav .nav-item .nav-icon {
  font-size: 18px;
  width: 20px;
  text-align: center;
}

/* 右侧主区域 */
.admin-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* 顶栏 */
.admin-header {
  height: var(--header-height);
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 var(--spacing-lg);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.admin-header .header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.admin-header .header-user {
  color: var(--color-text-secondary);
  font-size: var(--font-size-base);
}

.admin-header .header-user strong {
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

/* 管理员内容区 */
.admin-content {
  flex: 1;
  padding: var(--spacing-lg);
  background: var(--color-bg);
}

/* 响应式 */
@media (max-width: 768px) {
  .admin-sidebar {
    width: 60px;
  }
  .sidebar-logo .logo-text-wrap {
    display: none;
  }
  .sidebar-nav .nav-item {
    justify-content: center;
    padding: 14px 0;
    font-size: 0;
  }
  .sidebar-nav .nav-item .nav-icon {
    font-size: 20px;
  }
  .admin-main {
    margin-left: 60px;
  }
  .admin-content {
    padding: var(--spacing-md);
  }
}
</style>
