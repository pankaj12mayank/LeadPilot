import { Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { Badge, StatusBadge } from '@/components/ui/Badge'
import { FilterSelect } from '@/components/ui/FilterSelect'
import { fetchLeads } from '@/lib/api/leads'
import { getHighScoreThreshold, getPriorityTierFromScore } from '@/lib/config/userConfigRules'
import { leadStatusLabel } from '@/lib/copy/appCopy'
import { useUserConfigStore } from '@/store/userConfigStore'
import type { Lead } from '@/types/models'

function isClosedStatus(status: string) {
  const s = (status || '').trim().toLowerCase().replace(/\s+/g, '_')
  return s === 'close' || s === 'closed' || s === 'converted'
}

function fmtShort(iso: string) {
  if (!iso) return '—'
  return iso.length >= 10 ? iso.slice(0, 16).replace('T', ' ') : iso
}

function priorityVariant(priority: string): 'hot' | 'warm' | 'cold' | 'muted' {
  const p = String(priority || '').trim().toLowerCase()
  if (p === 'hot') return 'hot'
  if (p === 'warm') return 'warm'
  if (p === 'cold') return 'cold'
  return 'muted'
}

function priorityLabel(priority: string): string {
  const p = String(priority || '').trim().toLowerCase()
  if (p === 'hot' || p === 'warm' || p === 'cold') {
    return p.charAt(0).toUpperCase() + p.slice(1)
  }
  return 'Unranked'
}

function priorityWeight(level: string | undefined): number {
  const normalized = String(level || '').trim().toLowerCase()
  if (normalized === 'high') return 18
  if (normalized === 'medium') return 9
  if (normalized === 'low') return 3
  return 0
}

const STATUS_OPTIONS = [
  { value: '', label: 'All active statuses' },
  { value: 'new', label: 'New' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'replied', label: 'Replied' },
  { value: 'follow_up', label: 'Follow-up' },
]

export function OutreachQueuePage() {
  const adminConfig = useUserConfigStore((s) => s.adminConfig)
  const lastConfigEventTs = useUserConfigStore((s) => s.lastEventTs)
  const highScoreThreshold = getHighScoreThreshold(adminConfig)
  const [rows, setRows] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [minScore, setMinScore] = useState(0)
  const [preset, setPreset] = useState<'none' | 'hot' | 'hiring' | 'quick_wins' | 'growth'>('none')
  const [highlightReady, setHighlightReady] = useState(false)
  const [skippedBrokenRows, setSkippedBrokenRows] = useState(0)
  const [err, setErr] = useState<string | null>(null)
  const preferredKeywords = useMemo(
    () =>
      (adminConfig.targeting?.preferred_keywords || [])
        .map((x: any) => String(x || '').trim().toLowerCase())
        .filter(Boolean),
    [adminConfig.targeting?.preferred_keywords],
  )
  const preferredLocations = useMemo(
    () =>
      (adminConfig.targeting?.preferred_locations || [])
        .map((x: any) => String(x || '').trim().toLowerCase())
        .filter(Boolean),
    [adminConfig.targeting?.preferred_locations],
  )
  const preferredIndustries = useMemo(
    () =>
      (adminConfig.targeting?.industries || [])
        .map((x: any) => String(x || '').trim().toLowerCase())
        .filter(Boolean),
    [adminConfig.targeting?.industries],
  )
  
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
    const roleWeight = Number(adminConfig.scoring_weights?.role_weight || 40)
    const signalWeight = Number(adminConfig.scoring_weights?.signal_weight || 35)
    const dataWeight = Number(adminConfig.scoring_weights?.data_weight || 25)
    const totalWeight = Math.max(1, roleWeight + signalWeight + dataWeight)
    const signalBoostFactor = signalWeight / totalWeight
    const roleBoostFactor = roleWeight / totalWeight

    function targetFitBoost(lead: Lead): number {
      const title = String(lead.title || '').toLowerCase()
      const company = String(lead.company_name || '').toLowerCase()
      const industry = String(lead.industry || '').toLowerCase()
      const location = String(lead.location || '').toLowerCase()
      const keywordHit = preferredKeywords.some((k: any) => title.includes(k) || company.includes(k))
      const locationHit = preferredLocations.some((loc: any) => location.includes(loc))
      const industryHit = preferredIndustries.some((ind: any) => industry.includes(ind))
      let boost = 0
      if (keywordHit) boost += 8
      if (locationHit) boost += 6
      if (industryHit) boost += 6
      return boost * roleBoostFactor
    }

    function scoringBoost(lead: Lead): number {
      const sig = Number(lead.signal_hiring || 0) + Number(lead.signal_scaling || 0)
      const contentGap = Number(lead.signal_content_gap || 0)
      const adsGap = Number(lead.signal_ads_gap || 0)
      const raw = sig * 8 + contentGap * 3 + adsGap * 3
      return raw * signalBoostFactor
    }

    function taskPriorityBoost(lead: Lead): number {
      const sourcePlatform = String(lead.source_platform || '').trim().toLowerCase()
      let boost = 0
      if (sourcePlatform === 'linkedin') {
        boost += priorityWeight(adminConfig.task_priority?.linkedin)
      } else {
        boost += priorityWeight(adminConfig.task_priority?.ingestion)
      }
      if (Number(lead.score || 0) >= highScoreThreshold) {
        boost += priorityWeight(adminConfig.task_priority?.scoring)
      }
      if (!String(lead.personalized_message || '').trim()) {
        boost += priorityWeight(adminConfig.task_priority?.enrichment)
      }
      return boost
    }

    return (rows || [])
      .filter((x) => !isClosedStatus(x.status || ''))
      .filter((x) => Number(x.score || 0) >= Number(minScore || 0))
      .filter((x) => {
        if (preset === 'hiring') return Number(x.signal_hiring || 0) >= 1
        if (preset === 'quick_wins') return Number(x.signal_content_gap || 0) >= 1
        if (preset === 'growth') return Number(x.signal_scaling || 0) >= 1
        return true
      })
      .sort((a, b) => {
        const aPriority = Number(a.score || 0) + scoringBoost(a) + targetFitBoost(a) + taskPriorityBoost(a)
        const bPriority = Number(b.score || 0) + scoringBoost(b) + targetFitBoost(b) + taskPriorityBoost(b)
        if (bPriority !== aPriority) return bPriority - aPriority
        return Number(b.score || 0) - Number(a.score || 0)
      })
  }, [
    adminConfig.scoring_weights?.data_weight,
    adminConfig.scoring_weights?.role_weight,
    adminConfig.scoring_weights?.signal_weight,
    adminConfig.task_priority?.enrichment,
    adminConfig.task_priority?.ingestion,
    adminConfig.task_priority?.linkedin,
    adminConfig.task_priority?.scoring,
    highScoreThreshold,
    minScore,
    preferredIndustries,
    preferredKeywords,
    preferredLocations,
    preset,
    rows,
  ])

  function applyPreset(p: 'hot' | 'hiring' | 'quick_wins' | 'growth') {
    if (p === 'hot') {
      setMinScore(highScoreThreshold)
      setPreset('hot')
      return
    }
    setMinScore(0)
    setPreset(p)
  }

  function isReadyForOutreach(lead: Lead) {
    const st = (lead.status || '').toLowerCase()
    return !isClosedStatus(st) && Number(lead.score || 0) >= highScoreThreshold && Boolean((lead.personalized_message || '').trim())
  }

  useEffect(() => {
    if (preset === 'hot' && Number(minScore || 0) !== highScoreThreshold) {
      setMinScore(highScoreThreshold)
    }
  }, [highScoreThreshold, minScore, preset])

  useEffect(() => {
    if (!lastConfigEventTs) return
    void load()
  }, [lastConfigEventTs, load])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Outreach Queue</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Active pipeline — leads sorted by priority score.
        </p>
      </div>

      <section className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-lg border border-surface-border bg-zinc-50 px-2.5 py-1.5 dark:bg-zinc-800">
              <FilterSelect
                options={STATUS_OPTIONS}
                value={statusFilter}
                onChange={setStatusFilter}
                placeholder="Status"
                className="[&_select]:border-0 [&_select]:bg-transparent [&_select]:text-xs [&_select]:font-medium [&_select]:focus:ring-0"
              />
            </div>
            <div className="flex items-center gap-2 rounded-lg border border-surface-border bg-zinc-50 px-2.5 py-1.5 dark:bg-zinc-800">
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
                className="w-16 border-0 bg-transparent text-xs font-medium text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-0 dark:text-white"
                placeholder="Score"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-medium text-zinc-400 dark:text-zinc-500">Presets</span>
              <button
                type="button"
                onClick={() => applyPreset('hot')}
                className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                  preset === 'hot'
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                    : 'border-surface-border text-zinc-500 hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white'
                }`}
              >
                Hot Leads
              </button>
              <button
                type="button"
                onClick={() => applyPreset('hiring')}
                className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                  preset === 'hiring'
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                    : 'border-surface-border text-zinc-500 hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white'
                }`}
              >
                Hiring
              </button>
              <button
                type="button"
                onClick={() => applyPreset('quick_wins')}
                className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                  preset === 'quick_wins'
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                    : 'border-surface-border text-zinc-500 hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white'
                }`}
              >
                Quick Wins
              </button>
              <button
                type="button"
                onClick={() => applyPreset('growth')}
                className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                  preset === 'growth' ? 'border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200' : 'border-surface-border text-zinc-500 hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white'
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
                className="rounded-lg border border-surface-border px-2.5 py-1 text-[11px] font-medium text-zinc-500 transition hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white"
              >
                Clear preset
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setHighlightReady(!highlightReady)}
              className={`rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                highlightReady
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  : 'border-surface-border text-zinc-500 hover:border-zinc-300 hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-white'
              }`}
            >
              Show Ready
            </button>
          </div>
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
                <th className="px-3 py-2">Priority</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Last contacted</th>
                <th className="px-3 py-2">Score</th>
              </tr>
            </thead>
            <tbody>
              {loading && queueRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-12 text-center text-ink-muted">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : queueRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-10 text-center text-ink-muted">
                    No active leads found for current filters.
                  </td>
                </tr>
              ) : (
                queueRows.map((row) => (
                  <tr
                    key={row.id}
                    className={`border-b border-surface-border/80 text-ink-muted last:border-0 hover:bg-amber-500/[0.04] dark:hover:bg-amber-400/[0.03] ${
                      Number(row.score || 0) >= highScoreThreshold
                        ? 'bg-amber-500/[0.05] dark:bg-amber-400/[0.06]'
                        : ''
                    } ${highlightReady && isReadyForOutreach(row) ? 'ring-1 ring-emerald-500/30' : ''}`}
                  >
                    <td className="max-w-[16rem] truncate px-3 py-2.5 text-ink" title={row.full_name}>
                      {row.full_name || '—'}
                    </td>
                    <td className="max-w-[14rem] truncate px-3 py-2.5" title={row.company_name}>
                      {row.company_name || '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge variant={priorityVariant(getPriorityTierFromScore(Number(row.score || 0), adminConfig))}>
                          {priorityLabel(getPriorityTierFromScore(Number(row.score || 0), adminConfig))}
                        </Badge>
                        {String(row.source_platform || '').trim().toLowerCase() === 'linkedin' ? (
                          <Badge variant="platform">LinkedIn</Badge>
                        ) : null}
                      </div>
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
