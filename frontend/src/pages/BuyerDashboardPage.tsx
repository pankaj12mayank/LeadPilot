import { Download, ShoppingCart } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import {
  downloadLeadPack,
  exportFilteredLeads,
  listLeadPacks,
  previewLeadPack,
  purchaseLeadPack,
  type LeadPackPreviewLead,
} from '@/lib/api/marketplace'
import { getApiErrorMessage } from '@/lib/api/client'

type PackRow = {
  id: number
  name: string
  description: string
  price_usd: number
  lead_count: number
}

export function BuyerDashboardPage() {
  const [packs, setPacks] = useState<PackRow[]>([])
  const [selectedPackId, setSelectedPackId] = useState<number | null>(null)
  const [previewRows, setPreviewRows] = useState<LeadPackPreviewLead[]>([])
  const [busy, setBusy] = useState(false)
  const [filterTier, setFilterTier] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [planTier, setPlanTier] = useState<'starter' | 'growth' | 'pro'>('starter')
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx'>('csv')

  useEffect(() => {
    ;(async () => {
      try {
        setPacks(await listLeadPacks())
      } catch (e) {
        toast.error('Could not load lead packs', { description: getApiErrorMessage(e, 'Load failed') })
      }
    })()
  }, [])

  async function openPreview(packId: number) {
    try {
      setBusy(true)
      const data = await previewLeadPack(packId)
      setSelectedPackId(packId)
      setPreviewRows(data.preview || [])
    } catch (e) {
      toast.error('Preview failed', { description: getApiErrorMessage(e, 'Could not preview lead pack') })
    } finally {
      setBusy(false)
    }
  }

  async function purchaseAndDownload(packId: number) {
    try {
      setBusy(true)
      await purchaseLeadPack(packId)
      await downloadLeadPack(packId)
      toast.success('Purchase simulated', { description: 'Lead pack purchased and download unlocked.' })
    } catch (e) {
      toast.error('Purchase failed', { description: getApiErrorMessage(e, 'Could not complete purchase simulation') })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-[1200px] space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink sm:text-3xl">Buyer dashboard</h1>
        <p className="mt-2 text-sm text-ink-muted">Browse lead packs, preview sample leads, simulate purchase, and download access.</p>
      </div>

      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {packs.map((pack) => (
          <article key={pack.id} className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark">
            <h2 className="text-sm font-semibold text-ink">{pack.name}</h2>
            <p className="mt-1 text-xs text-ink-muted">{pack.description || 'Lead pack curated by admin.'}</p>
            <div className="mt-3 flex items-center justify-between text-xs text-ink-muted">
              <span>{pack.lead_count} leads</span>
              <span className="font-semibold text-ink">${pack.price_usd.toFixed(2)}</span>
            </div>
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => void openPreview(pack.id)}
                className="rounded-lg border border-surface-border px-3 py-1.5 text-xs text-ink-muted hover:bg-field/60"
              >
                Preview
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void purchaseAndDownload(pack.id)}
                className="inline-flex items-center gap-1 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-900 dark:text-amber-200"
              >
                <ShoppingCart className="h-3.5 w-3.5" />
                Purchase
              </button>
            </div>
          </article>
        ))}
      </section>

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
        <h2 className="font-display text-lg font-semibold text-ink">Preview leads</h2>
        <p className="mt-1 text-xs text-ink-muted">
          {selectedPackId ? `Showing preview for pack #${selectedPackId}` : 'Select a pack to view sample leads.'}
        </p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-xs">
            <thead className="border-b border-surface-border text-ink-muted">
              <tr>
                <th className="px-2 py-2">Name</th>
                <th className="px-2 py-2">Title</th>
                <th className="px-2 py-2">Company</th>
                <th className="px-2 py-2">Score</th>
                <th className="px-2 py-2">Tier</th>
              </tr>
            </thead>
            <tbody>
              {previewRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-2 py-3 text-ink-muted">
                    No preview yet.
                  </td>
                </tr>
              ) : (
                previewRows.map((row) => (
                  <tr key={row.id} className="border-b border-surface-border/70">
                    <td className="px-2 py-2">{row.full_name || '—'}</td>
                    <td className="px-2 py-2">{row.title || '—'}</td>
                    <td className="px-2 py-2">{row.company_name || '—'}</td>
                    <td className="px-2 py-2">{Math.round(Number(row.score || 0))}</td>
                    <td className="px-2 py-2">{row.tier || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
      <section className="space-y-3 rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
        <h2 className="font-display text-lg font-semibold text-ink">Filtered export</h2>
        <p className="text-xs text-ink-muted">Export CSV/XLSX with plan-based row limits.</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
            placeholder="Search"
            className="field-input rounded-lg px-2 py-1.5 text-xs"
          />
          <select value={filterTier} onChange={(e) => setFilterTier(e.target.value)} className="field-input rounded-lg px-2 py-1.5 text-xs">
            <option value="">All tiers</option>
            <option value="hot">Hot</option>
            <option value="warm">Warm</option>
            <option value="cold">Cold</option>
          </select>
          <input
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            placeholder="Status"
            className="field-input rounded-lg px-2 py-1.5 text-xs"
          />
          <select value={planTier} onChange={(e) => setPlanTier(e.target.value as 'starter' | 'growth' | 'pro')} className="field-input rounded-lg px-2 py-1.5 text-xs">
            <option value="starter">Starter</option>
            <option value="growth">Growth</option>
            <option value="pro">Pro</option>
          </select>
          <select value={exportFormat} onChange={(e) => setExportFormat(e.target.value as 'csv' | 'xlsx')} className="field-input rounded-lg px-2 py-1.5 text-xs">
            <option value="csv">CSV</option>
            <option value="xlsx">XLSX</option>
          </select>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={async () => {
            try {
              setBusy(true)
              await exportFilteredLeads({
                format: exportFormat,
                search: filterSearch.trim() || undefined,
                tier: filterTier || undefined,
                status: filterStatus.trim() || undefined,
                plan_tier: planTier,
              })
              toast.success('Export ready', { description: `${exportFormat.toUpperCase()} downloaded with ${planTier} plan limits.` })
            } catch (e) {
              toast.error('Export failed', { description: getApiErrorMessage(e, 'Could not export filtered leads') })
            } finally {
              setBusy(false)
            }
          }}
          className="w-fit rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-900 dark:text-amber-200"
        >
          Export filtered leads
        </button>
      </section>
      <div className="text-xs text-ink-subtle">
        <Download className="mr-1 inline h-3.5 w-3.5" />
        Downloads are unlocked after purchase simulation.
      </div>
    </div>
  )
}
