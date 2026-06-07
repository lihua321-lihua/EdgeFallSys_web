/**
 * 路由配置 - 页面路由定义、权限守卫、角色校验
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/store/useAuthStore'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/village',
    component: () => import('@/layout/VillageLayout.vue'),
    meta: { roles: ['village_grid', 'village_doctor', 'admin', 'super_admin'] },
    children: [
      {
        path: 'alert-board',
        name: 'AlertBoard',
        component: () => import('@/views/village/AlertBoard.vue'),
        meta: { title: '紧急工单台' },
      },
      {
        path: 'elder-roster',
        name: 'ElderRoster',
        component: () => import('@/views/village/ElderRoster.vue'),
        meta: { title: '老人名册' },
      },
      {
        path: 'elder-detail/:id',
        name: 'ElderDetail',
        component: () => import('@/views/village/ElderDetail.vue'),
        meta: { title: '老人详情' },
      },
      {
        path: 'visit-tasks',
        name: 'VisitTasks',
        component: () => import('@/views/village/VisitTasks.vue'),
        meta: { title: '走访任务' },
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layout/AdminLayout.vue'),
    meta: { roles: ['admin', 'super_admin'] },
    redirect: '/admin/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/Dashboard.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'device-assets',
        name: 'DeviceAssets',
        component: () => import('@/views/admin/DeviceAssets.vue'),
        meta: { title: '设备管理' },
      },
      {
        path: 'api-monitor',
        name: 'ApiMonitor',
        component: () => import('@/views/admin/ApiMonitor.vue'),
        meta: { title: 'API监控' },
      },
      {
        path: 'organization',
        name: 'Organization',
        component: () => import('@/views/admin/Organization.vue'),
        meta: { title: '组织架构' },
      },
    ],
  },
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: { noAuth: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 全局前置守卫 —— RBAC 权限校验
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - EdgeFall` : 'EdgeFall 养老守护系统'

  const authStore = useAuthStore()

  // 无需认证的页面直接放行
  if (to.meta.noAuth) {
    return next()
  }

  // 未登录 → 跳转登录
  if (!authStore.isLoggedIn) {
    return next('/login')
  }

  // 角色校验
  const allowedRoles = to.meta.roles
  if (allowedRoles && !allowedRoles.includes(authStore.role)) {
    // super_admin 可访问所有页面
    if (authStore.role === 'super_admin') {
      return next()
    }
    // admin 可访问村委会端
    if (authStore.role === 'admin' && to.path.startsWith('/village')) {
      return next()
    }
    return next('/login')
  }

  next()
})

export default router
