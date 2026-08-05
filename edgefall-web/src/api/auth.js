/**
 * 认证接口 - 忘记密码、修改密码
 * 登录由 useAuthStore 直接调用（需在登录流程中处理 token 持久化与 must_change_password）
 */
import request from '@/utils/request'

/** 提交忘记密码请求（仅用户名，无邮箱）。后端返回统一引导文案。 */
export function forgotPassword(username) {
  return request.post('/auth/forgot-password', { username })
}

/** 自助修改密码：所有登录用户可用。 */
export function changePassword(oldPassword, newPassword) {
  return request.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}
