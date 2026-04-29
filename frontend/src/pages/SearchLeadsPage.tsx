import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { SeleniumLeadpilotPanel } from '@/components/scraper/SeleniumLeadpilotPanel'
import { StatusBadge } from '@/components/ui/Badge'
import {
  checkLinkedinSession,
  explorerSearchCompanies,
  runScheduledJob,
  type ExplorerCompany,
  type LinkedinSessionCheckResponse,
} from '@/lib/api/companies'
import { getApiErrorMessage } from '@/lib/api/client'
import { fetchLeads } from '@/lib/api/leads'
import { getEnabledExplorerSources, getEnabledSignalFilters, getHighScoreThreshold } from '@/lib/config/userConfigRules'
import { useModeStore } from '@/store/modeStore'
import { useUserConfigStore } from '@/store/userConfigStore'
import type { Lead } from '@/types/models'

function clip(s: string, n: number) {
  const t = (s || '').trim()
  if (!t) return '—'
  return t.length > n ? `${t.slice(0, n)}…` : t
}

function titleizeSource(source: string) {
  const text = (source || '').trim()
  if (!text) return 'Manual'
  return text
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export function SearchLeadsPage() {
  const [recent, setRecent] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [pollRunning, setPollRunning] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [location, setLocation] = useState('')
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [minScore, setMinScore] = useState(0)
  const [signalHiring, setSignalHiring] = useState(false)
  const [signalScaling, setSignalScaling] = useState(false)
  const [explorerBusy, setExplorerBusy] = useState(false)
  const [explorerErr, setExplorerErr] = useState<string | null>(null)
  const [explorerRows, setExplorerRows] = useState<ExplorerCompany[]>([])
  const [explorerInfo, setExplorerInfo] = useState<string>('')
  const [sessionBusy, setSessionBusy] = useState(false)
  const [linkedinRunBusy, setLinkedinRunBusy] = useState(false)
  const [sessionStatus, setSessionStatus] = useState<LinkedinSessionCheckResponse | null>(null)
  const [linkedinJobMsg, setLinkedinJobMsg] = useState<string>('')
  const [linkedinCandidates, setLinkedinCandidates] = useState(0)
  const mode = useModeStore((s) => s.mode)
  const setMode = useModeStore((s) => s.setMode)
  const hydrateMode = useModeStore((s) => s.hydrate)
  const adminConfig = useUserConfigStore((s) => s.adminConfig)
  const lastConfigEventTs = useUserConfigStore((s) => s.lastEventTs)
  const lastChangedFields = useUserConfigStore((s) => s.lastChangedFields)
  const isSaturday = new Date().getDay() === 6
  const allowedSources = getEnabledExplorerSources(adminConfig)
  const enabledSignals = getEnabledSignalFilters(adminConfig)
  const defaultKeyword = String((adminConfig.targeting?.keywords || [])[0] || '').trim()
  const defaultLocation = String((adminConfig.targeting?.locations || [])[0] || '').trim()
  const defaultMinScore = getHighScoreThreshold(adminConfig)

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
    if (selectedSources.length === 0 && allowedSources.length > 0) {
      setSelectedSources(allowedSources)
    }
    if (selectedSources.length > 0) {
      const nextSelected = selectedSources.filter((src) => allowedSources.includes(src))
      if (nextSelected.length !== selectedSources.length) {
        setSelectedSources(nextSelected)
      }
    }
    if (!keyword.trim()) {
      const firstKeyword = String((adminConfig.targeting?.keywords || [])[0] || '').trim()
      if (firstKeyword) setKeyword(firstKeyword)
    }
    if (!location.trim()) {
      const firstLocation = String((adminConfig.targeting?.locations || [])[0] || '').trim()
      if (firstLocation) setLocation(firstLocation)
    }
    if (Number(minScore || 0) <= 0) {
      const minCompanyScore = getHighScoreThreshold(adminConfig)
      if (minCompanyScore > 0) setMinScore(minCompanyScore)
    }
    if (sourceFilter !== 'all' && !allowedSources.includes(sourceFilter)) {
      setSourceFilter('all')
    }
    if (!enabledSignals.hiring && signalHiring) {
      setSignalHiring(false)
    }
    if (!enabledSignals.scaling && signalScaling) {
      setSignalScaling(false)
    }
  }, [adminConfig, allowedSources, enabledSignals, keyword, location, minScore, selectedSources, sourceFilter, signalHiring, signalScaling])

  useEffect(() => {
    if (mode !== 'linkedin') return
    if (!isSaturday) return
    void (async () => {
      try {
        setSessionBusy(true)
        const s = await checkLinkedinSession()
        setSessionStatus(s)
      } catch {
        setSessionStatus(null)
      } finally {
        setSessionBusy(false)
      }
    })()
  }, [isSaturday, mode])

  useEffect(() => {
    if (!pollRunning) return
    const id = window.setInterval(() => void loadRecent(), 4000)
    return () => window.clearInterval(id)
  }, [pollRunning, loadRecent])

  const runExplorer = useCallback(async () => {
    setExplorerBusy(true)
    setExplorerErr(null)
    try {
      const r = await explorerSearchCompanies({
        mode: 'explorer',
        keyword: keyword.trim() || undefined,
        location: location.trim() || undefined,
        source_filter: sourceFilter,
        min_score: minScore || 0,
        signal_hiring: enabledSignals.hiring ? signalHiring : false,
        signal_scaling: enabledSignals.scaling ? signalScaling : false,
        min_results: 10,
        max_results: 50,
        sources: selectedSources,
      })
      setExplorerRows(r.results || [])
      const info =
        (r.results || []).length === 0 && r.ingestion?.triggered
          ? 'Fetching more data'
          : r.ingestion?.triggered
            ? `Low DB results detected -> ingestion triggered. Saved: +${r.ingestion.saved_total.created} new, ${r.ingestion.saved_total.updated} updated.`
            : `Results found directly from Company DB. ${r.count || 0} rows matched.`
      const metaHints: string[] = []
      if (r.effective_filters && r.effective_filters.source_filter !== sourceFilter && sourceFilter !== 'all') {
        metaHints.push('source filter adjusted by admin policy')
      }
      if (signalHiring && !r.effective_filters?.signal_hiring) {
        metaHints.push('hiring signal filter disabled by admin')
      }
      if (signalScaling && !r.effective_filters?.signal_scaling) {
        metaHints.push('scaling signal filter disabled by admin')
      }
      setExplorerInfo(metaHints.length ? `${info} (${metaHints.join(', ')})` : info)
    } catch (e) {
      setExplorerRows([])
      setExplorerErr(getApiErrorMessage(e, 'Explorer search failed'))
    } finally {
      setExplorerBusy(false)
    }
  }, [enabledSignals.hiring, enabledSignals.scaling, keyword, location, minScore, selectedSources, signalHiring, signalScaling, sourceFilter])

  useEffect(() => {
    if (!lastConfigEventTs || mode !== 'explorer') return
    const affectsExplorer = lastChangedFields.some((field) =>
      field.startsWith('admin_config.targeting') ||
      field.startsWith('admin_config.sources') ||
      field.startsWith('admin_config.signals_config') ||
      field.startsWith('admin_config.scoring_weights'),
    )
    if (!affectsExplorer) return
    void loadRecent()
    if (explorerRows.length > 0 || explorerInfo) {
      void runExplorer()
    }
  }, [explorerInfo, explorerRows.length, lastChangedFields, lastConfigEventTs, loadRecent, mode, runExplorer])

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
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-900 dark:text-emerald-200">
              Explorer is synced to the latest admin config.
              {defaultKeyword ? ` Keyword default: ${defaultKeyword}.` : ''}
              {defaultLocation ? ` Location default: ${defaultLocation}.` : ''}
              {defaultMinScore > 0 ? ` Score floor: ${defaultMinScore}.` : ''}
              {allowedSources.length ? ` Sources: ${allowedSources.join(', ')}.` : ''}
            </div>
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
                onChange={(e) => setSourceFilter(e.target.value)}
                className="field-input rounded-xl px-3 py-2 text-sm"
              >
                <option value="all">Source: all</option>
                {allowedSources.map((src) => (
                  <option key={src} value={src}>
                    Source: {src}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-xs text-ink-muted">
              Source filter controls which origin is shown in Explorer results. Each result includes the source that produced
              the company row.
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
              {enabledSignals.hiring ? (
                <label className="flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted">
                  <input
                    type="checkbox"
                    checked={signalHiring}
                    onChange={(e) => setSignalHiring(e.target.checked)}
                    className="h-4 w-4 rounded border-surface-border accent-amber-600"
                  />
                  Hiring signal
                </label>
              ) : (
                <div className="rounded-xl border border-surface-border/70 px-3 py-2 text-xs text-ink-subtle">Hiring signal disabled by admin</div>
              )}
              {enabledSignals.scaling ? (
                <label className="flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted">
                  <input
                    type="checkbox"
                    checked={signalScaling}
                    onChange={(e) => setSignalScaling(e.target.checked)}
                    className="h-4 w-4 rounded border-surface-border accent-amber-600"
                  />
                  Scaling signal
                </label>
              ) : (
                <div className="rounded-xl border border-surface-border/70 px-3 py-2 text-xs text-ink-subtle">Scaling signal disabled by admin</div>
              )}
            </div>
            <div className="rounded-xl border border-surface-border bg-field/30 px-3 py-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Active sources before run</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {allowedSources.map((src) => {
                  const checked = selectedSources.includes(src)
                  return (
                    <label key={src} className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          setSelectedSources((prev) => {
                            if (e.target.checked) {
                              return prev.includes(src) ? prev : [...prev, src]
                            }
                            return prev.filter((item) => item !== src)
                          })
                        }}
                        className="h-4 w-4 rounded border-surface-border accent-amber-600"
                      />
                      {src}
                    </label>
                  )
                })}
              </div>
              <p className="mt-2 text-xs text-ink-subtle">
                Only admin-enabled sources are shown here. Explorer will run against the selected active sources.
              </p>
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
                    selectedSources.length > 0 ||
                    Number(minScore || 0) > 0 ||
                    (enabledSignals.hiring && signalHiring) ||
                    (enabledSignals.scaling && signalScaling)
                  if (!hasAnyFilter) {
                    setExplorerErr('Add at least one filter before running Explorer.')
                    setExplorerRows([])
                    setExplorerInfo('')
                    return
                  }
                  if (selectedSources.length === 0) {
                    setExplorerErr('Select at least one active source before running Explorer.')
                    setExplorerRows([])
                    setExplorerInfo('')
                    return
                  }
                  setExplorerInfo('')
                  setExplorerRows([])
                  await runExplorer()
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
                          {row.website ? (
                            <a
                              href={row.website}
                              target="_blank"
                              rel="noreferrer"
                              className="text-amber-800 underline underline-offset-2 hover:text-amber-700 dark:text-amber-300 dark:hover:text-amber-200"
                            >
                              {row.website}
                            </a>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td className="px-2 py-2">
                          <span className="inline-flex rounded-full border border-surface-border bg-field/40 px-2 py-0.5 text-[11px] font-medium text-ink">
                            {titleizeSource(row.source || 'manual')}
                          </span>
                        </td>
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
          <div className="mt-4 space-y-3">
            <div className="rounded-xl border border-surface-border bg-field/40 px-4 py-3 text-sm text-ink-muted">
              LinkedIn Mode uses the existing desktop capture flow. Start the panel below and continue manual People
              search in your Chrome session.
            </div>

            {isSaturday ? (
              <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="inline-flex items-center gap-2 text-sm font-semibold text-amber-900 dark:text-amber-200">
                      <AlertTriangle className="h-4 w-4" />
                      LinkedIn job ready
                    </p>
                    <p className="text-xs text-amber-900/90 dark:text-amber-200/90">
                      Saturday flow: open system, complete manual LinkedIn login if needed, then run LinkedIn expansion.
                    </p>
                    <p className="text-xs text-ink-muted">
                      Session:{' '}
                      {sessionBusy
                        ? 'Checking...'
                        : sessionStatus
                          ? sessionStatus.requires_manual_login
                            ? 'Expired - manual login required'
                            : 'Valid - ready to run'
                          : 'Not checked'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={sessionBusy}
                      onClick={async () => {
                        setLinkedinJobMsg('')
                        setLinkedinCandidates(0)
                        try {
                          setSessionBusy(true)
                          const s = await checkLinkedinSession()
                          setSessionStatus(s)
                          setLinkedinJobMsg(
                            s.requires_manual_login
                              ? 'Session expired. Please log in to LinkedIn manually, then click Run LinkedIn Expansion.'
                              : 'Session is valid. You can run LinkedIn Expansion now.',
                          )
                        } catch (e) {
                          setLinkedinJobMsg(getApiErrorMessage(e, 'Failed to check LinkedIn session'))
                        } finally {
                          setSessionBusy(false)
                        }
                      }}
                      className="rounded-xl border border-surface-border px-3 py-2 text-xs text-ink-muted hover:bg-field disabled:opacity-50"
                    >
                      {sessionBusy ? 'Checking...' : 'Check session'}
                    </button>
                    <button
                      type="button"
                      disabled={linkedinRunBusy || sessionBusy}
                      onClick={async () => {
                        setLinkedinJobMsg('')
                        setLinkedinCandidates(0)
                        try {
                          setLinkedinRunBusy(true)
                          const run = await runScheduledJob('saturday_linkedin')
                          const paused = Boolean(run.result?.paused || run.session_gate?.paused)
                          if (paused) {
                            setLinkedinJobMsg(
                              String(
                                run.result?.instructions ||
                                  'LinkedIn session expired. Login manually, then run LinkedIn Expansion again.',
                              ),
                            )
                          } else {
                            const cands = Array.isArray(run.result?.candidates) ? run.result.candidates.length : 0
                            setLinkedinCandidates(cands)
                            setLinkedinJobMsg(`LinkedIn expansion ran successfully. Prepared ${cands} company candidates.`)
                          }
                        } catch (e) {
                          setLinkedinJobMsg(getApiErrorMessage(e, 'Failed to run LinkedIn expansion'))
                        } finally {
                          setLinkedinRunBusy(false)
                        }
                      }}
                      className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 hover:bg-amber-500/20 disabled:opacity-50 dark:text-amber-200"
                    >
                      {linkedinRunBusy ? 'Running...' : 'Run LinkedIn Expansion'}
                    </button>
                  </div>
                </div>
                {linkedinJobMsg ? <p className="mt-2 text-xs text-ink">{linkedinJobMsg}</p> : null}
                {linkedinCandidates > 0 ? <p className="mt-2 text-xs text-ink">Candidates prepared: {linkedinCandidates}</p> : null}
              </div>
            ) : null}
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
