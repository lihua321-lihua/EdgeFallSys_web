/**
 * 老人接口 - 获取老人列表、详情、AI健康报告
 */
import request from '@/utils/request'

export function getElders(params) {
  return request.get('/elders', { params })
}

export function getElderDetail(id) {
  return request.get(`/elders/${id}`)
}

export function getElderAiReport(id) {
  return request.get(`/elders/${id}/ai-report`)
}