import { Mail, Search, Filter, Trash2, ToggleLeft, ToggleRight, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api, getApiErrorMessage } from '@/lib/api/client'
import { cn } from '@/lib/utils/cn'

type Subscriber = {
  id: string
  email: string
  status: 'active' | 'inactive'
  created_at: string
  source?: string
}

export function AdminNewsletterPage() {
  const [subscribers, setSubscribers] = useState<Subscriber[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const [searchEmail, setSearchEmail] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const fetchSubscribers = useCallback(async () => {
    setBusy(true)
    setErr(null)
    try {
      const params: Record<string, string> = {}
      if (searchEmail.trim()) params.email = searchEmail.trim()
      if (statusFilter) params.status = statusFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo

      const { data } = await api.get<{ subscribers: Subscriber[]; total: number }>('/admin/newsletter', { params })
      setSubscribers(data.subscribers || [])
      setTotal(data.total ?? data.subscribers.length)
    } catch (e) {
      setErr(getApiErrorMessage(e, 'Could not load subscribers'))
    } finally {
      setBusy(false)
      setLoading(false)
    }
  }, [searchEmail, statusFilter, dateFrom, dateTo])

  useEffect(() => { void fetchSubscribers() }, [fetchSubscribers])

  const handleDelete = async (id: string) => {
    if (!confirm('Remove this subscriber?')) return
    try {
      await api.delete(`/admin/newsletter/${id}`)
      setSubscribers((prev) => prev.filter((s) => s.id !== id))
      setTotal((prev) => prev - 1)
    } catch (e) {
      alert(getApiErrorMessage(e, 'Failed to delete subscriber'))
    }
  }

  const handleToggleStatus = async (sub: Subscriber) => {
    const newStatus = sub.status === 'active' ? 'inactive' : 'active'
    try {
      await api.patch(`/admin/newsletter/${sub.id}`, { status: newStatus })
      setSubscribers((prev) =>
        prev.map((s) => (s.id === sub.id ? { ...s, status: newStatus } : s)),
      )
    } catch (e) {
      alert(getApiErrorMessage(e, 'Failed to update status'))
    }
  }

  const clearFilters = () => {
    setSearchEmail('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
  }

  const hasFilters = searchEmail || statusFilter || dateFrom || dateTo

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Newsletter Subscribers</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{total} subscriber{total !== 1 ? 's' : ''}</p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-3 border-b border-surface-border px-5 py-4">
          <div className="relative min-w-[200px] flex-1 max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
              placeholder="Search by email..."
              className="field-input w-full py-2 pl-9 pr-3"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-zinc-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="field-input"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-500 dark:text-zinc-400">From:</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="field-input"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-500 dark:text-zinc-400">To:</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="field-input"
            />
          </div>

          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-sm text-amber-600 hover:text-amber-700 dark:text-amber-400"
            >
              Clear
            </button>
          )}

          <button
            type="button"
            onClick={() => void fetchSubscribers()}
            disabled={busy}
            className="ml-auto inline-flex items-center gap-2 rounded-lg border border-surface-border px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
          </div>
        ) : err ? (
          <div className="px-5 py-12 text-center text-amber-600">{err}</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-surface-border bg-zinc-50/50 text-xs uppercase text-zinc-500 dark:bg-zinc-800/50">
                    <th className="px-5 py-3 font-semibold">Email</th>
                    <th className="py-3 pr-4 font-semibold">Status</th>
                    <th className="py-3 pr-4 font-semibold">Subscribed</th>
                    <th className="py-3 pr-4 font-semibold">Source</th>
                    <th className="py-3 pr-4 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscribers.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-12 text-center text-zinc-500 dark:text-zinc-400">
                        {hasFilters ? 'No subscribers match your filters.' : 'No subscribers yet.'}
                      </td>
                    </tr>
                  ) : subscribers.map((sub) => (
                    <tr
                      key={sub.id}
                      className="border-b border-surface-border/70 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <Mail className="h-4 w-4 text-zinc-400" />
                          <span className="text-zinc-900 dark:text-white">{sub.email}</span>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={cn(
                            'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
                            sub.status === 'active'
                              ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                              : 'bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300',
                          )}
                        >
                          {sub.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 font-mono text-xs text-zinc-500 dark:text-zinc-400">
                        {new Date(sub.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 pr-4 text-zinc-500 dark:text-zinc-400">
                        {sub.source || '—'}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void handleToggleStatus(sub)}
                            title={sub.status === 'active' ? 'Deactivate' : 'Activate'}
                            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
                          >
                            {sub.status === 'active' ? (
                              <ToggleRight className="h-5 w-5 text-emerald-500" />
                            ) : (
                              <ToggleLeft className="h-5 w-5" />
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDelete(sub.id)}
                            title="Delete"
                            className="rounded-lg p-1.5 text-zinc-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between border-t border-surface-border px-5 py-3">
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                Showing {subscribers.length} of {total} subscriber{total !== 1 ? 's' : ''}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}