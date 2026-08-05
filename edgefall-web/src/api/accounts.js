/**
 * 账号管理接口 - 获取账号列表、新增、编辑、启用/禁用
 */
import request from '@/utils/request'

export function getAccounts(params) {
  return request.get('/accounts', { params })
}

export function createAccount(data) {
  return request.post('/accounts', data)
}

export function updateAccount(id, data) {
  return request.put(`/accounts/${id}`, data)
}

export function toggleAccountStatus(id, data) {
  return request.patch(`/accounts/${id}/status`, data)
}

/** 密码重置申请列表（待处理） */
export function getResetRequests() {
  return request.get('/accounts/reset-requests')
}

/** 重置指定账号密码为默认初始密码（123456） */
export function resetPassword(id) {
  return request.post(`/accounts/${id}/reset-password`)
}
