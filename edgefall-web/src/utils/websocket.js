/**
 * WebSocket 客户端 - 心跳保活、断线重连、消息分发
 */
class WebSocketClient {
  constructor() {
    this.ws = null
    this.token = ''
    this.heartbeatTimer = null
    this.reconnectTimer = null
    this.reconnectCount = 0
    this.maxReconnect = 10
    this.listeners = {}
    this.isManualClose = false
  }

  connect(token) {
    this.isManualClose = false
    this.token = token
    this.reconnectCount = 0
    const url = `${import.meta.env.VITE_WS_URL}?token=${token}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WS] 连接成功')
      this.reconnectCount = 0
      this._startHeartbeat()
    }

    this.ws.onclose = (event) => {
      this._stopHeartbeat()
      if (event.code === 4001) {
        console.warn('[WS] Token 已过期，跳转登录页')
        localStorage.removeItem('token')
        window.location.href = '/#/login'
        return
      }
      if (!this.isManualClose) {
        this._reconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] 连接错误:', error)
    }

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        this._dispatch(message.type, message)
      } catch (e) {
        console.error('[WS] 消息解析失败:', e)
      }
    }
  }

  disconnect() {
    this.isManualClose = true
    this._stopHeartbeat()
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  on(type, callback) {
    if (!this.listeners[type]) {
      this.listeners[type] = []
    }
    this.listeners[type].push(callback)
  }

  off(type, callback) {
    if (!this.listeners[type]) return
    this.listeners[type] = this.listeners[type].filter(fn => fn !== callback)
  }

  _dispatch(type, data) {
    const callbacks = this.listeners[type] || []
    callbacks.forEach(fn => fn(data))
  }

  _startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'PING' }))
      }
    }, 30000)
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  _reconnect() {
    if (this.reconnectCount >= this.maxReconnect) {
      console.error('[WS] 重连次数已达上限')
      return
    }

    this.reconnectCount++
    const delay = Math.min(Math.pow(2, this.reconnectCount - 1) * 1000, 30000)
    this.reconnectTimer = setTimeout(() => {
      console.log(`[WS] 第 ${this.reconnectCount} 次重连...`)
      this.connect(this.token)
    }, delay)
  }
}

export default new WebSocketClient()
