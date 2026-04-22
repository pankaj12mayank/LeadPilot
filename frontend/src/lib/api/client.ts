import axios, { type AxiosError } from 'axios'

import { useAuthStore } from '@/store/authStore'

/**
 * Resolved browser base URL for the LeadPilot JSON API (includes ``/api`` when that is the server prefix).
 *
 * **Local dev (recommended):** leave both env vars unset → baseURL is ``/api`` and Vite proxies to the backend.
 *
 * **Direct to FastAPI:** ``VITE_API_BASE_URL=http://localhost:8000/api`` (or legacy ``VITE_API_URL``).
 *
 * @example
 * // .env.local — browser talks to FastAPI on another origin (set CORS + FRONTEND_URL on the server)
 * VITE_API_BASE_URL=http://localhost:8000/api
 *
 * @example
 * // Axios usage elsewhere (paths omit the shared prefix; it is added by baseURL)
 * await api.post('/auth/login', { email, password })
 * await api.get('/leads', { params: { page: 1 } })
 */
function normalizeConfiguredApiBase(raw: string): string {
  let u = raw.trim().replace(/\/$/, '')
  if (!u) return u
  if (u.startsWith('/')) return u
  if (!/^https?:\/\//i.test(u)) return u
  try {
    const parsed = new URL(u)
    const path = (parsed.pathname || '').replace(/\/$/, '') || '/'
    if (path === '/') {
      return `${parsed.origin}/api`
    }
  } catch {
    /* ignore */
  }
  return u
}

export function getApiBaseURL(): string {
  const a = String(import.meta.env.VITE_API_BASE_URL ?? '')
    .trim()
    .replace(/\/$/, '')
  const b = String(import.meta.env.VITE_API_URL ?? '')
    .trim()
    .replace(/\/$/, '')
  const fromEnv = normalizeConfiguredApiBase(a || b)
  if (fromEnv) return fromEnv
  if (import.meta.env.DEV) return '/api'
  return 'http://127.0.0.1:8000/api'
}

/** FastAPI ``HTTPException`` / validation error payload → short user-facing string. */
export function getApiErrorMessage(err: unknown, fallback = 'Request failed'): string {
  const ax = err as AxiosError<{ detail?: unknown }>
  const status = ax.response?.status
  const d = ax.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    const first = d[0] as { msg?: string } | undefined
    if (first && typeof first.msg === 'string') return first.msg
  }
  if (d && typeof d === 'object' && 'message' in d && typeof (d as { message?: string }).message === 'string') {
    return (d as { message: string }).message
  }
  if (ax.code === 'ECONNABORTED') return 'Request timed out. Try again.'
  if (ax.message === 'Network Error' || !status) {
    return 'Network error — check that the API is running and CORS allows this origin.'
  }
  return fallback
}

export const api = axios.create({
  baseURL: getApiBaseURL(),
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const t = useAuthStore.getState().token
  if (t) {
    config.headers.Authorization = `Bearer ${t}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      if (window.location.pathname.startsWith('/admin')) {
        return Promise.reject(err)
      }
      useAuthStore.getState().logout()
      if (!window.location.pathname.startsWith('/login')) {
        try {
          sessionStorage.setItem(
            'leadpilot_auth_notice',
            'Session expired. Please sign in again to continue.',
          )
        } catch {
          /* ignore */
        }
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)
