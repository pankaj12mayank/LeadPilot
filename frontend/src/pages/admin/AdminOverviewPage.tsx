import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { adminGetStats, type AdminWorkspaceStats } from '@/lib/api/admin'

export function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const s = await adminGetStats()
        if (!c) setStats(s)
      } catch {
        if (!c) setErr('Could not load workspace statistics.')
      }
    })()
    return () => {
      c = true
    }
  }, [])

  return (
    <div className="space-y-10">
      <section>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Overview</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-muted">
          Snapshot of the same lead workspace your app users see. Use <strong>Users</strong> for accounts and{' '}
          <strong>Branding</strong> for logo, favicon, and product name shown in the user portal.
        </p>
      </section>

      {err ? <p className="text-sm text-red-600 dark:text-red-400">{err}</p> : null}

      {stats ? (
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Registered users</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.registered_users}</div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Total leads</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.total_leads}</div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Hot leads</div>
            <div className="mt-2 font-display text-3xl font-bold text-amber-700 dark:text-amber-300">{stats.hot_leads}</div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Contacted</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.contacted_leads}</div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Converted</div>
            <div className="mt-2 font-display text-3xl font-bold text-emerald-700 dark:text-emerald-300">{stats.converted_leads}</div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Conversion rate</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.conversion_rate_percent}%</div>
          </div>
        </section>
      ) : !err ? (
        <div className="skeleton-shimmer h-40 max-w-4xl rounded-2xl" />
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/admin/users"
          className="rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card transition hover:border-amber-500/35 dark:bg-premium-card-dark"
        >
          <h2 className="font-display text-lg font-semibold text-ink">Users</h2>
          <p className="mt-2 text-sm text-ink-muted">View registered app accounts and creation dates.</p>
        </Link>
        <Link
          to="/admin/branding"
          className="rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card transition hover:border-amber-500/35 dark:bg-premium-card-dark"
        >
          <h2 className="font-display text-lg font-semibold text-ink">Branding</h2>
          <p className="mt-2 text-sm text-ink-muted">Product name, footer, logo, and favicon for the user portal.</p>
        </Link>
      </section>
    </div>
  )
}
