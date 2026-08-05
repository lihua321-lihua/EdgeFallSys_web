/**
 * AI 接口 - 告警分类、监控数据、健康报告、流式对话
 *
 * streamChat 用原生 fetch + ReadableStream 接收 SSE（axios 不支持流式），
 * 后端响应头已设 X-Accel-Buffering: no 避免 proxy 缓冲。
 */
import request from '@/utils/request'
import { useAuthStore } from '@/store/useAuthStore'

/** 告警智能分类 */
export function classifyAlert(data) {
  return request.post('/ai/classify-alert', data)
}

/** 大模型服务监控数据（最近调用 + 汇总 + 趋势） */
export function getAiMonitor(days = 7) {
  return request.get('/ai/monitor', { params: { days } })
}

/** 手动为指定老人生成健康报告 */
export function generateHealthReport(elderId) {
  return request.post(`/ai/health-report/${elderId}`)
}

/**
 * 流式对话（SSE）
 * @param {string} message 用户消息
 * @param {Array} history 历史对话 [{role, content}]
 * @param {(text: string) => void} onChunk 每收到一段文本的回调
 * @returns {Promise<void>}
 */
export async function streamChat(message, history = [], onChunk) {
  const baseURL = import.meta.env.VITE_API_BASE_URL
  const authStore = useAuthStore()

  const resp = await fetch(`${baseURL}/ai/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authStore.token}`,
    },
    body: JSON.stringify({ message, history }),
  })

  if (!resp.ok) {
    const detail = await resp.text().catch(() => '')
    throw new Error(detail || `HTTP ${resp.status}`)
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    // SSE 事件以 \n\n 分隔
    const parts = buffer.split('\n\n')
    buffer = parts.pop() // 末尾可能不完整，留到下次
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.replace(/^data:\s*/, '')
      if (payload === '[DONE]') return
      try {
        const obj = JSON.parse(payload)
        if (obj.text) onChunk(obj.text)
      } catch {
        // 忽略非 JSON 帧
      }
    }
  }
}


/** 手动重新生成指定老人本月 AI 月度健康评估（大模型生成，覆盖固定字样） */
export function regenerateMonthlyReport(elderId) {
  return request.post(`/ai/health-report/${elderId}`)
}

// ============ 专业 AI 分析报告（救援简报 / 长期健康分析） ============

/** 生成跌倒救援简报（9 模块 JSON） */
export function generateRescueBriefing(data) {
  return request.post('/ai/rescue-briefing', data)
}

/** 生成长期健康分析报告（10 模块 JSON） */
export function generateHealthAnalysis(data) {
  return request.post('/ai/health-analysis', data)
}

/** 连续两次独立调用：先救援简报再健康分析 */
export function generateFullAnalysis(elderId, data) {
  return request.post(`/ai/full-analysis/${elderId}`, data)
}

/** AI 分析报告列表（按 elder_id / report_type 过滤） */
export function getAiReports(params) {
  return request.get('/ai/reports', { params })
}

/** 报告详情 */
export function getAiReport(reportId) {
  return request.get(`/ai/reports/${reportId}`)
}

/**
 * 下载报告文件（JSON / TXT）
 * 用 a 标签触发浏览器下载，携带 Token
 */
export function downloadAiReport(reportId, format = 'json') {
  const baseURL = import.meta.env.VITE_API_BASE_URL
  const authStore = useAuthStore()
  // fetch 拿 blob 再用 a 标签下载（可携带 Authorization 头）
  return fetch(`${baseURL}/ai/reports/${reportId}/download?format=${format}`, {
    headers: { Authorization: `Bearer ${authStore.token}` },
  }).then(async (resp) => {
    if (!resp.ok) throw new Error(`下载失败: HTTP ${resp.status}`)
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 从响应头取文件名，兜底用 reportId.format
    const disposition = resp.headers.get('content-disposition') || ''
    const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';]+)/)
    a.download = decodeURIComponent(match ? match[1] : `${reportId}.${format}`)
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  })
}
