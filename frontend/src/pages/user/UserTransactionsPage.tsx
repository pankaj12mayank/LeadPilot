import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { userGetTransactions } from '@/lib/api/subscriptions'
import type { TransactionType } from '@/lib/api/subscriptions'
import { UsageBar } from '@/components/UsageBar'
import { useAuthStore } from '@/store/authStore'

export function UserTransactionsPage() {
  const [txns, setTxns] = useState<TransactionType[]>([])
  const [sub, setSub] = useState<any>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    async function load() {
      try {
        const [res, subRes] = await Promise.all([
          userGetTransactions({ status: statusFilter || undefined }),
          fetch('/api/user/subscription', { headers: { Authorization: `Bearer ${sessionStorage.getItem('li_token')}` } }).then((r) => r.json()),
        ])
        setTxns(res.transactions || [])
        if (subRes.has_subscription) setSub(subRes.subscription)
      } catch { /* ignore */ }
    }
    void load()
  }, [statusFilter])

  const statusColors: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    failed: 'bg-red-500/10 text-red-700 dark:text-red-300',
    pending: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    refunded: 'bg-purple-500/10 text-purple-700 dark:text-purple-300',
  }

  if (!user) return <p className="p-6 text-sm text-zinc-500">Loading...</p>

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">My Transactions</h1>

      {sub && (
        <div className="rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900">
          <h2 className="mb-4 font-semibold text-zinc-900 dark:text-white">
            {sub.plan_name} Plan
          </h2>
          <UsageBar used={sub.leads_consumed || 0} limit={sub.lead_limit || 0} label="Leads used this period" />
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
            <span>Period: {sub.period_start ? new Date(sub.period_start).toLocaleDateString() : '-'} – {sub.period_end ? new Date(sub.period_end).toLocaleDateString() : '-'}</span>
            <span>Status: {sub.status}</span>
          </div>
          {sub.leads_consumed >= sub.lead_limit && sub.lead_limit > 0 && (
            <Link to="/pricing" className="mt-3 inline-block rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700">
              Upgrade Now
            </Link>
          )}
        </div>
      )}

      <div className="flex gap-2">
        {['', 'success', 'failed', 'pending', 'refunded'].map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStatusFilter(s)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
              statusFilter === s ? 'bg-amber-600 text-white' : 'border border-surface-border text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-2xl border border-surface-border">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-zinc-50 dark:bg-zinc-800/50">
              <th className="px-4 py-3 font-semibold text-zinc-600 dark:text-zinc-300">Date</th>
              <th className="px-4 py-3 font-semibold text-zinc-600 dark:text-zinc-300">Plan</th>
              <th className="px-4 py-3 font-semibold text-zinc-600 dark:text-zinc-300">Amount</th>
              <th className="px-4 py-3 font-semibold text-zinc-600 dark:text-zinc-300">Status</th>
              <th className="px-4 py-3 font-semibold text-zinc-600 dark:text-zinc-300">Invoice</th>
            </tr>
          </thead>
          <tbody>
            {txns.map((t) => (
              <tr key={t.id} className="border-b border-surface-border last:border-0 hover:bg-zinc-50 dark:hover:bg-zinc-800/30">
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                  {t.created_at ? new Date(t.created_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-4 py-3 font-medium text-zinc-900 dark:text-white">{t.plan_name || '-'}</td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{t.currency?.toUpperCase()} {t.amount?.toFixed(2)}</td>
                <td className="px-4 py-3">
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColors[t.status] || ''}`}>
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
            ))}
            {txns.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-zinc-400">No transactions found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
