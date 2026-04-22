import { getApiBaseURL } from '@/lib/api/client'

/**
 * Static branding files are served at ``/branding/*`` on the API host root, not under ``/api``.
 * In dev, Vite proxies ``/branding`` to the backend (see vite.config.ts).
 */
export function resolveMediaUrl(pathOrUrl: string): string {
  const u = (pathOrUrl || '').trim()
  if (!u) return ''
  if (u.startsWith('http://') || u.startsWith('https://')) return u

  const path = u.startsWith('/') ? u : `/${u}`

  if (path.startsWith('/branding')) {
    const base = getApiBaseURL().replace(/\/$/, '')
    if (base.startsWith('http')) {
      try {
        const parsed = new URL(base)
        return `${parsed.origin}${path}`
      } catch {
        return path
      }
    }
    if (typeof window !== 'undefined') {
      return `${window.location.origin}${path}`
    }
    return path
  }

  const base = getApiBaseURL().replace(/\/$/, '')
  return `${base}${path}`
}
