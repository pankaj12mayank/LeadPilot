import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { userGetTransactions } from '@/lib/api/subscriptions'
import type { TransactionType } from '@/lib/api/subscriptions'
import { UsageBar } from '@/components/UsageBar'
import { useAuthStore } from '@/store/authStore'

const STATUS_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'success', label: 'Success' },
  { value: 'pending', label: 'Pending' },
  { value: 'failed', label: 'Failed' },
  { value: 'refunded', label: 'Refunded' },
]

const PAGE_SIZE = 10

export function UserTransactionsPage() {
  const [txns, setTxns] = useState<TransactionType[]>([])
  const [sub, setSub] = useState<any>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const [res, subRes] = await Promise.all([
          userGetTransactions({ status: statusFilter || undefined }),
          fetch('/api/user/subscription', { headers: { Authorization: `Bearer ${sessionStorage.getItem('li_token')}` } }).then((r) => r.json()),
        ])
        setTxns(res.transactions || [])
        if (subRes.has_subscription) setSub(subRes.subscription)
      } catch { /* ignore */ } finally {
        setLoading(false)
      }
    }
    void load()
  }, [statusFilter])

  const statusColors: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    failed: 'bg-red-500/10 text-red-700 dark:text-red-300',
    pending: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    refunded: 'bg-purple-500/10 text-purple-700 dark:text-purple-300',
  }

  const filteredTxns = txns.filter((t) => {
    if (!searchQuery) return true
    const q = searchQuery.toLowerCase()
    return (
      (t.plan_name || '').toLowerCase().includes(q) ||
      (t.amount?.toString() || '').includes(q) ||
      (t.gateway || '').toLowerCase().includes(q)
    )
  })

  const totalPages = Math.ceil(filteredTxns.length / PAGE_SIZE)
  const paginatedTxns = filteredTxns.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  if (!user) return <p className="p-6 text-sm text-zinc-500">Loading...</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">My Transactions</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">View your payment history and invoices</p>
      </div>

      {sub && (
        <div className="rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-zinc-900 dark:text-white">{sub.plan_name} Plan</h2>
              <UsageBar used={sub.leads_consumed || 0} limit={sub.lead_limit || 0} label="Leads used this period" />
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
                <span>Period: {sub.period_start ? new Date(sub.period_start).toLocaleDateString() : '-'} – {sub.period_end ? new Date(sub.period_end).toLocaleDateString() : '-'}</span>
                <span className="capitalize">Status: {sub.status}</span>
              </div>
            </div>
            {sub.leads_consumed >= sub.lead_limit && sub.lead_limit > 0 && (
              <Link to="/user/upgrade" className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700">
                Upgrade Now
              </Link>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                setStatusFilter(opt.value)
                setCurrentPage(1)
              }}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                statusFilter === opt.value
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'border border-surface-border text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setCurrentPage(1)
            }}
            placeholder="Search by plan, amount..."
            className="w-full rounded-lg border border-surface-border bg-transparent py-1.5 pl-3 pr-8 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600"
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-zinc-50/80 text-xs uppercase tracking-wider text-zinc-500 dark:bg-zinc-800/50">
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Plan</th>
                <th className="px-4 py-3 font-semibold">Amount</th>
                <th className="px-4 py-3 font-semibold">Gateway</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Invoice</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-zinc-500">
                    Loading transactions...
                  </td>
                </tr>
              ) : paginatedTxns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-zinc-400">
                    No transactions found.
                  </td>
                </tr>
              ) : (
                paginatedTxns.map((t, idx) => (
                  <tr
                    key={t.id}
                    className={`border-b border-surface-border/60 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/30 ${idx % 2 === 1 ? 'bg-zinc-50/50 dark:bg-zinc-800/10' : ''}`}
                  >
                    <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                      {t.created_at ? new Date(t.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '-'}
                    </td>
                    <td className="px-4 py-3 font-medium text-zinc-900 dark:text-white">{t.plan_name || '-'}</td>
                    <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{t.currency?.toUpperCase()} {t.amount?.toFixed(2)}</td>
                    <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400 capitalize">{t.gateway || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusColors[t.status] || ''}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {t.invoice_url ? (
                        <a href={t.invoice_url} target="_blank" rel="noopener noreferrer" className="text-amber-600 hover:underline dark:text-amber-400">
                          View
                        </a>
                      ) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
            <span className="text-xs text-zinc-500">
              Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filteredTxns.length)} of {filteredTxns.length}
            </span>
            <div className="flex gap-1">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="rounded-md border border-surface-border px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                Prev
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const page = i + 1
                return (
                  <button
                    key={page}
                    type="button"
                    onClick={() => setCurrentPage(page)}
                    className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
                      currentPage === page
                        ? 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                        : 'border-surface-border text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    }`}
                  >
                    {page}
                  </button>
                )
              })}
              <button
                type="button"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="rounded-md border border-surface-border px-2.5 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
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