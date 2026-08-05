<template>
  <div class="change-password-page">
    <div class="change-password-card">
      <h2>修改密码</h2>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password prefix-icon="Lock"
            placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码（至少6位）" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password prefix-icon="Lock"
            placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm">
          <el-input v-model="form.confirm" type="password" show-password prefix-icon="Lock"
            placeholder="请再次输入新密码" @keyup.enter="handleSubmit" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width:100%" :loading="loading" @click="handleSubmit">
            确认修改
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
/**
 * 修改密码页 - 所有登录用户可用（网格员/村医/管理员/超管）
 * 场景1：首次登录或被管理员重置后强制改密（mustChangePassword=true）
 * 场景2：用户主动在顶栏点"修改密码"自助修改
 */
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/store/useAuthStore'
import { changePassword } from '@/api/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({ old_password: '', new_password: '', confirm: '' })

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== form.new_password) callback(new Error('两次输入的密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

function roleHome() {
  const role = authStore.role
  if (role === 'admin' || role === 'super_admin') return '/admin/dashboard'
  if (role === 'village_doctor') return '/doctor/alert-board'
  return '/grid/alert-board'
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const wasForced = authStore.mustChangePassword
    await changePassword(form.old_password, form.new_password)
    authStore.mustChangePassword = false
    ElMessage.success('密码修改成功')
    // 被强制改密 → 跳回对应端首页；主动改密 → 返回上一页
    if (wasForced) {
      router.push(roleHome())
    } else {
      router.back()
    }
  } catch (e) {
    // 错误由 request.js 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.change-password-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-bg);
}
.change-password-card {
  width: 420px;
  padding: 40px;
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-modal);
}
.change-password-card h2 {
  text-align: center;
  color: var(--color-primary);
  margin: 0 0 28px;
  font-size: 22px;
}
</style>
