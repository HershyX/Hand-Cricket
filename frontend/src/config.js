const backendUrl = import.meta.env.VITE_BACKEND_URL ?? ''

export const config = {
  backendUrl,
}

export function apiUrl(path) {
  return `${backendUrl}${path}`
}

export function wsBaseUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws`
}
