type EventHandler = (data: unknown) => void

class SocketService {
  private ws: WebSocket | null = null
  private handlers = new Map<string, EventHandler[]>()
  private connected = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private collection = ''
  private token = ''

  connect(collection: string, token: string) {
    this.collection = collection
    this.token = token
    this.reconnectAttempts = 0
    this._connect()
  }

  private _connect() {
    if (this.ws) this.disconnect()
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    // TODO: use a dedicated short-lived WS auth token instead of main JWT
    const shortToken = this.token || ''
    const url = `${proto}://${host}/ws/${this.collection}?token=${shortToken}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.connected = true
      this.reconnectAttempts = 0
      this.emit('_connected', null)
    }

    this.ws.onclose = () => {
      this.connected = false
      this.ws = null
      this.emit('_disconnected', null)
      this._scheduleReconnect()
    }

    this.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.event === 'pong') return
        this.emit(msg.event, msg.data)
        this.emit('*', msg)
      } catch {
        // ignore parse errors
      }
    }

    this.ws.onerror = () => {
      this.connected = false
      this.emit('_error', null)
    }
  }

  private _scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return
    this.reconnectAttempts++
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)
    this.reconnectTimer = setTimeout(() => this._connect(), delay)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = this.maxReconnectAttempts
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.connected = false
  }

  on(event: string, handler: EventHandler) {
    if (!this.handlers.has(event)) this.handlers.set(event, [])
    this.handlers.get(event)!.push(handler)
    return () => {
      const handlers = this.handlers.get(event)
      if (handlers) {
        const idx = handlers.indexOf(handler)
        if (idx >= 0) handlers.splice(idx, 1)
      }
    }
  }

  private emit(event: string, data: unknown) {
    const handlers = this.handlers.get(event) || []
    for (const h of handlers) h(data)
  }
}

export const socket = new SocketService()
