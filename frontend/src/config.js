export const config = {
  backendUrl: import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000',
  wsUrl: import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws',
}
