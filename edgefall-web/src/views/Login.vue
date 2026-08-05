<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <AppLogo :size="64" class="login-logo" />
        <h1>EdgeFall 养老守护系统</h1>
        <p>边缘智能 · 守护银龄</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>

        <div class="login-options">
          <el-checkbox v-model="rememberMe">记住登录</el-checkbox>
          <a class="forgot-link" @click="showResetDialog = true">忘记密码</a>
        </div>

        <el-form-item label="身份选择（需与账号实际角色一致）">
          <el-radio-group v-model="form.roleHint" class="role-group">
            <el-radio-button value="village_grid">村级网格员</el-radio-button>
            <el-radio-button value="village_doctor">村医</el-radio-button>
            <el-radio-button value="admin">管理员</el-radio-button>
            <el-radio-button value="super_admin">超级管理员</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" style="width:100%" @click="handleLogin"
            :loading="loading">
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>

  <!-- 忘记密码弹窗 -->
  <el-dialog v-model="showResetDialog" title="找回密码" width="420px" :close-on-click-modal="false">
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input v-model="resetForm.username" placeholder="请输入用户名" />
      </el-form-item>
    </el-form>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="账号由管理员统一分配，暂不支持邮箱自助找回。"
      description="请提交重置请求并联系管理员在「组织架构」中重置密码，重置后初始密码为 123456，登录后请及时修改。"
    />
    <template #footer>
      <el-button @click="showResetDialog = false">取消</el-button>
      <el-button type="primary" @click="handleResetPassword" :loading="resetLoading">提交重置请求</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * 登录页 - 表单校验、角色登录、记住登录状态、忘记密码
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/useAuthStore'
import { ElMessage } from 'element-plus'
import AppLogo from '@/components/AppLogo.vue'
import { forgotPassword } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const rememberMe = ref(false)
const showResetDialog = ref(false)
const resetLoading = ref(false)

const resetForm = reactive({ username: '' })

const form = reactive({
  username: '',
  password: '',
  roleHint: 'village_grid',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 读取本地保存的登录凭证
onMounted(() => {
  const saved = localStorage.getItem('edgefall_remember')
  if (saved) {
    try {
      const data = JSON.parse(saved)
      form.username = data.username || ''
      form.roleHint = data.roleHint || 'village_grid'
      rememberMe.value = true
    } catch (e) { /* ignore */ }
  }
})

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    // remember 传入 store：勾选→token 存 localStorage（跨浏览器重启），
    // 未勾选→token 存 sessionStorage（关闭浏览器即失效）
    await authStore.login(form.username, form.password, form.roleHint, rememberMe.value)

    // 记住登录：仅保存用户名/角色用于下次预填（token 持久化已由 store 按 remember 处理）
    if (rememberMe.value) {
      localStorage.setItem('edgefall_remember', JSON.stringify({
        username: form.username,
        roleHint: form.roleHint,
      }))
    } else {
      localStorage.removeItem('edgefall_remember')
    }

    // 首次登录 / 密码被管理员重置后，强制跳转修改密码页
    if (authStore.mustChangePassword) {
      ElMessage.warning('首次登录或密码已被重置，请先修改密码')
      router.push('/change-password')
      return
    }

    const role = authStore.role
    // P0: 按角色跳转到对应端
    if (role === 'admin' || role === 'super_admin') {
      router.push('/admin/dashboard')
    } else if (role === 'village_doctor') {
      router.push('/doctor/alert-board')
    } else {
      // village_grid 默认
      router.push('/grid/alert-board')
    }
    ElMessage.success(`欢迎，${authStore.displayName}`)
  } catch (e) {
    // 错误提示统一由 request.js 拦截器处理（含角色不符、密码错误等明细）
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  if (!resetForm.username) {
    ElMessage.warning('请输入用户名')
    return
  }
  resetLoading.value = true
  try {
    const res = await forgotPassword(resetForm.username)
    ElMessage.success(res.message || '重置请求已提交，请联系管理员处理')
    showResetDialog.value = false
    resetForm.username = ''
  } catch (e) {
    // 错误提示由 request.js 拦截器统一处理
  } finally {
    resetLoading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #e8f4f8 0%, #f0f7ff 100%);
}
.login-card {
  width: 420px;
  padding: 40px;
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-logo {
  margin-bottom: 12px;
}
.login-header h1 {
  font-size: 24px;
  color: var(--color-primary);
  margin: 0 0 8px;
}
.login-header p {
  font-size: 14px;
  color: var(--color-text-light);
  margin: 0;
}
.role-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.forgot-link {
  color: var(--color-primary);
  font-size: 14px;
  cursor: pointer;
  text-decoration: none;
}
.forgot-link:hover {
  text-decoration: underline;
}
</style>