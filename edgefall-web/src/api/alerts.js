/**
 * 告警接口 - 获取告警列表、处理告警工单
 */
import request from '@/utils/request'

export function getAlerts(params) {
  return request.get('/alerts', { params })
}

export function resolveAlert(eventId, data) {
  return request.post(`/alerts/${eventId}/resolve`, data)
}