/**
 * 设备接口 - 获取设备列表、设备换绑、API用量查询
 */
import request from '@/utils/request'

export function getDevices(params) {
  return request.get('/devices', { params })
}

export function rebindDevice(data) {
  return request.post('/devices/rebind', data)
}

export function getApiUsage() {
  return request.get('/system/api-usage')
}