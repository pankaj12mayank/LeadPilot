import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { PasswordField } from '@/components/ui/PasswordField'
import { useBrandingStore } from '@/store/brandingStore'
import { fetchMe, login, register } from '@/lib/api/auth'
import { getApiErrorMessage } from '@/lib/api/client'
import { useAuthStore } from '@/store/authStore'

/** Shown under the heading (compact for small viewports). */
const LOGIN_DESC_VISIBLE =
  'Sign in to manage leads, outreach, and analytics from one workspace.'
const REGISTER_DESC_VISIBLE =
  'Create your workspace for prospecting, outreach, and pipeline in one place.'
/** Used for ``<meta name="description">`` only. */
const LOGIN_DESC_META =
  'Sign in to manage leads, track outreach activity, review sales analytics, and organize your sales pipeline from one lead management workspace.'
const REGISTER_DESC_META =
  'Create your workspace to manage prospecting, lead scoring, outreach tracking, and sales performance in a single CRM platform.'

export function LoginPage() {
  const { token, setAuth } = useAuthStore()
  const productName = useBrandingStore((s) => s.branding.product_name)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    try {
      const n = sessionStorage.getItem('leadpilot_auth_notice')
      if (n) {
        setError(n)
        sessionStorage.removeItem('leadpilot_auth_notice')
      }
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    const pageTitle = mode === 'login' ? 'Sign In' : 'Create Account'
    document.title = `${pageTitle} | ${productName}`
    const el = document.querySelector('meta[name="description"]')
    if (el) {
      el.setAttribute('content', mode === 'login' ? LOGIN_DESC_META : REGISTER_DESC_META)
    }
  }, [mode, productName])

  if (token) {
    return <Navigate to="/dashboard" replace />
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match. Re-enter your password and confirmation.')
      return
    }
    setBusy(true)
    try {
      const data =
        mode === 'login'
          ? await login(email.trim(), password)
          : await register(email.trim(), password)
      const user = data.user ?? (await fetchMe())
      setAuth(data.access_token, user)
    } catch (e) {
      const hint = getApiErrorMessage(
        e,
        mode === 'login'
          ? 'Sign-in failed. Check your email and password, then try again.'
          : 'Registration could not be completed. Verify your details or contact your administrator.',
      )
      setError(hint)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative flex h-dvh max-h-dvh min-h-0 flex-col overflow-hidden bg-surface">
      <div className="pointer-events-none absolute -left-32 top-1/4 h-72 w-72 rounded-full bg-amber-500/15 blur-[100px] dark:bg-amber-400/10 sm:h-96 sm:w-96 sm:blur-[120px]" />
      <div className="pointer-events-none absolute -right-20 bottom-0 h-64 w-64 rounded-full bg-emerald-600/10 blur-[80px] dark:bg-emerald-500/10 sm:h-80 sm:w-80 sm:blur-[100px]" />

      <div className="relative z-10 flex shrink-0 justify-end px-4 pb-1 pt-3 sm:px-8 sm:pt-4">
        <ThemeToggle />
      </div>

      <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-y-auto overscroll-y-contain px-4 pb-4 pt-1 sm:px-6 sm:pb-6">
        <div className="relative my-auto w-full max-w-md shrink-0 rounded-2xl border border-surface-border bg-premium-card-light/95 p-6 shadow-glow backdrop-blur-xl dark:bg-premium-card-dark/95 sm:p-8">
        <div className="mb-1.5 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-700 dark:text-amber-300 sm:mb-2 sm:text-xs">
          {productName}
        </div>
        <h1 className="font-display text-2xl font-bold tracking-display-tight text-ink sm:text-3xl">
          {mode === 'login' ? 'Access your lead workspace' : 'Create your account'}
        </h1>
        <p className="mt-2 text-sm leading-snug text-ink-muted sm:mt-3 sm:text-base sm:leading-relaxed">
          {mode === 'login' ? LOGIN_DESC_VISIBLE : REGISTER_DESC_VISIBLE}
        </p>

        <div className="mt-5 flex gap-1 rounded-xl border border-surface-border bg-field/80 p-1 dark:bg-zinc-900/50 sm:mt-6">
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-200 sm:py-2.5 ${
              mode === 'login'
                ? 'bg-gradient-to-r from-amber-600 via-amber-500 to-amber-700 text-white shadow-md ring-1 ring-amber-500/35 dark:from-amber-500 dark:via-amber-400 dark:to-amber-600 dark:shadow-glow-gold'
                : 'text-ink-muted hover:text-ink'
            }`}
            onClick={() => {
              setMode('login')
              setError(null)
              setConfirmPassword('')
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-200 sm:py-2.5 ${
              mode === 'register'
                ? 'bg-gradient-to-r from-amber-600 via-amber-500 to-amber-700 text-white shadow-md ring-1 ring-amber-500/35 dark:from-amber-500 dark:via-amber-400 dark:to-amber-600 dark:shadow-glow-gold'
                : 'text-ink-muted hover:text-ink'
            }`}
            onClick={() => {
              setMode('register')
              setError(null)
              setConfirmPassword('')
            }}
          >
            Create Account
          </button>
        </div>

        <form className="mt-5 space-y-3 sm:mt-6 sm:space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="email">
              Work email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field-input mt-2"
            />
          </div>
          <div>
            <PasswordField
              id="password"
              label="Password"
              value={password}
              onChange={setPassword}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              required
              minLength={6}
            />
            {mode === 'login' ? (
              <p className="mt-1.5 text-[11px] leading-snug text-ink-subtle sm:mt-2 sm:text-xs">
                Forgot your password? Contact your workspace administrator.
              </p>
            ) : null}
          </div>
          {mode === 'register' ? (
            <PasswordField
              id="confirm"
              label="Confirm password"
              value={confirmPassword}
              onChange={setConfirmPassword}
              autoComplete="new-password"
              required
              minLength={6}
            />
          ) : null}
          {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
          <button type="submit" disabled={busy} className="btn-primary w-full">
            {busy ? 'Please wait' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-ink-muted sm:mt-5">
          {mode === 'login' ? (
            <>
              Need an account?{' '}
              <button
                type="button"
                className="font-medium text-amber-800 underline-offset-4 hover:underline dark:text-amber-300"
                onClick={() => {
                  setMode('register')
                  setError(null)
                  setConfirmPassword('')
                }}
              >
                Create Account
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                className="font-medium text-amber-800 underline-offset-4 hover:underline dark:text-amber-300"
                onClick={() => {
                  setMode('login')
                  setError(null)
                  setConfirmPassword('')
                }}
              >
                Sign In
              </button>
            </>
          )}
        </p>

        </div>
      </div>
    </div>
  )
}
