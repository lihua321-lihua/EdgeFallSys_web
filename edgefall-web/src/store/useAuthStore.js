/**
 * 认证状态管理 - 登录/登出、用户信息、角色权限
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/utils/request'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)
  const role = ref('')
  const displayName = ref('')

  const isLoggedIn = computed(() => !!token.value)
  const isVillageRole = computed(() => ['village_grid', 'village_doctor'].includes(role.value))
  const isAdminRole = computed(() => ['admin', 'super_admin'].includes(role.value))

  async function login(username, password, roleHint) {
    const res = await request.post('/auth/login', { username, password, roleHint })
    token.value = res.token
    userInfo.value = res.user
    role.value = res.user.role
    displayName.value = res.user.display_name
    localStorage.setItem('token', res.token)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    role.value = ''
    displayName.value = ''
    localStorage.removeItem('token')
  }

  return { token, userInfo, role, displayName, isLoggedIn, isVillageRole, isAdminRole, login, logout }
})
