import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  adminGetConfig,
  adminGetControls,
  adminGetJobLogs,
  adminGetStats,
  adminPatchConfig,
  adminPatchControls,
  type AdminConfig,
  type AdminControls,
  type AdminJobLogRow,
  type AdminWorkspaceStats,
} from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'
import { adminCreateLeadPack, adminListLeadPacks, adminUpdateLeadPack } from '@/lib/api/marketplace'

export function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [controls, setControls] = useState<AdminControls | null>(null)
  const [adminConfig, setAdminConfig] = useState<AdminConfig | null>(null)
  const [jobLogs, setJobLogs] = useState<AdminJobLogRow[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [saveMsg, setSaveMsg] = useState<string>('')
  const [logsBusy, setLogsBusy] = useState(false)
  const [logsRefreshedAt, setLogsRefreshedAt] = useState('')
  const [jobFilter, setJobFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'partial_success' | 'failure'>('all')
  const [page, setPage] = useState(1)
  const [packName, setPackName] = useState('')
  const [packDescription, setPackDescription] = useState('')
  const [packLeadIds, setPackLeadIds] = useState('')
  const [packPrice, setPackPrice] = useState(99)
  const [packs, setPacks] = useState<Array<{ id: number; name: string; price_usd: number; lead_ids: string[]; is_active: boolean }>>([])
  const pageSize = 10

  function listToCsv(items: string[]) {
    return (items || []).join(', ')
  }

  function csvToList(raw: string) {
    return String(raw || '')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean)
  }

  function titleize(value: string) {
    const text = String(value || '').replaceAll('_', ' ').trim()
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : '—'
  }

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
        const [s, ctl, cfg, logs] = await Promise.all([adminGetStats(), adminGetControls(), adminGetConfig(), adminGetJobLogs(300)])
        const packRows = await adminListLeadPacks()
        if (!c) {
          setStats(s)
          setControls(ctl)
          setAdminConfig(cfg)
          setJobLogs(logs.items || [])
          setPacks(packRows || [])
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

      {adminConfig ? (
        <section className="space-y-4 rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
          <div>
            <h2 className="font-display text-lg font-semibold text-ink">Admin control layer</h2>
            <p className="mt-1 text-xs text-ink-muted">
              Control targeting, sources, scoring, priorities, worker count, scheduler, and retry policy from one place.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Target keywords (comma separated)</span>
              <input
                value={listToCsv(adminConfig.targeting.keywords)}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev ? { ...prev, targeting: { ...prev.targeting, keywords: csvToList(e.target.value) } } : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Target locations (comma separated)</span>
              <input
                value={listToCsv(adminConfig.targeting.locations)}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev ? { ...prev, targeting: { ...prev.targeting, locations: csvToList(e.target.value) } } : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Industries (comma separated)</span>
              <input
                value={listToCsv(adminConfig.targeting.industries)}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev ? { ...prev, targeting: { ...prev.targeting, industries: csvToList(e.target.value) } } : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Company types (comma separated)</span>
              <input
                value={listToCsv(adminConfig.targeting.company_types)}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev ? { ...prev, targeting: { ...prev.targeting, company_types: csvToList(e.target.value) } } : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs text-ink-muted">
            {(
              [
                'job_boards',
                'startup_directories',
                'local_listings',
                'manual_seeds',
                'linkedin',
                'public_db',
                'google_maps',
                'indiamart',
                'justdial',
                'eworldtrade',
                'global_sources',
                'thomasnet',
                'yelp',
                'faire',
              ] as const
            ).map((key) => (
              <label key={key} className="flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2">
                <input
                  type="checkbox"
                  checked={Boolean(adminConfig.sources[key])}
                  onChange={(e) =>
                    setAdminConfig((prev) =>
                      prev ? { ...prev, sources: { ...prev.sources, [key]: e.target.checked } } : prev,
                    )
                  }
                />
                <span>{key.replaceAll('_', ' ')}</span>
              </label>
            ))}
          </div>
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Source registry</div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {adminConfig.source_registry.map((entry) => (
                <label key={entry.source_name} className="rounded-xl border border-surface-border px-3 py-3 text-xs text-ink-muted">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={Boolean(entry.enabled)}
                      onChange={(e) =>
                        setAdminConfig((prev) =>
                          prev
                            ? {
                                ...prev,
                                source_registry: prev.source_registry.map((item) =>
                                  item.source_name === entry.source_name ? { ...item, enabled: e.target.checked } : item,
                                ),
                                sources: {
                                  ...prev.sources,
                                  allowed_sources: e.target.checked
                                    ? prev.sources.allowed_sources.includes(entry.source_name)
                                      ? prev.sources.allowed_sources
                                      : [...prev.sources.allowed_sources, entry.source_name]
                                    : prev.sources.allowed_sources.filter((item) => item !== entry.source_name),
                                },
                              }
                            : prev,
                        )
                      }
                    />
                    <span className="font-medium text-ink">{titleize(entry.source_name)}</span>
                  </div>
                  <div className="mt-2 space-y-1 text-[11px] text-ink-subtle">
                    <div>Type: {titleize(entry.source_type)}</div>
                    <div>Input: {titleize(entry.input_type)}</div>
                    <div className="break-all">Adapter: {entry.adapter_function}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>
          <label className="block space-y-1 text-xs text-ink-muted">
            <span>User-visible enabled sources</span>
            <input
              value={listToCsv((adminConfig.source_registry || []).filter((item) => item.enabled).map((item) => item.source_name))}
              readOnly
              className="field-input w-full rounded-lg px-2 py-1.5 text-sm opacity-80"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(adminConfig.scoring_weights).map(([key, value]) => (
              <label key={key} className="space-y-1 text-xs text-ink-muted">
                <span>{key.replaceAll('_', ' ')}</span>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={value}
                  onChange={(e) =>
                    setAdminConfig((prev) =>
                      prev ? { ...prev, scoring_weights: { ...prev.scoring_weights, [key]: Number(e.target.value || 1) } } : prev,
                    )
                  }
                  className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
                />
              </label>
            ))}
          </div>
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">AI Control</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-xs text-ink-muted">
              {(['ollama_enabled', 'api_enabled'] as const).map((key) => (
                <label key={key} className="flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2">
                  <input
                    type="checkbox"
                    checked={Boolean(adminConfig.ai_control[key])}
                    onChange={(e) =>
                      setAdminConfig((prev) =>
                        prev ? { ...prev, ai_control: { ...prev.ai_control, [key]: e.target.checked } } : prev,
                      )
                    }
                  />
                  <span>{key.replaceAll('_', ' ')}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">Scoring Control</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(adminConfig.scoring_control).map(([key, value]) => (
                <label key={key} className="space-y-1 text-xs text-ink-muted">
                  <span>{key.replaceAll('_', ' ')}</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={value}
                    onChange={(e) =>
                      setAdminConfig((prev) =>
                        prev ? { ...prev, scoring_control: { ...prev.scoring_control, [key]: Number(e.target.value || 1) } } : prev,
                      )
                    }
                    className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(adminConfig.task_priority).map(([key, value]) => (
              <label key={key} className="space-y-1 text-xs text-ink-muted">
                <span>{key}</span>
                <select
                  value={value}
                  onChange={(e) =>
                    setAdminConfig((prev) =>
                      prev
                        ? {
                            ...prev,
                            task_priority: {
                              ...prev.task_priority,
                              [key]: e.target.value as 'high' | 'medium' | 'low',
                            },
                          }
                        : prev,
                    )
                  }
                  className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
                >
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </label>
            ))}
          </div>

          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">Queue Priority</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(adminConfig.queue_priority).map(([key, value]) => (
                <label key={key} className="space-y-1 text-xs text-ink-muted">
                  <span>{key}</span>
                  <select
                    value={value}
                    onChange={(e) =>
                      setAdminConfig((prev) =>
                        prev
                          ? {
                              ...prev,
                              queue_priority: {
                                ...prev.queue_priority,
                                [key]: e.target.value as 'high' | 'medium' | 'low',
                              },
                            }
                          : prev,
                      )
                    }
                    className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Worker count</span>
              <input
                type="number"
                min={1}
                max={64}
                value={adminConfig.worker_config.worker_count}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev
                      ? {
                          ...prev,
                          worker_config: { worker_count: Number(e.target.value || 1) },
                        }
                      : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Daily time (HH:MM)</span>
              <input
                value={adminConfig.scheduler_config.daily_time}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev
                      ? { ...prev, scheduler_config: { ...prev.scheduler_config, daily_time: e.target.value } }
                      : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Weekly time (HH:MM)</span>
              <input
                value={adminConfig.scheduler_config.weekly_time}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev
                      ? { ...prev, scheduler_config: { ...prev.scheduler_config, weekly_time: e.target.value } }
                      : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>LinkedIn day</span>
              <select
                value={adminConfig.scheduler_config.linkedin_day}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev
                      ? { ...prev, scheduler_config: { ...prev.scheduler_config, linkedin_day: e.target.value } }
                      : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              >
                <option value="mon">Mon</option>
                <option value="tue">Tue</option>
                <option value="wed">Wed</option>
                <option value="thu">Thu</option>
                <option value="fri">Fri</option>
                <option value="sat">Sat</option>
                <option value="sun">Sun</option>
              </select>
            </label>
            <label className="space-y-1 text-xs text-ink-muted">
              <span>Retry count</span>
              <input
                type="number"
                min={1}
                max={10}
                value={adminConfig.retry_policy.retry_count}
                onChange={(e) =>
                  setAdminConfig((prev) =>
                    prev ? { ...prev, retry_policy: { retry_count: Number(e.target.value || 1) } } : prev,
                  )
                }
                className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
              />
            </label>
          </div>
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-ink-muted">Safety Control</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(adminConfig.safety_control).map(([key, value]) => (
                <label key={key} className="space-y-1 text-xs text-ink-muted">
                  <span>{key.replaceAll('_', ' ')}</span>
                  <input
                    type="number"
                    min={key === 'delay_seconds' ? 0.2 : 1}
                    max={key === 'delay_seconds' ? 8 : 2000}
                    step={key === 'delay_seconds' ? 0.1 : 1}
                    value={Number(value)}
                    onChange={(e) =>
                      setAdminConfig((prev) =>
                        prev
                          ? {
                              ...prev,
                              safety_control: {
                                ...prev.safety_control,
                                [key]: Number(e.target.value || 0),
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
          </div>

          <button
            type="button"
            onClick={async () => {
              try {
                const next = await adminPatchConfig(adminConfig)
                setAdminConfig(next)
                setSaveMsg('Admin control config saved.')
              } catch (e) {
                setSaveMsg(getApiErrorMessage(e, 'Could not save admin control config.'))
              }
            }}
            className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200"
          >
            Save admin control layer
          </button>
        </section>
      ) : null}

      <section className="space-y-4 rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
        <div>
          <h2 className="font-display text-lg font-semibold text-ink">Lead packs marketplace</h2>
          <p className="mt-1 text-xs text-ink-muted">Create buyer lead packs, set pricing, and control active availability.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-xs text-ink-muted">
            <span>Pack name</span>
            <input value={packName} onChange={(e) => setPackName(e.target.value)} className="field-input w-full rounded-lg px-2 py-1.5 text-sm" />
          </label>
          <label className="space-y-1 text-xs text-ink-muted">
            <span>Price (USD)</span>
            <input
              type="number"
              min={0}
              step="0.01"
              value={packPrice}
              onChange={(e) => setPackPrice(Number(e.target.value || 0))}
              className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
            />
          </label>
        </div>
        <label className="space-y-1 text-xs text-ink-muted">
          <span>Description</span>
          <textarea
            value={packDescription}
            onChange={(e) => setPackDescription(e.target.value)}
            rows={2}
            className="field-input w-full rounded-lg px-2 py-1.5 text-sm"
          />
        </label>
        <label className="space-y-1 text-xs text-ink-muted">
          <span>Lead IDs (comma separated)</span>
          <textarea
            value={packLeadIds}
            onChange={(e) => setPackLeadIds(e.target.value)}
            rows={2}
            className="field-input w-full rounded-lg px-2 py-1.5 font-mono text-xs"
          />
        </label>
        <button
          type="button"
          onClick={async () => {
            try {
              await adminCreateLeadPack({
                name: packName.trim(),
                description: packDescription.trim(),
                lead_ids: packLeadIds.split(',').map((x) => x.trim()).filter(Boolean),
                price_usd: Number(packPrice || 0),
                is_active: true,
              })
              setSaveMsg('Lead pack created.')
              setPacks(await adminListLeadPacks())
            } catch (e) {
              setSaveMsg(getApiErrorMessage(e, 'Could not create lead pack.'))
            }
          }}
          className="w-fit rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200"
        >
          Create lead pack
        </button>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="border-b border-surface-border text-ink-muted">
              <tr>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Price</th>
                <th className="px-2 py-2">Leads</th>
                <th className="px-2 py-2">Active</th>
                <th className="px-2 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {packs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-3 text-ink-muted">
                    No packs yet.
                  </td>
                </tr>
              ) : (
                packs.map((pack) => (
                  <tr key={pack.id} className="border-b border-surface-border/70">
                    <td className="px-2 py-2">{pack.name}</td>
                    <td className="px-2 py-2">${Number(pack.price_usd || 0).toFixed(2)}</td>
                    <td className="px-2 py-2">{(pack.lead_ids || []).length}</td>
                    <td className="px-2 py-2">{pack.is_active ? 'Yes' : 'No'}</td>
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        className="rounded border border-surface-border px-2 py-1 hover:bg-field/60"
                        onClick={async () => {
                          try {
                            await adminUpdateLeadPack(pack.id, {
                              name: pack.name,
                              description: '',
                              lead_ids: pack.lead_ids || [],
                              price_usd: Number(pack.price_usd || 0),
                              is_active: !pack.is_active,
                            })
                            setPacks(await adminListLeadPacks())
                          } catch (e) {
                            setSaveMsg(getApiErrorMessage(e, 'Could not update pack'))
                          }
                        }}
                      >
                        Toggle
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

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
