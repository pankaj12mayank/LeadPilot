import { Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { SeleniumLeadpilotPanel } from '@/components/scraper/SeleniumLeadpilotPanel'
import { StatusBadge } from '@/components/ui/Badge'
import { explorerSearchCompanies, type ExplorerCompany } from '@/lib/api/companies'
import { getApiErrorMessage } from '@/lib/api/client'
import { fetchLeads } from '@/lib/api/leads'
import { useModeStore } from '@/store/modeStore'
import type { Lead } from '@/types/models'

function clip(s: string, n: number) {
  const t = (s || '').trim()
  if (!t) return '—'
  return t.length > n ? `${t.slice(0, n)}…` : t
}

export function SearchLeadsPage() {
  const [recent, setRecent] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [pollRunning, setPollRunning] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [location, setLocation] = useState('')
  const [sourceFilter, setSourceFilter] = useState<'job_board' | 'yc' | 'local' | 'all'>('all')
  const [minScore, setMinScore] = useState(0)
  const [signalHiring, setSignalHiring] = useState(false)
  const [signalScaling, setSignalScaling] = useState(false)
  const [explorerBusy, setExplorerBusy] = useState(false)
  const [explorerErr, setExplorerErr] = useState<string | null>(null)
  const [explorerRows, setExplorerRows] = useState<ExplorerCompany[]>([])
  const [explorerInfo, setExplorerInfo] = useState<string>('')
  const mode = useModeStore((s) => s.mode)
  const setMode = useModeStore((s) => s.setMode)
  const hydrateMode = useModeStore((s) => s.hydrate)

  const loadRecent = useCallback(async () => {
    try {
      const r = await fetchLeads({ page: 1, page_size: 15, sort: 'created_at_desc' })
      setRecent(r.items)
    } catch {
      setRecent([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    hydrateMode()
  }, [hydrateMode])

  useEffect(() => {
    void loadRecent()
  }, [loadRecent])

  useEffect(() => {
    if (!pollRunning) return
    const id = window.setInterval(() => void loadRecent(), 4000)
    return () => window.clearInterval(id)
  }, [pollRunning, loadRecent])

  return (
    <div className="mx-auto max-w-[1200px] space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">Lead generation</h1>
        <p className="mt-2 max-w-2xl text-sm text-ink-muted">
          Choose how leads are generated. Explorer uses the company database for self-growing discovery, while LinkedIn
          keeps the current desktop capture flow unchanged. New leads appear in{' '}
          <Link to="/leads" className="font-medium text-amber-800 underline-offset-2 hover:underline dark:text-amber-300">
            Leads
          </Link>{' '}
          when ingest is enabled.
        </p>
      </div>

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark sm:p-6">
        <h2 className="type-panel-title">Mode selector</h2>
        <p className="mt-1 text-xs text-ink-muted">
          Switch between LinkedIn capture and Explorer Mode. Your selected mode is stored for this session. Default
          mode is Explorer.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setMode('linkedin')}
            className={`rounded-xl border px-3 py-1.5 text-xs ${mode === 'linkedin' ? 'border-amber-500/50 bg-amber-500/10 text-ink' : 'border-surface-border text-ink-muted'}`}
          >
            LinkedIn Mode
          </button>
          <button
            type="button"
            onClick={() => setMode('explorer')}
            className={`rounded-xl border px-3 py-1.5 text-xs ${mode === 'explorer' ? 'border-amber-500/50 bg-amber-500/10 text-ink' : 'border-surface-border text-ink-muted'}`}
          >
            Explorer Mode
          </button>
        </div>
        <div className="mt-3 rounded-xl border border-surface-border bg-field/40 px-4 py-3 text-xs text-ink-muted">
          Active mode: <span className="font-semibold text-ink">{mode === 'explorer' ? 'Explorer Mode' : 'LinkedIn Mode'}</span>
        </div>

        {mode === 'explorer' ? (
          <div className="mt-4 space-y-3">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="keyword (optional)"
                className="field-input rounded-xl px-3 py-2 text-sm"
              />
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="location (optional)"
                className="field-input rounded-xl px-3 py-2 text-sm"
              />
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value as 'job_board' | 'yc' | 'local' | 'all')}
                className="field-input rounded-xl px-3 py-2 text-sm"
              >
                <option value="all">Source: all</option>
                <option value="job_board">Source: job_board</option>
                <option value="yc">Source: yc</option>
                <option value="local">Source: local</option>
              </select>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                type="number"
                min={0}
                max={100}
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                placeholder="min score"
                className="field-input rounded-xl px-3 py-2 text-sm"
              />
              <label className="flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted">
                <input
                  type="checkbox"
                  checked={signalHiring}
                  onChange={(e) => setSignalHiring(e.target.checked)}
                  className="h-4 w-4 rounded border-surface-border accent-amber-600"
                />
                Hiring signal
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted">
                <input
                  type="checkbox"
                  checked={signalScaling}
                  onChange={(e) => setSignalScaling(e.target.checked)}
                  className="h-4 w-4 rounded border-surface-border accent-amber-600"
                />
                Scaling signal
              </label>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={explorerBusy}
                onClick={async () => {
                  const hasAnyFilter =
                    Boolean(keyword.trim()) ||
                    Boolean(location.trim()) ||
                    sourceFilter !== 'all' ||
                    Number(minScore || 0) > 0 ||
                    signalHiring ||
                    signalScaling
                  if (!hasAnyFilter) {
                    setExplorerErr('Add at least one filter before running Explorer.')
                    setExplorerRows([])
                    setExplorerInfo('')
                    return
                  }
                  setExplorerBusy(true)
                  setExplorerErr(null)
                  setExplorerInfo('')
                  setExplorerRows([])
                  try {
                    const r = await explorerSearchCompanies({
                      mode: 'explorer',
                      keyword: keyword.trim() || undefined,
                      location: location.trim() || undefined,
                      source_filter: sourceFilter,
                      min_score: minScore || 0,
                      signal_hiring: signalHiring,
                      signal_scaling: signalScaling,
                      min_results: 10,
                      max_results: 50,
                    })
                    setExplorerRows(r.results || [])
                    const info =
                      (r.results || []).length === 0 && r.ingestion?.triggered
                        ? 'Fetching more data'
                        : r.ingestion?.triggered
                          ? `Low DB results detected -> ingestion triggered. Saved: +${r.ingestion.saved_total.created} new, ${r.ingestion.saved_total.updated} updated.`
                          : `Results found directly from Company DB. ${r.count || 0} rows matched.`
                    setExplorerInfo(info)
                  } catch (e) {
                    setExplorerRows([])
                    setExplorerErr(getApiErrorMessage(e, 'Explorer search failed'))
                  } finally {
                    setExplorerBusy(false)
                  }
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs font-semibold text-amber-900 disabled:opacity-50 dark:text-amber-200"
              >
                {explorerBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                Run Explorer
              </button>
              {explorerInfo ? <span className="text-xs text-ink-muted">{explorerInfo}</span> : null}
            </div>
            {explorerErr ? <p className="text-xs text-red-600 dark:text-red-300">{explorerErr}</p> : null}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] text-left text-xs">
                <thead className="border-b border-surface-border text-ink-muted">
                  <tr>
                    <th className="px-2 py-2">Company</th>
                    <th className="px-2 py-2">Website</th>
                    <th className="px-2 py-2">Source</th>
                    <th className="px-2 py-2">Score</th>
                    <th className="px-2 py-2">Signals</th>
                  </tr>
                </thead>
                <tbody>
                  {explorerRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-2 py-3 text-ink-muted">
                        No explorer rows yet. Apply filters and run Explorer.
                      </td>
                    </tr>
                  ) : (
                    explorerRows.map((row) => (
                      <tr key={`${row.id}-${row.domain}`} className="border-b border-surface-border/70">
                        <td className="px-2 py-2">{row.company_name || '—'}</td>
                        <td className="max-w-[18rem] truncate px-2 py-2" title={row.website}>
                          {row.website || '—'}
                        </td>
                        <td className="px-2 py-2">{row.source || 'manual'}</td>
                        <td className="px-2 py-2">{Math.round(Number(row.score || 0))}</td>
                        <td className="px-2 py-2">
                          {[
                            row.signals?.hiring ? 'hiring' : '',
                            row.signals?.scaling ? 'scaling' : '',
                            row.signals?.content_gap ? 'content_gap' : '',
                            row.signals?.ads_gap ? 'ads_gap' : '',
                          ]
                            .filter(Boolean)
                            .join(', ') || '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-surface-border bg-field/40 px-4 py-3 text-sm text-ink-muted">
            LinkedIn Mode uses the existing desktop capture flow. Start the panel below and continue manual People
            search in your Chrome session.
          </div>
        )}
      </section>

      {mode === 'linkedin' ? <SeleniumLeadpilotPanel onRunningChange={setPollRunning} /> : null}

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark sm:p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="type-panel-title">Recently captured</h2>
            <p className="text-xs text-ink-muted">
              Refreshes while the desktop pipeline runs. Open a row in <span className="text-ink">Leads</span> to edit
              status and fields.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadRecent()}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted transition hover:bg-field"
          >
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
            Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">
              <tr className="border-b border-surface-border">
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Company</th>
                <th className="px-2 py-2">Role</th>
                <th className="px-2 py-2">Agency</th>
                <th className="px-2 py-2">Status</th>
                <th className="px-2 py-2">Problem</th>
                <th className="px-2 py-2">Solution</th>
                <th className="px-2 py-2">Conn.</th>
                <th className="px-2 py-2">Replied</th>
              </tr>
            </thead>
            <tbody>
              {loading && recent.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-2 py-10 text-center text-ink-muted">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : recent.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-2 py-8 text-center text-sm text-ink-muted">
                    No leads yet. Start the desktop pipeline above, then run a People search in Chrome.
                  </td>
                </tr>
              ) : (
                recent.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-surface-border/80 text-ink-muted last:border-0 hover:bg-amber-500/[0.04] dark:hover:bg-amber-400/[0.03]"
                  >
                    <td className="max-w-[7rem] truncate px-2 py-2.5 text-ink" title={row.full_name}>
                      {clip(row.full_name, 32)}
                    </td>
                    <td className="max-w-[7rem] truncate px-2 py-2.5" title={row.company_name}>
                      {clip(row.company_name, 28)}
                    </td>
                    <td className="max-w-[7rem] truncate px-2 py-2.5" title={row.title}>
                      {clip(row.title, 28)}
                    </td>
                    <td className="max-w-[4rem] truncate px-2 py-2.5" title={row.agency_type}>
                      {row.agency_type || '—'}
                    </td>
                    <td className="px-2 py-2.5">
                      <StatusBadge status={row.status || 'new'} />
                    </td>
                    <td className="max-w-[9rem] truncate px-2 py-2.5" title={row.problem_seen}>
                      {clip(row.problem_seen || '', 80)}
                    </td>
                    <td className="max-w-[10rem] truncate px-2 py-2.5" title={row.solution_text}>
                      {clip(row.solution_text || row.personalized_message || '', 100)}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-xs">{row.connection_sent || '—'}</td>
                    <td className="px-2 py-2.5 font-mono text-xs">{row.replied_yn || 'N'}</td>
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
