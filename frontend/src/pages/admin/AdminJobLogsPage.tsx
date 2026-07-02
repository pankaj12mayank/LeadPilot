import { RefreshCw, Search } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  adminGetJobLogs,
  type AdminJobLogRow,
} from '@/lib/api/admin'
import { cn } from '@/lib/utils/cn'

function titleize(value: string) {
  const text = String(value || '').replaceAll('_', ' ').trim()
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '—'
}

const statusStyles: Record<string, string> = {
  success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
  partial_success: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
  failure: 'bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30',
}

const pageSize = 10

export function AdminJobLogsPage() {
  const [logs, setLogs] = useState<AdminJobLogRow[]>([])
  const [busy, setBusy] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'partial_success' | 'failure'>('all')
  const [page, setPage] = useState(1)
  const [refreshedAt, setRefreshedAt] = useState('')

  const refresh = useCallback(async () => {
    setBusy(true)
    try {
      const data = await adminGetJobLogs(300)
      setLogs(data.items || [])
      setRefreshedAt(new Date().toLocaleTimeString())
    } catch {
      // silent
    } finally { setBusy(false) }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    return logs.filter((x) => {
      const byJob = !q || String(x.job_type || '').toLowerCase().includes(q)
      const byStatus = statusFilter === 'all' || String(x.status || '') === statusFilter
      return byJob && byStatus
    })
  }, [logs, searchQuery, statusFilter])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.max(1, Math.min(page, totalPages))
  const pageRows = filtered.slice((safePage - 1) * pageSize, safePage * pageSize)

  useEffect(() => { setPage(1) }, [searchQuery, statusFilter])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Job Logs</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Monitor automated job runs and system tasks</p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => void refresh()}
          className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-800"
        >
          <RefreshCw className={cn('h-4 w-4', busy && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2 border-b border-surface-border px-4 py-3">
          <div className="relative w-48">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Job type..."
              className="w-full rounded-lg border border-surface-border bg-transparent py-1.5 pl-8 pr-2.5 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            className="rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600"
          >
            <option value="all">All</option>
            <option value="success">Success</option>
            <option value="partial_success">Partial</option>
            <option value="failure">Failure</option>
          </select>
          {refreshedAt && (
            <span className="text-xs text-zinc-400 dark:text-zinc-500">Last updated: {refreshedAt}</span>
          )}
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-zinc-50/50 text-xs uppercase text-zinc-500 dark:bg-zinc-800/50">
                <th className="px-5 py-3 font-semibold">Job</th>
                <th className="py-3 pr-4 font-semibold">Status</th>
                <th className="py-3 pr-4 font-semibold">Started</th>
                <th className="py-3 pr-4 font-semibold">Records</th>
                <th className="py-3 pr-4 font-semibold">Message</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-zinc-500 dark:text-zinc-400">
                    {logs.length === 0 ? 'No job logs recorded yet.' : 'No matches for current filters.'}
                  </td>
                </tr>
              ) : pageRows.map((row, idx) => (
                <tr key={idx} className="border-b border-surface-border/70 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  <td className="px-5 py-3 font-medium text-zinc-900 dark:text-white">{titleize(row.job_type)}</td>
                  <td className="py-3 pr-4">
                    <span className={cn(
                      'inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium',
                      statusStyles[row.status] || 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
                    )}>
                      {titleize(row.status)}
                    </span>
                  </td>
                  <td className="py-3 pr-4 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                    {row.run_date ? new Date(row.run_date).toLocaleString() : '—'}
                  </td>
                  <td className="py-3 pr-4 text-zinc-500 dark:text-zinc-400">{row.records_processed ?? '—'}</td>
                  <td className="max-w-xs truncate py-3 pr-4 text-xs text-zinc-500 dark:text-zinc-400">
                    {(row.errors || []).join(', ') || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-surface-border px-5 py-3">
            <span className="text-xs text-zinc-500 dark:text-zinc-400">
              Page {safePage} of {totalPages} ({filtered.length} total)
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={safePage <= 1}
                onClick={() => setPage(safePage - 1)}
                className="rounded-lg border border-surface-border px-3 py-1.5 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 disabled:opacity-40 dark:hover:bg-zinc-800"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={safePage >= totalPages}
                onClick={() => setPage(safePage + 1)}
                className="rounded-lg border border-surface-border px-3 py-1.5 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 disabled:opacity-40 dark:hover:bg-zinc-800"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
