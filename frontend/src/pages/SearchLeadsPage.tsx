import { Loader2, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { useLocation, useNavigate } from 'react-router-dom'

import { ApiLoadError } from '@/components/ui/ApiLoadError'
import { FilterSelect } from '@/components/ui/FilterSelect'
import { SeleniumLeadpilotPanel } from '@/components/scraper/SeleniumLeadpilotPanel'
import { fetchScraperStatus, fetchScraperJob, startScraperJob, type ScraperJobStatus, type ScraperStatus } from '@/lib/api/scraper'
import { listPlatforms } from '@/lib/api/platforms'
import { cn } from '@/lib/utils/cn'
import type { PlatformRow } from '@/types/models'

function phaseLabel(phase: string, message: string): string {
  const m = message.toLowerCase()
  if (phase === 'extracting_data' && m.includes('profile')) return 'Opening prospect profile'
  switch (phase) {
    case 'queued':
      return 'Queued for execution'
    case 'searching':
      return 'Searching lead source'
    case 'extracting_data':
      return 'Extracting prospect data'
    case 'saving_lead':
      return 'Saving to prospect database'
    case 'completed':
      return 'Completed successfully'
    case 'failed':
      return 'Stopped with errors'
    default:
      return phase.replace(/_/g, ' ')
  }
}

function formatEta(sec: number | null | undefined): string {
  if (sec == null || !Number.isFinite(sec)) return '—'
  if (sec < 60) return `About ${Math.round(sec)} seconds`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `About ${m} minutes ${s} seconds`
}

function jobProgressPercent(job: ScraperJobStatus | null): number {
  if (!job) return 0
  if (job.completed && job.phase !== 'failed') return 100
  if (job.completed && job.phase === 'failed') return 100
  const target = Math.max(1, job.leads_target)
  const ratio = Math.min(1, job.leads_found / target)
  if (job.leads_found === 0 && (job.phase === 'searching' || job.phase === 'queued')) {
    return 12
  }
  return Math.max(4, Math.min(96, Math.round(ratio * 96)))
}

function cell(row: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = row[k]
    if (v != null && String(v).trim() !== '') return String(v)
  }
  return '—'
}

export function SearchLeadsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [platforms, setPlatforms] = useState<PlatformRow[]>([])
  const [scraper, setScraper] = useState<ScraperStatus | null>(null)
  const [loadingMeta, setLoadingMeta] = useState(true)

  const [platform, setPlatform] = useState('')
  const [keyword, setKeyword] = useState('')
  const [country, setCountry] = useState('')
  const [industry, setIndustry] = useState('')
  const [companySize, setCompanySize] = useState('')
  const [leadLimit, setLeadLimit] = useState(20)

  const [headless, setHeadless] = useState(true)
  const [profileContactEnrich, setProfileContactEnrich] = useState(false)
  const [delayMin, setDelayMin] = useState(3)
  const [delayMax, setDelayMax] = useState(5)
  const [maxScrollRounds, setMaxScrollRounds] = useState(12)

  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<ScraperJobStatus | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [metaLoadErr, setMetaLoadErr] = useState<string | null>(null)

  const loadMeta = useCallback(async () => {
    setLoadingMeta(true)
    setMetaLoadErr(null)
    try {
      const [plats, st] = await Promise.all([listPlatforms(), fetchScraperStatus()])
      const active = plats.filter((p) => p.active)
      setPlatforms(active)
      setScraper(st)
      setLeadLimit(st.max_leads_default)
      setDelayMin(st.delay_seconds_range[0])
      setDelayMax(st.delay_seconds_range[1])
      setPlatform((prev) => (prev && active.some((p) => p.slug === prev) ? prev : active[0]?.slug ?? ''))
    } catch {
      setMetaLoadErr('Could not load platforms or scraper defaults. Ensure the API is running, then retry.')
      setPlatforms([])
      setScraper(null)
    } finally {
      setLoadingMeta(false)
    }
  }, [])

  useEffect(() => {
    void loadMeta()
  }, [loadMeta])

  useEffect(() => {
    const st = location.state as { platform?: string } | null
    const slug = st?.platform?.trim()
    if (!slug) return
    if (!platforms.some((x) => x.slug === slug)) return
    setPlatform(slug)
    navigate(location.pathname, { replace: true, state: {} })
  }, [location.pathname, location.state, platforms, navigate])

  useEffect(() => {
    const onCh = () => void loadMeta()
    window.addEventListener('leadpilot-platforms-changed', onCh)
    return () => window.removeEventListener('leadpilot-platforms-changed', onCh)
  }, [loadMeta])

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    const tick = async () => {
      try {
        const j = await fetchScraperJob(jobId)
        if (cancelled) return
        setJob(j)
      } catch {
        if (!cancelled) setFormError('Unable to reach job status. Refresh the page and try again.')
      }
    }
    void tick()
    const id = window.setInterval(() => void tick(), 1000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [jobId])

  const progressPct = useMemo(() => jobProgressPercent(job), [job])

  const platformLabel = useMemo(() => {
    const p = platforms.find((x) => x.slug === (job?.platform || platform))
    return p?.label ?? job?.platform ?? platform ?? '—'
  }, [platforms, job, platform])

  async function onSearchLeads() {
    setFormError(null)
    if (!platform.trim() || !keyword.trim()) {
      setFormError('Select a lead source and enter a search keyword.')
      return
    }
    setStarting(true)
    setJob(null)
    setJobId(null)
    try {
      const accepted = await startScraperJob({
        platform: platform.trim(),
        keyword: keyword.trim(),
        country: country.trim(),
        industry: industry.trim(),
        company_size: companySize.trim(),
        lead_limit: leadLimit,
        headless,
        profile_contact_enrich: profileContactEnrich,
        delay_min_seconds: delayMin,
        delay_max_seconds: delayMax,
        max_scroll_rounds: maxScrollRounds,
      })
      setJobId(accepted.job_id)
      toast.success('Lead search job started')
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : 'Unable to start lead search. Try again or verify platform access.')
    } finally {
      setStarting(false)
    }
  }

  if (loadingMeta) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-sm text-ink-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading search configuration
      </div>
    )
  }

  if (metaLoadErr || !scraper) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <ApiLoadError
          title="Lead search unavailable"
          message={metaLoadErr ?? 'Scraper configuration was not returned from the API.'}
          onRetry={() => void loadMeta()}
        />
      </div>
    )
  }

  const cap = scraper.max_leads_cap
  const liveRows = job?.preview ?? []
  const statusLine = job
    ? phaseLabel(job.phase, job.message)
    : starting
      ? 'Starting job'
      : 'Idle'

  return (
    <div className="mx-auto max-w-[1400px] space-y-8">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,380px)_1fr]">
        <div className="space-y-5 rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark">
          <h2 className="type-panel-title mb-1">Search configuration</h2>
          <p className="mb-4 text-xs text-ink-muted">
            Search uses your <span className="text-ink">keyword</span>, <span className="text-ink">location</span>,{' '}
            <span className="text-ink">industry</span>, and <span className="text-ink">company size</span> together in
            the people search (same as typing them into LinkedIn&apos;s search box). Result cards usually show name,
            title, company, and profile URL only — email is rarely public unless you enable optional profile visits
            below.
          </p>

          <div className="space-y-4 text-sm">
            <div>
              <label htmlFor="search-lead-source" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Lead source
              </label>
              <FilterSelect
                id="search-lead-source"
                className="mt-1"
                options={platforms.map((p) => ({ value: p.slug, label: p.label }))}
                value={platform}
                onChange={setPlatform}
                placeholder="Choose lead source"
                disabled={platforms.length === 0}
                aria-label="Lead source"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Search keyword</label>
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="field-input mt-1"
                placeholder="Example: enterprise software sales leaders"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Location / region
              </label>
              <input
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="field-input mt-1"
                placeholder="Example: United States, London, Maharashtra…"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Industry</label>
              <input
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="field-input mt-1"
                placeholder="Example: information technology"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Company size</label>
              <input
                value={companySize}
                onChange={(e) => setCompanySize(e.target.value)}
                className="field-input mt-1"
                placeholder="Example: 50 to 500 employees"
              />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Lead limit</label>
              <input
                type="number"
                min={1}
                max={cap}
                value={leadLimit}
                onChange={(e) => setLeadLimit(Number(e.target.value))}
                className="field-input mt-1"
              />
            </div>

            <label className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-surface-border bg-field/50 px-3 py-2.5 dark:bg-zinc-900/40">
              <input
                type="checkbox"
                checked={profileContactEnrich}
                onChange={(e) => setProfileContactEnrich(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-surface-border text-amber-700 accent-amber-600"
              />
              <span className="text-xs leading-snug text-ink-muted">
                <span className="font-semibold text-ink">Fetch public email &amp; phone</span> (LinkedIn only): open
                each collected profile and read visible <span className="font-mono text-[11px]">mailto:</span> /{' '}
                <span className="font-mono text-[11px]">tel:</span> links. Slower; many profiles have no public email;
                server caps how many profiles are opened per run.
              </span>
            </label>

            <details className="rounded-xl border border-surface-border bg-field/50 px-3 py-2 dark:bg-zinc-900/40">
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Delay and safety
              </summary>
              <div className="mt-3 space-y-3">
                <label className="flex items-center gap-2 text-xs text-ink-muted">
                  <input type="checkbox" checked={headless} onChange={(e) => setHeadless(e.target.checked)} />
                  Run browser headless
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <span className="text-[10px] uppercase text-ink-subtle">Delay min (s)</span>
                    <input
                      type="number"
                      step={0.5}
                      min={1}
                      value={delayMin}
                      onChange={(e) => setDelayMin(Number(e.target.value))}
                      className="field-input mt-0.5 rounded-lg px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-ink-subtle">Delay max (s)</span>
                    <input
                      type="number"
                      step={0.5}
                      min={1}
                      value={delayMax}
                      onChange={(e) => setDelayMax(Number(e.target.value))}
                      className="field-input mt-0.5 rounded-lg px-2 py-1.5 text-sm"
                    />
                  </div>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-ink-subtle">Max scroll rounds</span>
                  <input
                    type="number"
                    min={1}
                    max={40}
                    value={maxScrollRounds}
                    onChange={(e) => setMaxScrollRounds(Number(e.target.value))}
                    className="field-input mt-0.5 rounded-lg px-2 py-1.5 text-sm"
                  />
                </div>
              </div>
            </details>
          </div>

          {formError ? (
            <p className="rounded-lg border border-rose-500/30 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/40 dark:text-rose-200">
              {formError}
            </p>
          ) : null}

          <button
            type="button"
            disabled={starting || Boolean(jobId && job && !job.completed)}
            onClick={() => void onSearchLeads()}
            className="btn-primary flex w-full items-center justify-center gap-2 py-3 text-sm disabled:opacity-50"
          >
            {starting || (jobId && job && !job.completed) ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching
              </>
            ) : (
              <>
                <Search className="h-4 w-4" />
                Start Lead Search
              </>
            )}
          </button>
          <p className="text-xs text-ink-subtle">
            Uses your saved platform session for the selected lead source. Maximum {cap} leads per run. Engine{' '}
            {scraper.engine}.
          </p>
        </div>

        <div className="space-y-6">
          <div
            className={cn(
              'rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark',
              job?.phase === 'failed' && 'border-rose-500/30',
            )}
          >
            <h2 className="type-panel-title mb-1">Scraping activity</h2>
            <p className="mb-4 text-xs text-ink-muted">
              Live job status for this prospecting run. Duplicate rows are removed before lead management ingestion.
            </p>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-200 dark:bg-zinc-800">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  job?.phase === 'failed'
                    ? 'bg-red-500'
                    : 'bg-gradient-to-r from-amber-500 to-emerald-600 dark:from-amber-400 dark:to-emerald-500',
                )}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wider text-ink-muted">Job status</dt>
                <dd className="mt-0.5 font-medium text-ink">{statusLine}</dd>
                {job?.message ? <dd className="mt-1 text-xs text-ink-subtle">{job.message}</dd> : null}
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wider text-ink-muted">Active lead source</dt>
                <dd className="mt-0.5 text-ink-muted">{platformLabel}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wider text-ink-muted">Pagination position</dt>
                <dd className="mt-0.5 font-mono text-ink-muted">{job?.page ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wider text-ink-muted">Leads collected</dt>
                <dd className="mt-0.5 font-mono text-ink-muted">
                  {job ? `${job.leads_found} / ${job.leads_target}` : '—'}
                  {job && job.duplicates_removed > 0 ? (
                    <span className="ml-2 text-xs text-ink-subtle">
                      ({job.duplicates_removed} duplicate records skipped)
                    </span>
                  ) : null}
                </dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wider text-ink-muted">Estimated time remaining</dt>
                <dd className="mt-0.5 text-ink-muted">{job ? formatEta(job.eta_seconds) : '—'}</dd>
              </div>
            </dl>
            {job?.error ? (
              <p className="mt-4 rounded-lg border border-rose-500/30 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950/40 dark:text-rose-200">
                {job.error}
              </p>
            ) : null}
            {job?.completed && job.result ? (
              <p className="mt-4 rounded-lg border border-emerald-500/25 bg-emerald-50 px-3 py-2 text-xs text-emerald-900 dark:bg-emerald-950/35 dark:text-emerald-100">
                Saved {(job.result.saved as number) ?? job.leads_found} leads · total seen{' '}
                {(job.result.total_found as number) ?? '—'} · CSV {(job.result.csv_file as string) || '—'}
              </p>
            ) : null}
          </div>

          <div className="overflow-hidden rounded-2xl border border-surface-border bg-premium-card-light shadow-card dark:bg-premium-card-dark">
            <div className="border-b border-surface-border px-4 py-3">
              <h2 className="font-display text-lg font-semibold tracking-tight text-ink">Live prospect preview</h2>
              <p className="text-xs text-ink-subtle">
                Rows appear as the job discovers contacts. Final qualification still happens in lead management.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm font-sans">
                <thead className="sticky top-0 z-10 bg-surface-raised/95 backdrop-blur-md dark:bg-zinc-950/90">
                  <tr className="border-b border-surface-border text-xs uppercase tracking-wider text-ink-muted">
                    <th className="px-4 py-2 font-medium">Contact name</th>
                    <th className="px-4 py-2 font-medium">Title</th>
                    <th className="px-4 py-2 font-medium">Organization</th>
                    <th className="px-4 py-2 font-medium">Profile URL</th>
                  </tr>
                </thead>
                <tbody>
                  {liveRows.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="px-4 py-10 text-center text-ink-muted">
                        {jobId && job && !job.completed ? (
                          <span className="inline-flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Waiting for first leads
                          </span>
                        ) : (
                          'Start a lead search to preview new prospects here.'
                        )}
                      </td>
                    </tr>
                  ) : (
                    liveRows.map((row, i) => (
                      <tr
                        key={i}
                        className={cn(
                          'border-b border-surface-border/80 text-ink-muted transition hover:bg-amber-500/[0.05] dark:hover:bg-amber-400/[0.04]',
                          i % 2 === 1 ? 'bg-field/35 dark:bg-white/[0.02]' : '',
                          'last:border-0',
                        )}
                      >
                        <td className="max-w-[180px] truncate px-4 py-2.5">{cell(row, 'full_name', 'name')}</td>
                        <td className="max-w-[200px] truncate px-4 py-2.5">{cell(row, 'title')}</td>
                        <td className="max-w-[180px] truncate px-4 py-2.5">{cell(row, 'company_name', 'company')}</td>
                        <td className="max-w-[260px] truncate px-4 py-2.5 font-mono text-xs text-amber-700 dark:text-amber-300">
                          {cell(row, 'url', 'linkedin_url') !== '—' ? (
                            <a
                              href={cell(row, 'url', 'linkedin_url')}
                              target="_blank"
                              rel="noreferrer"
                              className="hover:underline"
                            >
                              {cell(row, 'url', 'linkedin_url')}
                            </a>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <SeleniumLeadpilotPanel />
    </div>
  )
}
