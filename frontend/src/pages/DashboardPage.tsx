import { useEffect, useMemo, useState } from 'react'

import { PlatformBar, StatusPie } from '@/components/charts/DistributionCharts'
import { MonthLineChart, type MonthPoint } from '@/components/charts/MonthLineChart'
import { StackedTierByPlatform, type TierStackRow } from '@/components/charts/StackedTierByPlatform'
import { StatCard } from '@/components/dashboard/StatCard'
import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { fetchDashboard } from '@/lib/api/analytics'
import { leadStatusLabel } from '@/lib/copy/appCopy'
import type { DashboardData } from '@/types/models'

export function DashboardPage() {
  const [dash, setDash] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)

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

  const { monthData, stackData } = useMemo(() => {
    const lm = dash?.leads_by_month ?? []
    const monthData: MonthPoint[] = lm.map((x) => ({ month: x.month, count: x.count }))
    const tm = dash?.tier_mix_by_platform ?? []
    const stackData: TierStackRow[] = tm.map((x) => ({
      platform: x.platform,
      hot: x.hot,
      warm: x.warm,
      cold: x.cold,
    }))
    return { monthData, stackData }
  }, [dash])

  const plat = useMemo(() => {
    const raw = dash?.platform_distribution || dash?.by_platform || {}
    return Object.entries(raw).map(([name, value]) => ({ name, value: Number(value) }))
  }, [dash])

  const stat = useMemo(() => {
    const raw = dash?.status_distribution || dash?.by_status || {}
    return Object.entries(raw).map(([name, value]) => ({
      name: leadStatusLabel(String(name).toLowerCase().replace(/\s+/g, '_')),
      value: Number(value),
    }))
  }, [dash])

  if (loading) {
    return (
      <div className="mx-auto max-w-[1600px] space-y-10">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton-shimmer h-32 rounded-2xl" />
          ))}
        </section>
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="skeleton-shimmer h-96 rounded-2xl" />
          <div className="skeleton-shimmer h-96 rounded-2xl" />
        </section>
        <section className="grid gap-6 lg:grid-cols-2">
          <div className="skeleton-shimmer h-96 rounded-2xl" />
          <div className="skeleton-shimmer h-96 rounded-2xl" />
        </section>
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

  const total = dash.total_leads ?? dash.total ?? 0
  const conv = dash.conversion_rate_percent ?? 0

  return (
    <div className="mx-auto max-w-[1600px] space-y-10">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          title="Total workspace leads"
          value={total}
          hint="All prospect records available for lead tracking and sales outreach."
        />
        <StatCard
          title="High-priority opportunities"
          value={dash.hot_leads ?? 0}
          hint="Lead scoring tier indicating the strongest conversion signals."
        />
        <StatCard
          title="Active outreach"
          value={dash.contacted_leads ?? 0}
          hint="Contacts with logged outreach activity in your sales pipeline."
        />
        <StatCard
          title="Closed outcomes"
          value={dash.converted_leads ?? 0}
          hint="Won or converted records for customer acquisition reporting."
        />
        <StatCard
          title="Pipeline conversion rate"
          value={`${conv}%`}
          hint="Converted leads divided by total leads for conversion optimization."
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="type-section-heading">Lead source distribution</h2>
          <p className="mb-3 text-xs text-ink-muted">
            Volume by connected platform to compare prospecting channels and business intelligence inputs.
          </p>
          <PlatformBar data={plat.length ? plat : [{ name: '—', value: 0 }]} />
        </div>
        <div>
          <h2 className="type-section-heading">Lead status breakdown</h2>
          <p className="mb-3 text-xs text-ink-muted">
            CRM pipeline mix across lead management stages from new through closed.
          </p>
          <StatusPie data={stat.length ? stat : [{ name: '—', value: 1 }]} />
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="type-section-heading">Lead activity summary</h2>
          <p className="mb-3 text-xs text-ink-muted">
            New lead volume by month for sales analytics and capacity planning.
          </p>
          <MonthLineChart
            data={
              monthData.length
                ? monthData
                : [{ month: new Date().toISOString().slice(0, 7), count: 0 }]
            }
          />
        </div>
        <div>
          <h2 className="type-section-heading">Lead scoring mix by source</h2>
          <p className="mb-3 text-xs text-ink-muted">
            Hot, warm, and cold qualification tiers by platform for lead scoring calibration.
          </p>
          <StackedTierByPlatform
            data={
              stackData.length
                ? stackData
                : [{ platform: '—', hot: 0, warm: 0, cold: 0 }]
            }
          />
        </div>
      </section>
    </div>
  )
}
