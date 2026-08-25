/**
 * 路由配置 - 页面路由定义、权限守卫、角色校验
 * P0 修正：拆分 /village/* 为 /grid/*（网格员端）和 /doctor/*（村医端）
 *         取消 admin 访问 /village/* 的放行（C-04 管理不下沉原则）
 *         四端路由组独立，super_admin 可访问全部
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
    path: '/change-password',
    name: 'ChangePassword',
    component: () => import('@/views/ChangePassword.vue'),
    meta: { title: '修改密码' },
  },

  // ============ P0: 网格员端（village_grid） ============
  {
    path: '/grid',
    component: () => import('@/layout/GridLayout.vue'),
    meta: { roles: ['village_grid'] },
    redirect: '/grid/alert-board',
    children: [
      {
        path: 'alert-board',
        name: 'GridAlertBoard',
        component: () => import('@/views/village/AlertBoard.vue'),
        meta: { title: '紧急工单台' },
      },
      {
        path: 'elder-roster',
        name: 'GridElderRoster',
        component: () => import('@/views/village/ElderRoster.vue'),
        meta: { title: '老人名册' },
      },
      {
        path: 'elder-detail/:id',
        name: 'GridElderDetail',
        component: () => import('@/views/village/ElderDetail.vue'),
        meta: { title: '老人详情' },
      },
      {
        path: 'visit-tasks',
        name: 'GridVisitTasks',
        component: () => import('@/views/village/VisitTasks.vue'),
        meta: { title: '走访任务' },
      },
      {
        path: 'handled-records',
        name: 'GridHandledRecords',
        component: () => import('@/views/village/HandledRecords.vue'),
        meta: { title: '处理记录' },
      },
      {
        path: 'ai-chat',
        name: 'GridAiChat',
        component: () => import('@/views/common/AIChat.vue'),
        meta: { title: 'AI助手' },
      },
    ],
  },

  // ============ P0: 村医端（village_doctor） ============
  {
    path: '/doctor',
    component: () => import('@/layout/DoctorLayout.vue'),
    meta: { roles: ['village_doctor'] },
    redirect: '/doctor/alert-board',
    children: [
      {
        path: 'alert-board',
        name: 'DoctorAlertBoard',
        component: () => import('@/views/village/AlertBoard.vue'),
        meta: { title: '紧急工单台' },
      },
      {
        path: 'elder-roster',
        name: 'DoctorElderRoster',
        component: () => import('@/views/village/ElderRoster.vue'),
        meta: { title: '老人名册' },
      },
      {
        path: 'elder-detail/:id',
        name: 'DoctorElderDetail',
        component: () => import('@/views/village/ElderDetail.vue'),
        meta: { title: '老人详情' },
      },
      {
        path: 'visit-tasks',
        name: 'DoctorVisitTasks',
        component: () => import('@/views/village/VisitTasks.vue'),
        meta: { title: '随访任务' },
      },
      {
        path: 'handled-records',
        name: 'DoctorHandledRecords',
        component: () => import('@/views/village/HandledRecords.vue'),
        meta: { title: '处理记录' },
      },
      {
        path: 'ai-chat',
        name: 'DoctorAiChat',
        component: () => import('@/views/common/AIChat.vue'),
        meta: { title: 'AI助手' },
      },
    ],
  },

  // ============ 管理员端（admin） ============
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
        path: 'cameras',
        name: 'Cameras',
        component: () => import('@/views/admin/Cameras.vue'),
        meta: { title: '摄像头监控' },
      },
      {
        path: 'ai-chat',
        name: 'AiChat',
        component: () => import('@/views/common/AIChat.vue'),
        meta: { title: 'AI助手' },
      },
      {
        path: 'organization',
        name: 'Organization',
        component: () => import('@/views/admin/Organization.vue'),
        meta: { title: '组织架构' },
      },
    ],
  },

  // ============ P0: 兼容旧 /village/* 路径，重定向到对应端 ============
  // 已登录用户访问旧路径时，按角色重定向到新端
  {
    path: '/village/:pathMatch(.*)*',
    name: 'VillageRedirect',
    redirect: () => {
      const authStore = useAuthStore()
      if (authStore.role === 'village_doctor') {
        return { path: '/doctor/alert-board' }
      }
      return { path: '/grid/alert-board' }
    },
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

  // 被强制改密（首次登录/被重置后）时，仅允许停留在修改密码页
  if (authStore.mustChangePassword && to.path !== '/change-password') {
    return next('/change-password')
  }

  // 角色校验
  const allowedRoles = to.meta.roles
  if (allowedRoles && !allowedRoles.includes(authStore.role)) {
    // P0: super_admin 可访问所有页面（审计查阅需要）
    if (authStore.role === 'super_admin') {
      return next()
    }
    // P0 修正：取消 admin 访问 /grid/* 和 /doctor/* 的放行（C-04 管理不下沉）
    // 管理员如需查看基层数据，应通过 /admin/* 下的只读视图访问
    return next('/login')
  }

  next()
})

export default router
