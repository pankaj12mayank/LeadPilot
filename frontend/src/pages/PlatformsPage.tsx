import { KeyRound, Loader2, Play, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { Modal } from '@/components/ui/Modal'
import {
  fetchScraperStatus,
  openManualLogin,
  verifyAllSessions,
  type ScraperStatus,
} from '@/lib/api/scraper'
import {
  createPlatform,
  deletePlatform,
  listPlatforms,
  patchBuiltinActive,
  patchCustomPlatform,
} from '@/lib/api/platforms'
import { cn } from '@/lib/utils/cn'
import type { PlatformRow } from '@/types/models'

export function PlatformsPage() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<PlatformRow[]>([])
  const [scraper, setScraper] = useState<ScraperStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshBusy, setRefreshBusy] = useState(false)
  const [busySlug, setBusySlug] = useState<string | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [addSlug, setAddSlug] = useState('')
  const [addLabel, setAddLabel] = useState('')
  const [addLoginUrl, setAddLoginUrl] = useState('')
  const [addBusy, setAddBusy] = useState(false)
  const [addErr, setAddErr] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<PlatformRow | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [deleteErr, setDeleteErr] = useState<string | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadErr(null)
    try {
      const [plats, st] = await Promise.all([listPlatforms(), fetchScraperStatus()])
      setRows(plats)
      setScraper(st)
    } catch {
      setLoadErr('Could not load platforms or scraper configuration. Start the API and try again.')
      setRows([])
      setScraper(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function onManualLogin(slug: string) {
    setBusySlug(slug)
    try {
      await openManualLogin(slug, 180)
      await load()
    } catch (e) {
      console.error(e)
    } finally {
      setBusySlug(null)
    }
  }

  async function onRefreshSessions() {
    setRefreshBusy(true)
    try {
      await verifyAllSessions()
      await load()
    } finally {
      setRefreshBusy(false)
    }
  }

  async function onToggleChannel(p: PlatformRow, next: boolean) {
    try {
      if (p.builtin) {
        await patchBuiltinActive(p.slug, next)
      } else if (p.platform_id != null) {
        await patchCustomPlatform(p.platform_id, { active: next })
      }
      await load()
    } catch {
      /* ignore */
    }
  }

  async function onAddPlatform() {
    setAddErr(null)
    const slug = addSlug.trim().toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')
    const label = addLabel.trim()
    const loginUrl = addLoginUrl.trim()
    if (!slug || !label) {
      setAddErr('Enter a short slug (letters, numbers, underscores) and a display name.')
      return
    }
    if (!loginUrl.startsWith('http')) {
      setAddErr('Enter a valid sign-in page URL (https://…) where users log in to this source.')
      return
    }
    setAddBusy(true)
    try {
      await createPlatform({ slug, label, login_url: loginUrl })
      setAddOpen(false)
      setAddSlug('')
      setAddLabel('')
      setAddLoginUrl('')
      await load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setAddErr(err.response?.data?.detail || 'Could not add this platform. Try a different slug.')
    } finally {
      setAddBusy(false)
    }
  }

  async function onConfirmDelete() {
    if (!deleteTarget?.platform_id) return
    setDeleteErr(null)
    setDeleteBusy(true)
    try {
      await deletePlatform(deleteTarget.platform_id)
      setDeleteTarget(null)
      await load()
    } catch {
      setDeleteErr('Could not remove this platform. Try again.')
    } finally {
      setDeleteBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-ink-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading platform configuration
      </div>
    )
  }

  if (loadErr || !scraper) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <ApiLoadError
          title="Platforms unavailable"
          message={loadErr ?? 'Scraper status was not returned. Retry or verify the backend is healthy.'}
          onRetry={() => void load()}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-8">
      <section className="space-y-3">
        <h2 className="type-section-heading">Platform access</h2>
        <p className="max-w-3xl text-sm leading-relaxed text-ink-muted">
          Review connected lead sources, session management state, and scraper limits. Engine{' '}
          <span className="text-ink">{scraper.engine}</span>. Maximum leads per run{' '}
          <span className="text-ink">{scraper.max_leads_cap}</span>. Default delay window{' '}
          <span className="text-ink">
            {scraper.delay_seconds_range[0]} to {scraper.delay_seconds_range[1]} seconds
          </span>
          .
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={refreshBusy}
            onClick={() => void onRefreshSessions()}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-900 transition hover:border-amber-500/50 disabled:opacity-50 dark:text-amber-200"
          >
            {refreshBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            Refresh · verify logins
          </button>
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-4 py-2 text-sm text-ink-muted transition hover:border-amber-500/30 hover:text-ink"
          >
            Reload list
          </button>
        </div>
      </section>

      <section className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-6 dark:border-emerald-500/25 dark:bg-emerald-500/[0.07]">
        <h2 className="type-section-heading mb-2">Safe scraping: how it works</h2>
        <p className="max-w-3xl text-sm leading-relaxed text-ink-muted">
          Lead capture is gated for safety: the browser opens the real channel, you sign in when needed, then automation
          runs with delays and caps from Settings. You stay in control of the session before any bulk scraping.
        </p>
        <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-ink-muted">
          <li>
            <strong className="text-ink">Activate</strong> the source here and use <strong>Connect / manual login</strong>{' '}
            so a real browser window opens that channel.
          </li>
          <li>
            <strong className="text-ink">Log in</strong> in that window (and complete any 2FA). Close it when the app
            shows the session as connected.
          </li>
          <li>
            <strong className="text-ink">Run lead search</strong> from{' '}
            <Link to="/search-leads" className="font-semibold text-amber-800 underline decoration-amber-500/40 underline-offset-2 hover:text-amber-700 dark:text-amber-200 dark:hover:text-amber-100">
              Lead search
            </Link>
            : the same channel opens again, respects your session, then automates capture with safe delays.
          </li>
        </ol>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="type-section-heading mb-0">Connected lead sources</h2>
            <p className="mt-2 max-w-3xl text-xs text-ink-muted">
              Connect a platform session before running scraping activity. Built-in sources cannot be removed; custom
              platforms use the same card layout and support delete after confirmation.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              setAddErr(null)
              setAddSlug('')
              setAddLabel('')
              setAddLoginUrl('')
              setAddOpen(true)
            }}
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm ring-1 ring-amber-500/25 transition hover:from-amber-500 hover:to-amber-600 dark:from-amber-500 dark:to-amber-600"
          >
            <Plus className="h-4 w-4" />
            Add platform
          </button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {rows.map((p) => {
          const loggedIn = !!p.session_connected
          const hasProfile = !!p.session_profile
          const inactive = !p.active
          return (
            <div
              key={p.slug}
              className={cn(
                'flex flex-col rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card transition hover:border-amber-500/20 dark:bg-premium-card-dark dark:hover:border-amber-400/15',
                inactive && 'opacity-60',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-lg font-semibold tracking-tight text-ink">{p.label}</h3>
                  <p className="mt-1 font-mono text-xs text-ink-subtle">{p.slug}</p>
                </div>
                <span
                  className={cn(
                    'shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                    p.active ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'bg-zinc-200 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-500',
                  )}
                >
                  {p.active ? 'Channel on' : 'Channel off'}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between gap-3 rounded-xl border border-surface-border bg-field/40 px-3 py-2.5 dark:bg-zinc-900/30">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-ink">Workspace channel</p>
                  <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">
                    Search, filters, and scraper use enabled channels only.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={p.active}
                  aria-label={p.active ? 'Turn channel off' : 'Turn channel on'}
                  onClick={() => void onToggleChannel(p, !p.active)}
                  className={cn(
                    'relative h-7 w-12 shrink-0 rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50 focus-visible:ring-offset-2 focus-visible:ring-offset-premium-card-light dark:focus-visible:ring-offset-premium-card-dark',
                    p.active ? 'bg-emerald-600' : 'bg-zinc-300 dark:bg-zinc-600',
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 left-0.5 block h-6 w-6 rounded-full bg-white shadow-md ring-1 ring-black/5 transition-transform duration-200 ease-out',
                      p.active ? 'translate-x-5' : 'translate-x-0',
                    )}
                  />
                </button>
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-ink-muted">Login status</dt>
                  <dd
                    className={
                      loggedIn
                        ? 'font-medium text-emerald-700 dark:text-emerald-300'
                        : hasProfile
                          ? 'text-amber-700 dark:text-amber-200'
                          : 'text-ink-muted'
                    }
                  >
                    {loggedIn ? 'Connected' : hasProfile ? 'Profile saved — not verified' : 'Not connected'}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt className="text-ink-muted">Built-in connector</dt>
                  <dd className="text-ink-muted">{p.builtin ? 'Yes' : 'No'}</dd>
                </div>
                {p.login_url ? (
                  <div className="flex flex-col gap-0.5">
                    <dt className="text-ink-muted">Sign-in URL</dt>
                    <dd className="break-all font-mono text-[11px] text-ink-subtle">{p.login_url}</dd>
                  </div>
                ) : null}
              </dl>
              <div className="mt-6 flex flex-col gap-2">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => onManualLogin(p.slug)}
                    disabled={busySlug === p.slug || inactive}
                    className="inline-flex min-h-[40px] min-w-0 flex-1 items-center justify-center gap-2 rounded-xl border border-surface-border bg-field/80 px-3 py-2.5 text-xs font-semibold text-ink transition hover:border-amber-500/30 disabled:opacity-50 dark:bg-zinc-900/50"
                  >
                    {busySlug === p.slug ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <KeyRound className="h-4 w-4 text-amber-700 dark:text-amber-300" />
                    )}
                    Connect Platform
                  </button>
                  <button
                    type="button"
                    disabled={inactive}
                    onClick={() => navigate('/search-leads', { state: { platform: p.slug } })}
                    className="inline-flex min-h-[40px] min-w-0 flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 px-3 py-2.5 text-xs font-semibold text-white shadow-sm ring-1 ring-amber-500/25 transition hover:from-amber-500 hover:to-amber-600 disabled:opacity-50 dark:from-amber-500 dark:to-amber-600"
                  >
                    <Play className="h-4 w-4" />
                    Start Lead Search
                  </button>
                </div>
                {!p.builtin && p.platform_id != null ? (
                  <button
                    type="button"
                    onClick={() => {
                      setDeleteErr(null)
                      setDeleteTarget(p)
                    }}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-red-500/35 bg-red-500/5 px-3 py-2 text-xs font-semibold text-red-800 transition hover:border-red-500/50 hover:bg-red-500/10 dark:text-red-300"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete platform
                  </button>
                ) : null}
              </div>
            </div>
          )
        })}
        </div>
      </section>

      <Modal open={addOpen} title="Add platform" onClose={() => !addBusy && setAddOpen(false)}>
        <div className="space-y-4 text-sm">
          <p className="text-ink-muted">
            Custom platforms appear in this list with the same details as built-in sources. Use a short{' '}
            <span className="text-ink">slug</span> (lowercase, underscores) and a clear label for your team.
          </p>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="add-platform-slug">
              Slug
            </label>
            <input
              id="add-platform-slug"
              value={addSlug}
              onChange={(e) => setAddSlug(e.target.value)}
              className="field-input mt-1 font-mono text-sm"
              placeholder="e.g. custom_directory"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="add-platform-label">
              Display name
            </label>
            <input
              id="add-platform-label"
              value={addLabel}
              onChange={(e) => setAddLabel(e.target.value)}
              className="field-input mt-1"
              placeholder="e.g. Custom Directory"
            />
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="add-platform-login">
              Website sign-in URL
            </label>
            <input
              id="add-platform-login"
              value={addLoginUrl}
              onChange={(e) => setAddLoginUrl(e.target.value)}
              className="field-input mt-1 font-mono text-sm"
              placeholder="https://example.com/login"
              autoComplete="off"
            />
            <p className="mt-1 text-[11px] text-ink-subtle">
              Connect Platform opens this URL so the account can be linked after successful login.
            </p>
          </div>
          {addErr ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-800 dark:text-red-200">
              {addErr}
            </div>
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              disabled={addBusy}
              onClick={() => setAddOpen(false)}
              className="rounded-xl border border-surface-border px-4 py-2 text-sm text-ink-muted transition hover:text-ink disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={addBusy || !addSlug.trim() || !addLabel.trim() || !addLoginUrl.trim()}
              onClick={() => void onAddPlatform()}
              className="btn-primary px-4 py-2 text-sm disabled:opacity-50"
            >
              {addBusy ? 'Saving…' : 'Add platform'}
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={!!deleteTarget}
        title="Remove platform?"
        onClose={() => !deleteBusy && setDeleteTarget(null)}
      >
        <div className="space-y-4 text-sm">
          <p className="text-ink-muted">
            This removes <span className="font-semibold text-ink">{deleteTarget?.label}</span>{' '}
            <span className="font-mono text-xs text-ink-subtle">({deleteTarget?.slug})</span> from your workspace list.
            Existing leads that reference this source are not deleted.
          </p>
          {deleteErr ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-3 py-2 text-xs text-red-800 dark:text-red-200">
              {deleteErr}
            </div>
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              disabled={deleteBusy}
              onClick={() => setDeleteTarget(null)}
              className="rounded-xl border border-surface-border px-4 py-2 text-sm text-ink-muted transition hover:text-ink disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deleteBusy}
              onClick={() => void onConfirmDelete()}
              className="rounded-xl border border-red-500/40 bg-red-500/15 px-4 py-2 text-sm font-semibold text-red-800 transition hover:bg-red-500/25 dark:text-red-200"
            >
              {deleteBusy ? 'Removing…' : 'Delete platform'}
            </button>
          </div>
        </div>
      </Modal>

    </div>
  )
}
