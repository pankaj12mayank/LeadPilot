import { Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { StatusBadge } from '@/components/ui/Badge'
import { FilterSelect } from '@/components/ui/FilterSelect'
import { fetchLeads } from '@/lib/api/leads'
import { leadStatusLabel } from '@/lib/copy/appCopy'
import type { Lead } from '@/types/models'

function isClosedStatus(status: string) {
  const s = (status || '').trim().toLowerCase().replace(/\s+/g, '_')
  return s === 'close' || s === 'closed' || s === 'converted'
}

function fmtShort(iso: string) {
  if (!iso) return '—'
  return iso.length >= 10 ? iso.slice(0, 16).replace('T', ' ') : iso
}

const STATUS_OPTIONS = [
  { value: '', label: 'All active statuses' },
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'replied', label: 'Replied' },
  { value: 'follow_up', label: 'Follow-up' },
]

export function OutreachQueuePage() {
  const [rows, setRows] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [preset, setPreset] = useState<'none' | 'hot' | 'hiring' | 'quick_wins' | 'growth'>('none')
  const [showWorkflow, setShowWorkflow] = useState(false)
  const [highlightReady, setHighlightReady] = useState(false)
  const [skippedBrokenRows, setSkippedBrokenRows] = useState(0)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const r = await fetchLeads({
        page: 1,
        page_size: 200,
        sort: 'score_desc',
        status: statusFilter || undefined,
      })
      const incoming = r.items || []
      const safeRows = incoming.filter((x) => x && typeof x.id === 'string' && x.id.trim())
      setSkippedBrokenRows(Math.max(0, incoming.length - safeRows.length))
      setRows(safeRows)
    } catch {
      setRows([])
      setErr('Could not load outreach queue.')
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  useEffect(() => {
    void load()
  }, [load])

  const queueRows = useMemo(() => {
    return (rows || [])
      .filter((x) => !isClosedStatus(x.status || ''))
      .filter((x) => Number(x.score || 0) >= Number(minScore || 0))
      .filter((x) => {
        if (preset === 'hiring') return Number(x.signal_hiring || 0) >= 1
        if (preset === 'quick_wins') return Number(x.signal_content_gap || 0) >= 1
        if (preset === 'growth') return Number(x.signal_scaling || 0) >= 1
        return true
      })
      .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
  }, [rows, minScore, preset])

  function applyPreset(p: 'hot' | 'hiring' | 'quick_wins' | 'growth') {
    if (p === 'hot') {
      setMinScore(70)
      setPreset('hot')
      return
    }
    setMinScore(0)
    setPreset(p)
  }

  function isReadyForOutreach(lead: Lead) {
    const st = (lead.status || '').toLowerCase()
    return !isClosedStatus(st) && Number(lead.score || 0) >= 70 && Boolean((lead.personalized_message || '').trim())
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-6">
      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="type-panel-title">Outreach Queue</h2>
            <p className="mt-1 text-xs text-ink-muted">
              Active pipeline queue (all leads not closed), sorted by highest score first.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowWorkflow((v) => !v)}
              className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 transition hover:border-amber-500/60 dark:text-amber-200"
            >
              Daily Workflow
            </button>
            <button
              type="button"
              onClick={() => void load()}
              className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted transition hover:bg-field"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
              Refresh
            </button>
          </div>
        </div>
        {showWorkflow ? (
          <div className="mt-4 rounded-xl border border-surface-border bg-field/40 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-subtle">Daily Workflow Guide</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-4 text-sm text-ink-muted">
              <li>Open Explorer</li>
              <li>Filter Hot Leads</li>
              <li>Select top 10</li>
              <li>Send messages (manual paste in LinkedIn/Email)</li>
              <li>Update status</li>
            </ol>
            <label className="mt-3 inline-flex items-center gap-2 text-xs text-ink-muted">
              <input
                type="checkbox"
                checked={highlightReady}
                onChange={(e) => setHighlightReady(e.target.checked)}
                className="h-4 w-4 rounded border-surface-border accent-amber-600"
              />
              Highlight leads ready for outreach
            </label>
          </div>
        ) : null}

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Status filter</label>
            <FilterSelect
              className="mt-1"
              options={STATUS_OPTIONS}
              value={statusFilter}
              onChange={setStatusFilter}
              placeholder="All active statuses"
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Min score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => {
                const next = Number(e.target.value)
                if (!Number.isFinite(next)) {
                  setErr('Min score must be a valid number between 0 and 100.')
                  return
                }
                if (next < 0 || next > 100) {
                  setErr('Min score must be between 0 and 100.')
                  return
                }
                setErr(null)
                setMinScore(next)
              }}
              className="field-input mt-1"
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-ink-subtle">Smart presets</span>
          <button
            type="button"
            onClick={() => applyPreset('hot')}
            className={`rounded-lg border px-2.5 py-1 text-[11px] transition ${
              preset === 'hot' ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-surface-border text-ink-muted hover:bg-field hover:text-ink'
            }`}
          >
            Hot Leads
          </button>
          <button
            type="button"
            onClick={() => applyPreset('hiring')}
            className={`rounded-lg border px-2.5 py-1 text-[11px] transition ${
              preset === 'hiring' ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-surface-border text-ink-muted hover:bg-field hover:text-ink'
            }`}
          >
            Hiring Companies
          </button>
          <button
            type="button"
            onClick={() => applyPreset('quick_wins')}
            className={`rounded-lg border px-2.5 py-1 text-[11px] transition ${
              preset === 'quick_wins' ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-surface-border text-ink-muted hover:bg-field hover:text-ink'
            }`}
          >
            Quick Wins
          </button>
          <button
            type="button"
            onClick={() => applyPreset('growth')}
            className={`rounded-lg border px-2.5 py-1 text-[11px] transition ${
              preset === 'growth' ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-surface-border text-ink-muted hover:bg-field hover:text-ink'
            }`}
          >
            Growth
          </button>
          <button
            type="button"
            onClick={() => {
              setPreset('none')
              setMinScore(0)
            }}
            className="rounded-lg border border-surface-border px-2.5 py-1 text-[11px] text-ink-muted transition hover:bg-field hover:text-ink"
          >
            Clear preset
          </button>
        </div>
      </section>

      {err ? (
        <div className="rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">
          {err}
        </div>
      ) : null}
      {skippedBrokenRows > 0 ? (
        <div className="rounded-xl border border-amber-500/30 bg-amber-50 px-4 py-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
          Skipped {skippedBrokenRows} broken lead row(s) safely.
        </div>
      ) : null}

      <section className="overflow-hidden rounded-2xl border border-surface-border bg-premium-card-light shadow-card dark:bg-premium-card-dark">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[780px] text-left text-sm">
            <thead className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
              <tr className="border-b border-surface-border">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Last contacted</th>
                <th className="px-3 py-2">Score</th>
              </tr>
            </thead>
            <tbody>
              {loading && queueRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-12 text-center text-ink-muted">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : queueRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-10 text-center text-ink-muted">
                    No active leads found for current filters.
                  </td>
                </tr>
              ) : (
                queueRows.map((row) => (
                  <tr
                    key={row.id}
                    className={`border-b border-surface-border/80 text-ink-muted last:border-0 hover:bg-amber-500/[0.04] dark:hover:bg-amber-400/[0.03] ${
                      highlightReady && isReadyForOutreach(row)
                        ? 'bg-emerald-500/[0.08] dark:bg-emerald-400/[0.08]'
                        : ''
                    }`}
                  >
                    <td className="max-w-[16rem] truncate px-3 py-2.5 text-ink" title={row.full_name}>
                      {row.full_name || '—'}
                    </td>
                    <td className="max-w-[14rem] truncate px-3 py-2.5" title={row.company_name}>
                      {row.company_name || '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      <StatusBadge status={row.status || 'new'} title={leadStatusLabel(row.status || 'new')} />
                    </td>
                    <td className="px-3 py-2.5 tabular-nums">{fmtShort(row.last_contacted_at || '')}</td>
                    <td className="px-3 py-2.5 font-semibold tabular-nums text-ink">{Math.round(Number(row.score || 0))}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
