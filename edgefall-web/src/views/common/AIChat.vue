<template>
  <div class="page-ai-chat">
    <div class="chat-header">
      <h2 class="page-title">🤖 AI 助手</h2>
      <el-tag v-if="!configured" type="info" size="small">大模型未配置，回复为降级文本</el-tag>
      <el-tag v-else type="success" size="small">已接入 Qwen</el-tag>
    </div>

    <div class="chat-container">
      <div class="chat-messages" ref="messagesRef">
        <div v-for="(msg, idx) in messages" :key="idx" :class="['msg', msg.role]">
          <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="msg-bubble">{{ msg.content }}<span v-if="loading && idx === messages.length - 1 && msg.role === 'assistant'" class="cursor">▋</span></div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          :disabled="loading"
          placeholder="输入消息，Ctrl+Enter 发送"
          @keydown.ctrl.enter="send"
          resize="none"
        />
        <el-button type="primary" :loading="loading" :disabled="!input.trim()" @click="send">
          {{ loading ? '生成中' : '发送' }}
        </el-button>
      </div>

      <div class="chat-tips">
        <span>{{ roleTips }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * AI 助手 - 流式对话页（四端共享）
 * 用 streamChat 接收 SSE，逐字追加到助手消息气泡。
 * 欢迎语按当前登录角色定制，体现该端对应功能。
 */
import { ref, reactive, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { streamChat, getAiMonitor } from '@/api/ai'
import { useAuthStore } from '@/store/useAuthStore'

const authStore = useAuthStore()

// 按角色定制欢迎介绍，对应各端核心功能
const ROLE_INTRO = {
  village_grid: '您好，我是网格员 AI 助手。您可以询问告警现场处置建议、走访任务处理流程、老人基本信息等，我会尽力解答。',
  village_doctor: '您好，我是村医 AI 助手。您可以询问老人健康状况、医疗判断建议、随访任务、健康报告解读等，我会尽力解答。',
  admin: '您好，我是管理员 AI 助手。您可以询问设备管理、组织架构、告警统计、API 监控等管理问题，我会尽力解答。',
  super_admin: '您好，我是超级管理员 AI 助手。您可以询问系统与账号管理、全村庄数据审计、告警统计等，我会尽力解答。',
}
const roleIntro = ROLE_INTRO[authStore.role] || ROLE_INTRO.admin

// 按角色定制底部「可问」提示，对应各端核心功能
const ROLE_TIPS = {
  village_grid: '💡 可问：告警现场如何处置 / 走访任务处理流程 / 老人基本信息查询',
  village_doctor: '💡 可问：本月哪位老人风险较高 / 告警处置流程 / 健康报告解读',
  admin: '💡 可问：设备在线情况 / 组织架构与账号管理 / 近期告警统计',
  super_admin: '💡 可问：账号管理 / 全村庄数据审计 / 告警统计与系统运行情况',
}
const roleTips = ROLE_TIPS[authStore.role] || ROLE_TIPS.admin

const messages = ref([
  { role: 'assistant', content: roleIntro },
])
const input = ref('')
const loading = ref(false)
const configured = ref(true)
const messagesRef = ref(null)

onMounted(async () => {
  // 通过监控接口探测大模型是否已配置
  try {
    const res = await getAiMonitor(1)
    configured.value = !!res?.summary?.qwen_configured
  } catch {
    configured.value = false
  }
})

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true

  const assistantMsg = reactive({ role: 'assistant', content: '' })
  messages.value.push(assistantMsg)
  await scrollToBottom()

  try {
    // 历史对话（排除首条欢迎语和刚加入的空助手消息）
    const history = messages.value
      .slice(1, -2)
      .map(m => ({ role: m.role, content: m.content }))
      .filter(m => m.content)

    await streamChat(text, history, (chunk) => {
      assistantMsg.content += chunk
      scrollToBottom()
    })

    if (!assistantMsg.content) {
      assistantMsg.content = '（无回复内容）'
    }
  } catch (e) {
    assistantMsg.content = `调用失败：${e.message || '网络异常'}`
    ElMessage.error('对话失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}
</script>

<style scoped>
.page-ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.page-title {
  font-size: var(--font-size-title);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  min-height: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.msg {
  display: flex;
  gap: var(--spacing-sm);
  max-width: 80%;
}

.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.msg-avatar {
  font-size: 20px;
  flex-shrink: 0;
}

.msg-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: var(--font-size-base);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg.assistant .msg-bubble {
  background: var(--color-bg, #f5f7fa);
  color: var(--color-text);
  border-top-left-radius: 4px;
}

.msg.user .msg-bubble {
  background: var(--color-primary);
  color: #fff;
  border-top-right-radius: 4px;
}

.cursor {
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

.chat-input {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  align-items: flex-end;
}

.chat-tips {
  padding: 0 var(--spacing-lg) var(--spacing-sm);
  font-size: 12px;
  color: var(--color-text-light);
}
</style>
