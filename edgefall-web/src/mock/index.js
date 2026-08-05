/**
 * Mock 数据层 - 模拟后端接口、动态路由匹配、登录鉴权
 */
import alerts from './alerts.json'
import elders from './elders.json'
import elderDetail from './elder-detail.json'
import tasks from './tasks.json'
import devices from './devices.json'
import apiUsage from './api-usage.json'

const mockAccounts = {
  village_grid: {
    id: 1, username: 'zhang_grid', display_name: '张网格员',
    role: 'village_grid', village_id: 1, village_name: '桂花村',
  },
  village_doctor: {
    id: 2, username: 'li_doctor', display_name: '李村医',
    role: 'village_doctor', village_id: 1, village_name: '桂花村',
  },
  admin: {
    id: 3, username: 'wang_admin', display_name: '王管理员',
    role: 'admin', village_id: null, village_name: null,
  },
  super_admin: {
    id: 4, username: 'root', display_name: '超级管理员',
    role: 'super_admin', village_id: null, village_name: null,
  },
}

const mockMap = {
  '/auth/login': {
    POST: (body) => {
      const role = body?.roleHint || 'village_grid'
      const user = mockAccounts[role] || mockAccounts.village_grid
      return {
        token: 'mock-jwt-token-eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock',
        must_change_password: false,
        user,
      }
    },
  },
  '/auth/me': {
    GET: mockAccounts.village_grid,
  },
  '/auth/forgot-password': {
    POST: () => ({
      message: '如需重置密码，请联系系统管理员。管理员重置后初始密码为 123456，登录后请及时修改。',
    }),
  },
  '/auth/change-password': {
    POST: () => ({ message: '密码修改成功' }),
  },
  '/alerts': { GET: alerts },
  '/elders': { GET: { items: elders, total: elders.length } },
  '/tasks/visits': {
    GET: { items: tasks, total: tasks.length },
    POST: () => ({ message: '反馈提交成功' }),
  },
  '/devices': { GET: { items: devices, total: devices.length } },
  '/devices/rebind': {
    POST: (body) => ({ message: '换绑成功', device_sn: body?.device_sn, elder_id: body?.elder_id }),
  },
  '/system/api-usage': { GET: apiUsage },
}

export function getMockData(url, method = 'GET', body = null) {
  const cleanUrl = url.split('?')[0].replace(/\/$/, '')

  // 1. 精确匹配（优先）
  const sortedKeys = Object.keys(mockMap).sort((a, b) => b.length - a.length)
  for (const key of sortedKeys) {
    const cleanKey = key.replace(/\/$/, '')
    if (cleanUrl === cleanKey) {
      const entry = mockMap[key]
      const handler = entry[method] || entry.GET
      if (typeof handler === 'function') {
        return { code: 200, message: 'ok', data: handler(body) }
      }
      return { code: 200, message: 'ok', data: handler }
    }
  }

  // 2. 动态路径匹配：/elders/:id → 详情, /elders/:id/ai-report → AI报告
  // /alerts/:id/resolve → 处理工单
  const eldersMatch = cleanUrl.match(/^\/elders\/([^/]+)$/)
  if (eldersMatch) {
    return { code: 200, message: 'ok', data: elderDetail }
  }

  const reportMatch = cleanUrl.match(/^\/elders\/([^/]+)\/ai-report$/)
  if (reportMatch) {
    return { code: 200, message: 'ok', data: elderDetail.ai_report }
  }

  const resolveMatch = cleanUrl.match(/^\/alerts\/[^/]+\/resolve$/)
  if (resolveMatch && method === 'POST') {
    return { code: 200, message: 'ok', data: { message: '工单已处理' } }
  }

  // 3. 前缀匹配（用于 /tasks/visits/:id/feedback 等）
  for (const key of sortedKeys) {
    const cleanKey = key.replace(/\/$/, '')
    if (cleanUrl.startsWith(cleanKey + '/')) {
      const entry = mockMap[key]
      const handler = entry[method] || entry.GET
      if (typeof handler === 'function') {
        return { code: 200, message: 'ok', data: handler(body) }
      }
      return { code: 200, message: 'ok', data: handler }
    }
  }

  return { code: 404, message: 'Mock 数据未找到', data: null }
}