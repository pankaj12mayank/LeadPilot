import { useEffect, useState } from 'react'

import { StatCard } from '@/components/dashboard/StatCard'
import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { fetchDashboard } from '@/lib/api/analytics'
import { getHighScoreThreshold } from '@/lib/config/userConfigRules'
import { fetchSeleniumLeadpilotStatus, type SeleniumLeadpilotStatus } from '@/lib/api/seleniumLeadpilot'
import { useUserConfigStore } from '@/store/userConfigStore'
import type { DashboardData } from '@/types/models'

export function DashboardPage() {
  const adminConfig = useUserConfigStore((s) => s.adminConfig)
  const highScoreThreshold = getHighScoreThreshold(adminConfig)
  const [dash, setDash] = useState<DashboardData | null>(null)
  const [runStatus, setRunStatus] = useState<SeleniumLeadpilotStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    ;(async () => {
      try {
        const [d, s] = await Promise.all([fetchDashboard(), fetchSeleniumLeadpilotStatus()])
        if (!cancelled) {
          setDash(d)
          setRunStatus(s)
        }
      } catch {
        if (!cancelled) {
          setDash(null)
          setRunStatus(null)
          setLoadError(
            'The dashboard could not load from the API. Start the backend (port 8000 by default), confirm Vite proxy /api → API_ROOT_PATH, or set VITE_API_BASE_URL (e.g. http://localhost:8000/api), then try again.',
          )
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [retryNonce])

  if (loading) {
    return (
      <div className="mx-auto max-w-[1200px] space-y-8">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton-shimmer h-32 rounded-2xl" />
          ))}
        </section>
        <div className="skeleton-shimmer h-36 rounded-2xl" />
      </div>
    )
  }

  if (loadError || !dash) {
    return (
      <div className="mx-auto max-w-[1600px]">
        <ApiLoadError
          title="Dashboard unavailable"
          message={loadError ?? 'No dashboard payload was returned from the server.'}
          onRetry={() => setRetryNonce((n) => n + 1)}
        />
      </div>
    )
  }

  const totalCompanies = dash.total_companies ?? 0
  const totalLeads = dash.total_leads ?? dash.total ?? 0
  const hotLeads = dash.hot_leads ?? 0
  const newLeads = dash.new_leads ?? Number(dash.status_distribution?.new ?? dash.by_status?.new ?? 0)
  const lastRunStatus = runStatus?.state ? runStatus.state.charAt(0).toUpperCase() + runStatus.state.slice(1) : 'Unknown'
  const lastRunHint = runStatus?.message || 'No recent job status available.'

  return (
    <div className="mx-auto max-w-[1200px] space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">User Dashboard</h1>
        <p className="mt-2 max-w-2xl text-sm text-ink-muted">
          System status at a glance. See lead volume, priority, and latest run state immediately on load.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total leads"
          value={totalLeads}
          hint="All leads currently available in the system."
        />
        <StatCard
          title="Hot leads"
          value={hotLeads}
          hint={`High-priority leads with score >= ${highScoreThreshold}.`}
        />
        <StatCard
          title="New leads"
          value={newLeads}
          hint="Leads currently in New status."
        />
        <StatCard
          title="Last run status"
          value={lastRunStatus}
          hint={lastRunHint}
        />
      </section>

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark sm:p-6">
        <h2 className="type-panel-title">System Snapshot</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-surface-border bg-field/40 px-4 py-3 text-sm text-ink-muted">
            <div className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">Total companies</div>
            <div className="mt-1 text-xl font-semibold text-ink">{totalCompanies}</div>
          </div>
          <div className="rounded-xl border border-surface-border bg-field/40 px-4 py-3 text-sm text-ink-muted">
            <div className="text-xs font-semibold uppercase tracking-wide text-ink-subtle">Job state</div>
            <div className="mt-1 text-xl font-semibold capitalize text-ink">{runStatus?.state ?? 'unknown'}</div>
          </div>
        </div>
      </section>
    </div>
  )
}
