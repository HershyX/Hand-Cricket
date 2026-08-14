import { apiUrl } from '../config'

export class ApiError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(apiUrl(path), {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch {
    throw new ApiError('NETWORK', 'Cannot reach the game server. Is it running?')
  }

  if (!response.ok) {
    let detail = null
    try {
      detail = await response.json()
    } catch {
      detail = null
    }
    const code = detail?.detail?.code ?? 'HTTP_ERROR'
    const message = detail?.detail?.message ?? `Request failed (${response.status})`
    throw new ApiError(code, message)
  }

  return response.json()
}

export function createRoom(hostName) {
  return request('/rooms', {
    method: 'POST',
    body: JSON.stringify({ host_name: hostName }),
  })
}

export function joinRoom(roomCode, playerName) {
  return request(`/rooms/${encodeURIComponent(roomCode)}/join`, {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName }),
  })
}
