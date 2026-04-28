import { useEffect, useState } from 'react'
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

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const [s, ctl, logs] = await Promise.all([adminGetStats(), adminGetControls(), adminGetJobLogs(60)])
        if (!c) {
          setStats(s)
          setControls(ctl)
          setJobLogs(logs.items || [])
        }
      } catch (e) {
        if (!c) setErr(getApiErrorMessage(e, 'Could not load admin monitoring data.'))
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
            <p className="mt-1 text-xs text-ink-muted">Cron expressions used by scheduler config.</p>
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
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-display text-lg font-semibold text-ink">Job logs</h2>
          <button
            type="button"
            onClick={async () => {
              try {
                const logs = await adminGetJobLogs(60)
                setJobLogs(logs.items || [])
              } catch (e) {
                setSaveMsg(getApiErrorMessage(e, 'Could not refresh job logs.'))
              }
            }}
            className="rounded-lg border border-surface-border px-3 py-2 text-xs text-ink-muted hover:bg-field"
          >
            Refresh logs
          </button>
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
              {jobLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-3 text-ink-muted">
                    No job logs yet.
                  </td>
                </tr>
              ) : (
                jobLogs.map((row, idx) => (
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
