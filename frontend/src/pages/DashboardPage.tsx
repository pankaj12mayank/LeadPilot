import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { UsageBar } from '@/components/UsageBar'

import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { fetchDashboard } from '@/lib/api/analytics'
import { getHighScoreThreshold } from '@/lib/config/userConfigRules'
import { cn } from '@/lib/utils/cn'
import { useUserConfigStore } from '@/store/userConfigStore'
import type { DashboardData } from '@/types/models'

export function DashboardPage() {
  const adminConfig = useUserConfigStore((s) => s.adminConfig)
  const highScoreThreshold = getHighScoreThreshold(adminConfig)
  const [dash, setDash] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)
  const [sub, setSub] = useState<any>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    ;(async () => {
      try {
        const d = await fetchDashboard()
        if (!cancelled) setDash(d)
      } catch {
        if (!cancelled) {
          setDash(null)
          setLoadError('Dashboard could not load. Ensure the API is running.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [retryNonce])

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('/api/user/subscription', {
          headers: { Authorization: `Bearer ${sessionStorage.getItem('li_token') || ''}` },
        })
        if (res.ok) { const j = await res.json(); if (j.has_subscription) setSub(j.subscription) }
      } catch { /* ignore */ }
    })()
  }, [])

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-zinc-200 dark:bg-zinc-800" />
          ))}
        </div>
        <div className="h-48 animate-pulse rounded-xl bg-zinc-200 dark:bg-zinc-800" />
      </div>
    )
  }

  if (loadError || !dash) {
    return (
      <ApiLoadError
        title="Dashboard unavailable"
        message={loadError ?? 'No data returned.'}
        onRetry={() => setRetryNonce((n) => n + 1)}
      />
    )
  }

  const totalLeads = dash.total_leads ?? dash.total ?? 0
  const hotLeads = dash.hot_leads ?? 0
  const newLeads = dash.new_leads ?? Number(dash.status_distribution?.new ?? dash.by_status?.new ?? 0)
  const convRate = dash.conversion_rate_percent ?? 0

  const stats = [
    { label: 'Total Leads', value: totalLeads.toLocaleString(), color: 'bg-blue-500/10 text-blue-700 dark:text-blue-300' },
    { label: 'Hot Leads', value: hotLeads.toLocaleString(), color: 'bg-rose-500/10 text-rose-700 dark:text-rose-300' },
    { label: 'New Leads', value: newLeads.toLocaleString(), color: 'bg-violet-500/10 text-violet-700 dark:text-violet-300' },
    { label: 'Conversion Rate', value: `${convRate}%`, color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{s.label}</span>
              <span className={cn('rounded-md px-2 py-1 text-xs font-semibold', s.color)}>
                {s.value}
              </span>
            </div>
          </div>
        ))}
      </div>

      {sub ? (
        <div className="rounded-xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="font-semibold text-zinc-900 dark:text-white">{sub.plan_name || 'Free'} Plan</h2>
              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                Status: <span className="font-medium text-emerald-600 dark:text-emerald-400">{sub.status}</span>
                {sub.period_end ? ` · Renews ${new Date(sub.period_end).toLocaleDateString()}` : ''}
              </p>
              <div className="mt-3">
                <UsageBar used={sub.leads_consumed || 0} limit={sub.lead_limit || 0} label="Leads used" />
              </div>
            </div>
            {sub.leads_consumed >= sub.lead_limit && sub.lead_limit > 0 && (
              <Link to="/pricing" className="shrink-0 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700">
                Upgrade
              </Link>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
            <span>{sub.period_start ? `Period: ${new Date(sub.period_start).toLocaleDateString()}` : ''}</span>
            <Link to="/user/transactions" className="text-amber-600 hover:underline dark:text-amber-400">View Transactions</Link>
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
        <h2 className="mb-1 text-base font-semibold text-zinc-900 dark:text-white">System Overview</h2>
        <p className="mb-4 text-sm text-zinc-500">Current workspace status at a glance.</p>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-surface-border bg-zinc-50 p-4 dark:bg-zinc-800/50">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Hot Threshold</p>
            <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">{highScoreThreshold}</p>
          </div>
          <div className="rounded-lg border border-surface-border bg-zinc-50 p-4 dark:bg-zinc-800/50">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Pipeline</p>
            <p className="mt-1 text-2xl font-bold text-zinc-900 dark:text-white">3 Modes</p>
          </div>
          <div className="rounded-lg border border-surface-border bg-zinc-50 p-4 dark:bg-zinc-800/50">
            <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">Status</p>
            <p className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">Active</p>
          </div>
        </div>
      </div>
    </div>
  )
}
