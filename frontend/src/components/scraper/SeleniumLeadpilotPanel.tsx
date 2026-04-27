import { Loader2, Square, Zap } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'

import {
  fetchSeleniumLeadpilotStatus,
  startSeleniumLeadpilot,
  stopSeleniumLeadpilot,
  type LinkedinSessionCacheInfo,
  type SeleniumLeadpilotStatus,
} from '@/lib/api/seleniumLeadpilot'
import { cn } from '@/lib/utils/cn'

export function SeleniumLeadpilotPanel({
  onRunningChange,
}: {
  /** Fires when pipeline state is running (poll parent tables, etc.). */
  onRunningChange?: (running: boolean) => void
} = {}) {
  const [st, setSt] = useState<SeleniumLeadpilotStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [maxLeads, setMaxLeads] = useState(10)
  const [testMode, setTestMode] = useState(true)
  const [skipEnrich, setSkipEnrich] = useState(false)
  const [skipScoring, setSkipScoring] = useState(false)
  const [output, setOutput] = useState('')
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const load = useCallback(async () => {
    try {
      const s = await fetchSeleniumLeadpilotStatus()
      setSt(s)
    } catch {
      setSt(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (!st || st.state !== 'running') return
    const t = window.setInterval(() => void load(), 2000)
    return () => window.clearInterval(t)
  }, [st, load])

  useEffect(() => {
    onRunningChange?.(Boolean(st && st.state === 'running'))
  }, [st, onRunningChange])

  const onStart = async () => {
    setStarting(true)
    try {
      await startSeleniumLeadpilot({
        max_leads: maxLeads,
        test: testMode,
        skip_enrich: skipEnrich,
        skip_scoring: skipScoring,
        output: output.trim() || null,
        lnn_base_url: null,
        skip_preflight: false,
      })
      toast.success('Desktop LinkedIn pipeline started on the server')
      await load()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Could not start pipeline'
      toast.error(msg)
    } finally {
      setStarting(false)
    }
  }

  const onStop = async () => {
    setStopping(true)
    try {
      await stopSeleniumLeadpilot()
      toast.message('Stop requested')
      await load()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Stop failed')
    } finally {
      setStopping(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-2xl border border-surface-border bg-premium-card-light p-6 text-sm text-ink-muted dark:bg-premium-card-dark">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading desktop pipeline status
      </div>
    )
  }

  if (!st?.available) {
    return (
      <div className="rounded-2xl border border-amber-500/25 bg-amber-50/80 p-5 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
        <p className="font-semibold">LinkedIn desktop pipeline (Selenium)</p>
        <p className="mt-1 text-xs opacity-90">
          Not available in this deployment — the <span className="font-mono">backend/leadpilot</span> package is missing
          on the API host.
        </p>
      </div>
    )
  }

  const running = st.state === 'running'
  const tail = st.log_tail?.length ? st.log_tail : [st.message || '—']

  return (
    <div
      className={cn(
        'rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark',
        st.state === 'failed' && 'border-rose-500/30',
        st.state === 'completed' && st.returncode === 0 && 'border-emerald-500/25',
      )}
    >
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="type-panel-title">LinkedIn desktop pipeline (Selenium)</h2>
          <p className="mt-1 max-w-[720px] text-xs text-ink-muted">
            Runs <span className="font-mono">python -m backend.leadpilot</span> on the server. After start, you get a
            short countdown — switch to Chrome on <strong>People</strong> search results (no need to press Enter in the
            log).             Uses launch or attach from <span className="font-mono">scraper.env</span>. Set{' '}
            <span className="font-mono">CHROME_USER_DATA_DIR</span> to keep the same LinkedIn login between runs;
            we also record last successful capture in <span className="font-mono">sessions/linkedin_session_cache.json</span>{' '}
            (default: remind after ~7 days — <span className="font-mono">LEADPILOT_LINKEDIN_SESSION_DAYS</span>).
            Leads go to Excel and the <strong>Leads</strong> list when ingest is enabled.
          </p>
        </div>
        <span
          className={cn(
            'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
            running && 'bg-amber-500/15 text-amber-800 dark:text-amber-200',
            st.state === 'idle' && 'bg-zinc-500/10 text-ink-muted',
            st.state === 'completed' && st.returncode === 0 && 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-200',
            st.state === 'failed' && 'bg-rose-500/10 text-rose-800 dark:text-rose-200',
          )}
        >
          {st.state}
        </span>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Max leads</label>
          <input
            type="number"
            min={1}
            max={500}
            value={maxLeads}
            onChange={(e) => setMaxLeads(Number(e.target.value))}
            disabled={running}
            className="field-input mt-1"
          />
        </div>
        <div>
          <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted">Output .xlsx (optional)</label>
          <input
            value={output}
            onChange={(e) => setOutput(e.target.value)}
            disabled={running}
            placeholder="leadpilot_runs.xlsx"
            className="field-input mt-1 font-mono text-xs"
          />
        </div>
        <div className="flex flex-col justify-end gap-2 sm:col-span-2 lg:col-span-2">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-muted">
            <input
              type="checkbox"
              checked={testMode}
              onChange={(e) => setTestMode(e.target.checked)}
              disabled={running}
              className="h-4 w-4 rounded border-surface-border accent-amber-600"
            />
            Test mode (cap 10 leads, verbose)
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-muted">
            <input
              type="checkbox"
              checked={skipEnrich}
              onChange={(e) => setSkipEnrich(e.target.checked)}
              disabled={running}
              className="h-4 w-4 rounded border-surface-border accent-amber-600"
            />
            Skip Apollo / Skrapp enrichment
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-ink-muted">
            <input
              type="checkbox"
              checked={skipScoring}
              onChange={(e) => setSkipScoring(e.target.checked)}
              disabled={running}
              className="h-4 w-4 rounded border-surface-border accent-amber-600"
            />
            Skip scoring
          </label>
        </div>
      </div>

      {(() => {
        const ls = st.linkedin_session as LinkedinSessionCacheInfo | { message?: string; has_cache?: boolean } | undefined
        if (!ls || !('message' in ls) || !ls.message) return null
        const full = ls as LinkedinSessionCacheInfo
        const stale = full.has_cache && full.within_policy === false
        return (
          <p
            className={`mb-3 rounded-xl border px-3 py-2 text-xs ${
              stale
                ? 'border-amber-500/30 bg-amber-50/80 text-amber-950 dark:bg-amber-950/25 dark:text-amber-100'
                : 'border-surface-border bg-field/50 text-ink-muted dark:bg-zinc-900/40'
            }`}
          >
            <span className="font-semibold text-ink">LinkedIn session cache: </span>
            {ls.message}
            {typeof full.age_days === 'number' && full.last_verified_at ? (
              <span className="mt-1 block font-mono text-[10px] opacity-80">
                Last capture: {full.last_verified_at} · age {full.age_days}d · policy {full.policy_days}d
              </span>
            ) : null}
          </p>
        )
      })()}
      <p className="mb-3 text-xs text-ink-subtle">
        {st.message} {st.pid != null && running ? `· pid ${st.pid}` : null}
        {st.command ? (
          <span className="mt-1 block font-mono text-[10px] text-ink-subtle/80">{st.command}</span>
        ) : null}
      </p>

      <div className="mb-4 max-h-48 overflow-y-auto rounded-xl border border-surface-border bg-field/50 p-3 font-mono text-[10px] leading-relaxed text-ink-muted dark:bg-zinc-900/50">
        {tail.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-all">
            {line}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={running || starting}
          onClick={() => void onStart()}
          className="btn-primary inline-flex items-center justify-center gap-2 px-4 py-2.5 text-sm disabled:opacity-50"
        >
          {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {running ? 'Running…' : 'Start desktop pipeline'}
        </button>
        <button
          type="button"
          disabled={!running || stopping}
          onClick={() => void onStop()}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-surface-border px-4 py-2.5 text-sm text-ink-muted transition hover:bg-field disabled:opacity-50"
        >
          {stopping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
          Stop
        </button>
        <button
          type="button"
          onClick={() => void load()}
          className="inline-flex items-center justify-center rounded-xl border border-transparent px-3 py-2.5 text-sm text-ink-subtle hover:text-ink"
        >
          Refresh log
        </button>
      </div>
    </div>
  )
}
