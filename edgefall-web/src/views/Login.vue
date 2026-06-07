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

        <el-form-item label="身份选择（仅提示，实际权限由系统判定）">
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
  <el-dialog v-model="showResetDialog" title="找回密码" width="400px" :close-on-click-modal="false">
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input v-model="resetForm.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="联系邮箱">
        <el-input v-model="resetForm.email" placeholder="请输入注册时绑定的邮箱" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showResetDialog = false">取消</el-button>
      <el-button type="primary" @click="handleResetPassword" :loading="resetLoading">提交重置</el-button>
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

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)
const rememberMe = ref(false)
const showResetDialog = ref(false)
const resetLoading = ref(false)

const resetForm = reactive({ username: '', email: '' })

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
    await authStore.login(form.username, form.password, form.roleHint)

    // 记住登录状态
    if (rememberMe.value) {
      localStorage.setItem('edgefall_remember', JSON.stringify({
        username: form.username,
        roleHint: form.roleHint,
      }))
    } else {
      localStorage.removeItem('edgefall_remember')
    }

    const role = authStore.role
    if (['admin', 'super_admin'].includes(role)) {
      router.push('/admin/dashboard')
    } else {
      router.push('/village/alert-board')
    }
    ElMessage.success(`欢迎，${authStore.displayName}`)
  } catch (e) {
    ElMessage.error(e.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  if (!resetForm.username || !resetForm.email) {
    ElMessage.warning('请填写用户名和邮箱')
    return
  }
  resetLoading.value = true
  try {
    // Mock 环境：模拟提交成功
    await new Promise(resolve => setTimeout(resolve, 800))
    ElMessage.success('重置链接已发送至您的邮箱，请查收')
    showResetDialog.value = false
    resetForm.username = ''
    resetForm.email = ''
  } catch (e) {
    ElMessage.error('提交失败，请重试')
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