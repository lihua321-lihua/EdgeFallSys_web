/**
 * Axios 请求封装 - Mock拦截、Token注入、统一错误处理
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/useAuthStore'
import { getMockData } from '@/mock'

const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

service.interceptors.request.use((config) => {
  if (USE_MOCK) {
    const body = config.data ? (typeof config.data === 'string' ? JSON.parse(config.data) : config.data) : null
    const mockData = getMockData(config.url, config.method?.toUpperCase(), body)
    config.adapter = () => Promise.resolve({
      data: mockData,
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    })
  }

  if (!USE_MOCK) {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

service.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== undefined) {
      if (res.code === 200) {
        return res.data
      }
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  (error) => {
    // 提取后端返回的明细错误信息（FastAPI HTTPException 返回 { detail: "..." }）
    const detail = error.response?.data?.detail || error.response?.data?.message
    const isLoginReq = (error.config?.url || '').includes('/auth/login')

    if (error.response?.status === 401) {
      // 登录接口的 401（用户名/密码错误）只需提示，不应触发登出跳转
      if (!isLoginReq) {
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/#/login'
      }
      ElMessage.error(detail || '登录失败，请检查用户名和密码')
    } else if (error.response?.status === 403) {
      ElMessage.error(detail || '没有操作权限')
    } else {
      ElMessage.error(detail || error.message || '网络异常')
    }
    // 用后端明细信息构造 Error，方便调用方 catch (e) 中读取 e.message
    return Promise.reject(new Error(detail || error.message || '网络异常'))
  }
)

export default service