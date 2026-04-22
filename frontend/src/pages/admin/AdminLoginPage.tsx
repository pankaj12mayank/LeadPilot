import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { PasswordField } from '@/components/ui/PasswordField'
import { adminLogin } from '@/lib/api/admin'
import { useAdminStore } from '@/store/adminStore'

export function AdminLoginPage() {
  const token = useAdminStore((s) => s.token)
  const setToken = useAdminStore((s) => s.setToken)
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (token) {
    return <Navigate to="/admin" replace />
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const data = await adminLogin(email.trim(), password)
      setToken(data.access_token)
      navigate('/admin', { replace: true })
    } catch (e: unknown) {
      const ax = e as { response?: { status?: number; data?: { detail?: unknown } } }
      const st = ax.response?.status
      const d = ax.response?.data?.detail
      const msg =
        typeof d === 'string'
          ? d
          : Array.isArray(d)
            ? d.map((x) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : String(x))).join(' ')
            : null
      if (st === 503) {
        setError(
          msg ||
            'Admin console is off on the server. Add ADMIN_EMAIL and ADMIN_PASSWORD to the LeadPilot project root file `.env` (same folder as `config.py`), then restart the API.',
        )
      } else if (st === 401) {
        setError(msg || 'Email or password does not match the server admin credentials.')
      } else {
        setError(
          msg ||
            'Could not reach the API. Check the server is running and VITE_API_BASE_URL (or dev /api proxy) matches API_ROOT_PATH. Admin vars belong in LeadPilot/.env, not frontend/.env.',
        )
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex h-dvh max-h-dvh min-h-0 flex-col overflow-hidden bg-surface">
      <div className="relative z-10 flex shrink-0 justify-end px-4 pb-1 pt-3 sm:px-8 sm:pt-4">
        <ThemeToggle />
      </div>
      <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-y-auto overscroll-y-contain px-4 pb-4 pt-1 sm:px-6 sm:pb-6">
        <div className="relative my-auto w-full max-w-md shrink-0 rounded-2xl border border-surface-border bg-premium-card-light/95 p-6 shadow-card backdrop-blur-xl dark:bg-premium-card-dark/95 sm:p-8">
        <div className="mb-2 font-display text-xs font-semibold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-300">
          Admin
        </div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Console sign-in</h1>
        <p className="mt-2 text-sm text-ink-muted">
          Uses credentials from the API server configuration (not app user accounts).
        </p>
        <form className="mt-6 space-y-3 sm:mt-8 sm:space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="adm-email">
              Admin email
            </label>
            <input
              id="adm-email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field-input mt-2"
            />
          </div>
          <PasswordField
            id="adm-pw"
            label="Password"
            value={password}
            onChange={setPassword}
            autoComplete="current-password"
            required
          />
          {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? 'Signing in…' : 'Sign in to admin'}
          </button>
        </form>
        </div>
      </div>
    </div>
  )
}
