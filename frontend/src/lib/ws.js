const RECONNECT_BASE_MS = 800
const RECONNECT_MAX_MS = 8000

export function createSocket(url) {
  let ws = null
  let closedByClient = false
  let reconnectTimer = null
  let attempt = 0
  const listeners = new Set()

  function emit(event, payload) {
    for (const listener of Array.from(listeners)) {
      try {
        listener(event, payload)
      } catch {
        // a listener must never break the socket loop
      }
    }
  }

  function connect() {
    let socket
    try {
      socket = new WebSocket(url)
    } catch {
      emit('close', { clean: closedByClient })
      return
    }
    ws = socket

    socket.onopen = () => {
      attempt = 0
      emit('open')
    }

    socket.onmessage = (event) => {
      let message
      try {
        message = JSON.parse(event.data)
      } catch {
        return
      }
      emit('message', message)
    }

    socket.onerror = () => {
      // onclose always follows; nothing to do here
    }

    socket.onclose = () => {
      ws = null
      emit('close', { clean: closedByClient })
      if (!closedByClient && !reconnectTimer) {
        const delay = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS)
        attempt += 1
        reconnectTimer = window.setTimeout(() => {
          reconnectTimer = null
          connect()
        }, delay)
      }
    }
  }

  connect()

  return {
    get readyState() {
      return ws ? ws.readyState : WebSocket.CLOSED
    },
    get isClosedByClient() {
      return closedByClient
    },
    send(type, payload = {}) {
      if (!ws || ws.readyState !== WebSocket.OPEN) return false
      ws.send(JSON.stringify({ type, ...payload }))
      return true
    },
    on(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    close() {
      closedByClient = true
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (ws) {
        ws.onclose = null
        try {
          ws.close()
        } catch {
          // already closed
        }
      }
      ws = null
    },
  }
}
