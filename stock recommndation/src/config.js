/**
 * Centralized API & WebSocket Configuration
 * Supports Local Development, Render (Docker/Web Service), and Vercel Deployment
 */
export const API = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '')

export function getWsUrl() {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL
  }
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000/ws/feed'
  }
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'ws://localhost:8000/ws/feed'
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/feed`
}

export default API
