import { Loader2, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { SeleniumLeadpilotPanel } from '@/components/scraper/SeleniumLeadpilotPanel'
import { StatusBadge } from '@/components/ui/Badge'
import { fetchLeads } from '@/lib/api/leads'
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
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">LinkedIn search</h1>
        <p className="mt-2 max-w-2xl text-sm text-ink-muted">
          Run the desktop LinkedIn capture below from the same browser session you use for People search. Each run
          writes rows with: Name, Company, Role, Profile link, Agency type, Team size, Problem, Last active, Connection
          sent, Replied, Status, and an AI <strong>Solution</strong> from the problem (Ollama). New leads appear in{' '}
          <Link to="/leads" className="font-medium text-amber-800 underline-offset-2 hover:underline dark:text-amber-300">
            Leads
          </Link>{' '}
          when ingest is enabled.
        </p>
      </div>

      <SeleniumLeadpilotPanel onRunningChange={setPollRunning} />

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
