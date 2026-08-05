/**
 * 走访任务接口 - 获取任务列表、提交走访反馈
 */
import request from '@/utils/request'

export function getVisitTasks(params) {
  return request.get('/tasks/visits', { params })
}

export function submitTaskFeedback(taskId, data) {
  return request.post(`/tasks/visits/${taskId}/feedback`, data)
}