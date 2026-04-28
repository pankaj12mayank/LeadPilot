import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  adminGetControls,
  adminGetJobLogs,
  adminGetStats,
  adminPatchControls,
  type AdminControls,
  type AdminJobLogRow,
  type AdminWorkspaceStats,
} from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'

export function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [controls, setControls] = useState<AdminControls | null>(null)
  const [jobLogs, setJobLogs] = useState<AdminJobLogRow[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState<string>('')
  const [logsBusy, setLogsBusy] = useState(false)
  const [logsRefreshedAt, setLogsRefreshedAt] = useState('')
  const [jobFilter, setJobFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'partial_success' | 'failure'>('all')
  const [page, setPage] = useState(1)
  const pageSize = 10

  function explainCron(expr: string): string {
    const p = String(expr || '').trim().split(/\s+/)
    if (p.length !== 5) return 'Invalid format. Use: minute hour day month weekday'
    const [min, hr, day, month, week] = p
    const weekdayMap: Record<string, string> = {
      '0': 'Sunday',
      '1': 'Monday',
      '2': 'Tuesday',
      '3': 'Wednesday',
      '4': 'Thursday',
      '5': 'Friday',
      '6': 'Saturday',
    }
    const hh = /^\d+$/.test(hr) ? String(Math.max(0, Math.min(23, Number(hr)))).padStart(2, '0') : hr
    const mm = /^\d+$/.test(min) ? String(Math.max(0, Math.min(59, Number(min)))).padStart(2, '0') : min
    const timeText = `${hh}:${mm}`
    if (day === '*' && month === '*' && week === '*') return `Runs daily at ${timeText}`
    if (day === '*' && month === '*' && weekdayMap[week]) return `Runs every ${weekdayMap[week]} at ${timeText}`
    return `Runs at ${timeText} with custom cron rule`
  }

  const filteredLogs = useMemo(() => {
    const q = jobFilter.trim().toLowerCase()
    return jobLogs.filter((x) => {
      const byJob = !q || String(x.job_type || '').toLowerCase().includes(q)
      const byStatus = statusFilter === 'all' || String(x.status || '') === statusFilter
      return byJob && byStatus
    })
  }, [jobFilter, jobLogs, statusFilter])

  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / pageSize))
  const pageRows = useMemo(() => {
    const p = Math.max(1, Math.min(page, totalPages))
    const start = (p - 1) * pageSize
    return filteredLogs.slice(start, start + pageSize)
  }, [filteredLogs, page, totalPages])

  async function refreshLogs() {
    setLogsBusy(true)
    try {
      const logs = await adminGetJobLogs(300)
      setJobLogs(logs.items || [])
      setLogsRefreshedAt(new Date().toLocaleTimeString())
      setSaveMsg('Job logs refreshed.')
    } catch (e) {
      setSaveMsg(getApiErrorMessage(e, 'Could not refresh job logs.'))
    } finally {
      setLogsBusy(false)
    }
  }

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const [s, ctl, logs] = await Promise.all([adminGetStats(), adminGetControls(), adminGetJobLogs(300)])
        if (!c) {
          setStats(s)
          setControls(ctl)
          setJobLogs(logs.items || [])
          setLogsRefreshedAt(new Date().toLocaleTimeString())
        }
      } catch (e) {
        if (!c) setErr(getApiErrorMessage(e, 'Could not load admin monitoring data.'))
      }
    })()
    return () => {
      c = true
    }
  }, [])

  useEffect(() => {
    setPage(1)
  }, [jobFilter, statusFilter])

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
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">DB companies</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.total_companies ?? 0}</div>
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

      {controls ? (
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <h2 className="font-display text-lg font-semibold text-ink">Scoring weights</h2>
            <p className="mt-1 text-xs text-ink-muted">Adjust scoring distribution used by enrichment and lead scoring.</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {Object.entries(controls.scoring_weights).map(([k, v]) => (
                <label key={k} className="space-y-1 text-xs text-ink-muted">
                  <span>{k.replaceAll('_', ' ')}</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={v}
                    onChange={(e) =>
                      setControls((prev) =>
                        prev
                          ? {
                              ...prev,
                              scoring_weights: {
                                ...prev.scoring_weights,
                                [k]: Number(e.target.value || 0),
                              },
                            }
                          : prev,
                      )
                    }
                    className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  const next = await adminPatchControls({ scoring_weights: controls.scoring_weights })
                  setControls(next)
                  setSaveMsg('Scoring weights saved.')
                } catch (e) {
                  setSaveMsg(getApiErrorMessage(e, 'Could not save scoring weights.'))
                }
              }}
              className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200"
            >
              Save scoring weights
            </button>
          </div>

          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <h2 className="font-display text-lg font-semibold text-ink">Schedule timing (optional)</h2>
            <p className="mt-1 text-xs text-ink-muted">
              Use format: <span className="font-mono">minute hour day month weekday</span>. Example: <span className="font-mono">0 2 * * *</span> means every day at 02:00.
            </p>
            <div className="mt-3 grid gap-2">
              {Object.entries(controls.schedule_timing).map(([k, v]) => (
                <label key={k} className="space-y-1 text-xs text-ink-muted">
                  <span>{k.replaceAll('_', ' ')}</span>
                  <input
                    value={v}
                    onChange={(e) =>
                      setControls((prev) =>
                        prev
                          ? {
                              ...prev,
                              schedule_timing: {
                                ...prev.schedule_timing,
                                [k]: e.target.value,
                              },
                            }
                          : prev,
                      )
                    }
                    className="field-input w-full rounded-lg px-2 py-1.5 font-mono text-xs"
                  />
                  <p className="text-[11px] text-ink-subtle">{explainCron(v)}</p>
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={async () => {
                try {
                  const next = await adminPatchControls({ schedule_timing: controls.schedule_timing })
                  setControls(next)
                  setSaveMsg('Schedule timing saved.')
                } catch (e) {
                  setSaveMsg(getApiErrorMessage(e, 'Could not save schedule timing.'))
                }
              }}
              className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200"
            >
              Save schedule timing
            </button>
          </div>
        </section>
      ) : null}

      {saveMsg ? <p className="text-xs text-ink-muted">{saveMsg}</p> : null}

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">Job logs</h2>
            <p className="text-xs text-ink-subtle">Last refresh: {logsRefreshedAt || '—'}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={jobFilter}
              onChange={(e) => setJobFilter(e.target.value)}
              placeholder="Filter by job type"
              className="field-input w-44 rounded-lg px-2 py-1.5 text-xs"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as 'all' | 'success' | 'partial_success' | 'failure')}
              className="field-input rounded-lg px-2 py-1.5 text-xs"
            >
              <option value="all">All status</option>
              <option value="success">Success</option>
              <option value="partial_success">Partial success</option>
              <option value="failure">Failure</option>
            </select>
            <button
              type="button"
              onClick={() => void refreshLogs()}
              disabled={logsBusy}
              className="rounded-lg border border-surface-border px-3 py-2 text-xs text-ink-muted hover:bg-field disabled:opacity-50"
            >
              {logsBusy ? 'Refreshing…' : 'Refresh logs'}
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-xs">
            <thead className="border-b border-surface-border text-ink-muted">
              <tr>
                <th className="px-2 py-2">Run date</th>
                <th className="px-2 py-2">Job</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Processed</th>
                <th className="px-2 py-2">Errors</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-3 text-ink-muted">
                    No job logs yet.
                  </td>
                </tr>
              ) : (
                pageRows.map((row, idx) => (
                  <tr key={`${row.run_date}-${row.job_type}-${idx}`} className="border-b border-surface-border/70">
                    <td className="px-2 py-2">{row.run_date || '—'}</td>
                    <td className="px-2 py-2">{row.job_type || '—'}</td>
                    <td className="px-2 py-2">{row.status || '—'}</td>
                    <td className="px-2 py-2">{Number(row.records_processed || 0)}</td>
                    <td className="px-2 py-2">{(row.errors || []).slice(0, 2).join(' | ') || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-ink-muted">
          <span>
            Showing {pageRows.length} of {filteredLogs.length} logs
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-lg border border-surface-border px-2 py-1 disabled:opacity-40"
            >
              Prev
            </button>
            <span>
              Page {Math.min(page, totalPages)} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="rounded-lg border border-surface-border px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </section>

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
