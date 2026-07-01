import { ArrowRight, Cable, ScrollText, Sliders, Users, Wallet } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'

import { adminGetStats, type AdminWorkspaceStats } from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'

const quickLinks = [
  { to: '/admin/users', label: 'Users', icon: Users, color: 'from-blue-500 to-blue-600', desc: 'Manage accounts' },
  { to: '/admin/lead-packs', label: 'Lead Packs', icon: Wallet, color: 'from-emerald-500 to-emerald-600', desc: 'Curated lead packs' },
  { to: '/admin/scoring', label: 'Scoring', icon: Sliders, color: 'from-violet-500 to-violet-600', desc: 'Weights & schedule' },
  { to: '/admin/sources', label: 'Sources', icon: Cable, color: 'from-orange-500 to-orange-600', desc: 'Channels & registry' },
  { to: '/admin/job-logs', label: 'Job Logs', icon: ScrollText, color: 'from-rose-500 to-rose-600', desc: 'Monitor automation' },
]

export function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const s = await adminGetStats()
        if (!c) setStats(s)
      } catch (e) {
        if (!c) setErr(getApiErrorMessage(e, 'Could not load admin data.'))
      }
    })()
    return () => { c = true }
  }, [])

  const funnelData = useMemo(() => {
    if (!stats) return []
    return [
      { name: 'Total Leads', value: stats.total_leads },
      { name: 'Hot', value: stats.hot_leads },
      { name: 'Contacted', value: stats.contacted_leads },
      { name: 'Converted', value: stats.converted_leads },
    ]
  }, [stats])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Overview of your workspace performance</p>
      </div>

      {err && (
        <div className="rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">
          {err}
        </div>
      )}

      {/* Stats Cards */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="absolute right-0 top-0 h-20 w-20 translate-x-6 -translate-y-6 rounded-full bg-amber-500/5" />
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Registered Users</p>
          <p className="mt-2 font-display text-3xl font-bold text-zinc-900 dark:text-white">
            {stats?.registered_users ?? '—'}
          </p>
        </div>
        <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="absolute right-0 top-0 h-20 w-20 translate-x-6 -translate-y-6 rounded-full bg-blue-500/5" />
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Total Leads</p>
          <p className="mt-2 font-display text-3xl font-bold text-blue-600 dark:text-blue-400">
            {stats?.total_leads ?? '—'}
          </p>
        </div>
        <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="absolute right-0 top-0 h-20 w-20 translate-x-6 -translate-y-6 rounded-full bg-emerald-500/5" />
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Hot Leads</p>
          <p className="mt-2 font-display text-3xl font-bold text-emerald-600 dark:text-emerald-400">
            {stats?.hot_leads ?? '—'}
          </p>
        </div>
        <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="absolute right-0 top-0 h-20 w-20 translate-x-6 -translate-y-6 rounded-full bg-violet-500/5" />
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Conversion Rate</p>
          <p className="mt-2 font-display text-3xl font-bold text-violet-600 dark:text-violet-400">
            {stats?.conversion_rate_percent ?? 0}%
          </p>
        </div>
      </section>

      {/* Chart + Additional Stats */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Lead Funnel Chart */}
        {funnelData.length > 0 && (
          <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900 lg:col-span-2">
            <h2 className="mb-4 font-display text-base font-semibold text-zinc-900 dark:text-white">Lead Funnel</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="stroke-zinc-200 dark:stroke-zinc-700" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} className="text-zinc-500" />
                  <YAxis tick={{ fontSize: 12 }} className="text-zinc-500" />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '12px',
                      border: '1px solid var(--color-surface-border)',
                      backgroundColor: 'var(--color-surface)',
                    }}
                  />
                  <Bar dataKey="value" fill="#f59e0b" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Quick Stats */}
        {stats && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Companies</p>
              <p className="mt-2 font-display text-2xl font-bold text-zinc-900 dark:text-white">{stats.total_companies ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Contacted</p>
              <p className="mt-2 font-display text-2xl font-bold text-zinc-900 dark:text-white">{stats.contacted_leads}</p>
            </div>
            <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Converted</p>
              <p className="mt-2 font-display text-2xl font-bold text-emerald-600 dark:text-emerald-400">{stats.converted_leads}</p>
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {quickLinks.map(({ to, label, icon: Icon, color, desc }) => (
          <Link
            key={to}
            to={to}
            className="group rounded-2xl border border-surface-border bg-white p-5 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 dark:bg-zinc-900"
          >
            <div className={`mb-3 inline-flex rounded-lg bg-gradient-to-br ${color} p-2.5 shadow-sm`}>
              <Icon className="h-5 w-5 text-white" />
            </div>
            <h3 className="font-display text-base font-semibold text-zinc-900 dark:text-white">{label}</h3>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{desc}</p>
            <div className="mt-3 flex items-center gap-1 text-xs font-medium text-amber-600 dark:text-amber-400 opacity-0 transition-opacity group-hover:opacity-100">
              Go to {label} <ArrowRight className="h-3 w-3" />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
