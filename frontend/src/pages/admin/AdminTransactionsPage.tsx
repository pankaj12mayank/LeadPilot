import { Search } from 'lucide-react'
import { useEffect, useState } from 'react'

import { adminGetTransactions } from '@/lib/api/subscriptions'
import type { TransactionType } from '@/lib/api/subscriptions'

export function AdminTransactionsPage() {
  const [txns, setTxns] = useState<TransactionType[]>([])
  const [gatewayFilter, setGatewayFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [userSearch, setUserSearch] = useState('')

  useEffect(() => { void load() }, [])

  async function load() {
    try {
      const res = await adminGetTransactions({ gateway: gatewayFilter || undefined, status: statusFilter || undefined })
      setTxns(res.transactions || [])
    } catch { /* ignore */ }
  }

  const filtered = txns.filter((t) => {
    if (userSearch && !t.user_email?.toLowerCase().includes(userSearch.toLowerCase())) return false
    return true
  })

  const statusColors: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    failed: 'bg-red-500/10 text-red-700 dark:text-red-300',
    pending: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    refunded: 'bg-purple-500/10 text-purple-700 dark:text-purple-300',
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Transactions</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{txns.length} transactions</p>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-surface-border bg-white p-3 shadow-sm dark:bg-zinc-900">
        <div className="relative w-48">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
          <input
            value={userSearch}
            onChange={(e) => setUserSearch(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-transparent py-1.5 pl-8 pr-2.5 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
            placeholder="Email..."
          />
        </div>
        <select value={gatewayFilter} onChange={(e) => setGatewayFilter(e.target.value)} className="rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600">
          <option value="">All Gateways</option>
          <option value="stripe">Stripe</option>
          <option value="razorpay">Razorpay</option>
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600">
          <option value="">All</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
          <option value="refunded">Refunded</option>
        </select>
        <button type="button" onClick={() => void load()} className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 hover:border-zinc-400 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:border-zinc-600">
          Refresh
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white dark:bg-zinc-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-zinc-50 dark:bg-zinc-800/50">
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Date</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">User</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Plan</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Amount</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Gateway</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-zinc-400">No transactions found</td></tr>
            )}
            {filtered.map((t) => (
              <tr key={t.id} className="border-b border-surface-border last:border-0">
                <td className="px-4 py-3 text-zinc-500">{new Date(t.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <div>
                    <p className="text-zinc-900 dark:text-white">{t.user_email}</p>
                    <p className="text-xs text-zinc-400">{t.user_name}</p>
                  </div>
                </td>
                <td className="px-4 py-3 font-medium text-zinc-900 dark:text-white">{t.plan_name}</td>
                <td className="px-4 py-3 text-zinc-900 dark:text-white">{t.currency?.toUpperCase()} {t.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-sm capitalize text-zinc-600 dark:text-zinc-400">{t.gateway}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[t.status] || 'bg-zinc-100 text-zinc-600'}`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
