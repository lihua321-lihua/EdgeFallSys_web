/**
 * 认证状态管理 - 登录/登出、用户信息、角色权限
 *
 * "记住登录" 真正生效：
 *   勾选 remember → token 存 localStorage，跨浏览器重启仍保持登录；
 *   未勾选       → token 存 sessionStorage，关闭浏览器即失效。
 * 另：登录响应中的 must_change_password 用于首次登录/被重置后强制改密。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/utils/request'

const TOKEN_KEY = 'token'

function readToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || ''
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(readToken())
  const userInfo = ref(null)
  const role = ref('')
  const displayName = ref('')
  const mustChangePassword = ref(false)

  const isLoggedIn = computed(() => !!token.value)
  const isVillageRole = computed(() => ['village_grid', 'village_doctor'].includes(role.value))
  const isAdminRole = computed(() => ['admin', 'super_admin'].includes(role.value))

  async function login(username, password, roleHint, remember = false) {
    const res = await request.post('/auth/login', { username, password, roleHint, remember })
    token.value = res.token
    userInfo.value = res.user
    role.value = res.user.role
    displayName.value = res.user.display_name
    mustChangePassword.value = !!res.must_change_password

    // 按 remember 选择持久化位置，并清理另一处存储，避免残留导致"关不掉"登录态
    const persist = remember ? localStorage : sessionStorage
    const stale = remember ? sessionStorage : localStorage
    persist.setItem(TOKEN_KEY, res.token)
    stale.removeItem(TOKEN_KEY)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    role.value = ''
    displayName.value = ''
    mustChangePassword.value = false
    localStorage.removeItem(TOKEN_KEY)
    sessionStorage.removeItem(TOKEN_KEY)
  }

  return {
    token, userInfo, role, displayName, mustChangePassword,
    isLoggedIn, isVillageRole, isAdminRole, login, logout,
  }
})
