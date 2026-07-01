import { Info, PackagePlus } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'

import { getApiErrorMessage } from '@/lib/api/client'
import { adminCreateLeadPack, adminListLeadPacks, adminUpdateLeadPack, type PackRow } from '@/lib/api/marketplace'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function AdminLeadPacksPage() {
  const [packs, setPacks] = useState<PackRow[]>([])
  const [busy, setBusy] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [leadIds, setLeadIds] = useState('')
  const [price, setPrice] = useState(99)
  const [toggleTarget, setToggleTarget] = useState<PackRow | null>(null)
  const [toggleBusy, setToggleBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setPacks(await adminListLeadPacks())
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not load lead packs'))
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function onCreate() {
    setBusy(true)
    try {
      await adminCreateLeadPack({
        name: name.trim(),
        description: description.trim(),
        lead_ids: leadIds.split(',').map((x) => Number(x.trim())).filter((n) => !isNaN(n)),
        price_usd: Number(price || 0),
        is_active: true,
      })
      toast.success('Lead pack created')
      setName(''); setDescription(''); setLeadIds(''); setPrice(99); setShowCreate(false)
      await load()
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not create lead pack'))
    } finally { setBusy(false) }
  }

  async function confirmToggle() {
    if (!toggleTarget) return
    setToggleBusy(true)
    try {
      await adminUpdateLeadPack(toggleTarget.id, {
        name: toggleTarget.name,
        description: '',
        lead_ids: (toggleTarget.lead_ids || []).map((x) => Number(x)).filter((n) => !isNaN(n)),
        price_usd: Number(toggleTarget.price_usd || 0),
        is_active: !toggleTarget.is_active,
      })
      await load()
      toast.success(toggleTarget.is_active ? 'Lead pack deactivated' : 'Lead pack activated')
      setToggleTarget(null)
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not update pack'))
    } finally { setToggleBusy(false) }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Lead Packs</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Curated lead packs for the buyer dashboard</p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-700"
        >
          <PackagePlus className="h-4 w-4" />
          Create Pack
        </button>
      </div>

      {/* Selling Flow Info */}
      <div className="rounded-2xl border border-amber-500/20 bg-amber-50/50 p-5 dark:bg-amber-950/20">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="text-sm text-zinc-700 dark:text-zinc-300">
            <p className="font-medium">How lead packs work:</p>
            <ul className="mt-2 list-inside list-disc space-y-1 text-zinc-600 dark:text-zinc-400">
              <li>Buyers see active packs in the <strong>Buyer Dashboard</strong> under their account</li>
              <li>Buyers can preview lead details before purchasing</li>
              <li>After purchase, buyers can download the pack as CSV</li>
              <li>Toggle a pack off to hide it from the buyer marketplace</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-zinc-50/50 dark:bg-zinc-800/50">
                <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Name</th>
                <th className="py-3 pr-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Price</th>
                <th className="py-3 pr-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Leads</th>
                <th className="py-3 pr-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Status</th>
                <th className="py-3 pr-4 text-xs font-semibold uppercase tracking-wider text-zinc-500">Actions</th>
              </tr>
            </thead>
            <tbody>
              {packs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-zinc-500 dark:text-zinc-400">
                    No lead packs yet. Create your first pack.
                  </td>
                </tr>
              ) : packs.map((pack) => (
                <tr key={pack.id} className="border-b border-surface-border/70 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  <td className="px-5 py-3">
                    <p className="font-medium text-zinc-900 dark:text-white">{pack.name}</p>
                  </td>
                  <td className="py-3 pr-4 font-medium text-zinc-900 dark:text-white">${Number(pack.price_usd || 0).toFixed(2)}</td>
                  <td className="py-3 pr-4 text-zinc-500 dark:text-zinc-400">{(pack.lead_ids || []).length} leads</td>
                  <td className="py-3 pr-4">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        pack.is_active
                          ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                          : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800'
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          pack.is_active ? 'bg-emerald-500' : 'bg-zinc-400'
                        }`}
                      />
                      {pack.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <button
                      type="button"
                      onClick={() => setToggleTarget(pack)}
                      className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-zinc-600 transition hover:border-amber-500/30 hover:text-amber-700 dark:text-zinc-400 dark:hover:text-amber-300"
                    >
                      {pack.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Toggle confirmation */}
      <ConfirmDialog
        open={!!toggleTarget}
        title={toggleTarget?.is_active ? 'Deactivate Lead Pack' : 'Activate Lead Pack'}
        message={
          toggleTarget?.is_active
            ? `This will hide "${toggleTarget?.name}" from the buyer marketplace. Buyers will no longer be able to purchase it.`
            : `This will make "${toggleTarget?.name}" visible in the buyer marketplace for purchase.`
        }
        confirmLabel={toggleTarget?.is_active ? 'Deactivate' : 'Activate'}
        variant="warning"
        busy={toggleBusy}
        onConfirm={() => void confirmToggle()}
        onCancel={() => setToggleTarget(null)}
      />

      <Modal
        open={showCreate}
        title="Create Lead Pack"
        titleHint="Set up a new curated lead pack"
        onClose={() => { if (!busy) { setShowCreate(false); setName(''); setDescription(''); setLeadIds(''); setPrice(99) } }}
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Pack Name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Premium Tech Leads" className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900" />
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Price (USD)</span>
              <input type="number" value={price} onChange={(e) => setPrice(Number(e.target.value))} min={0} className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900" />
            </label>
          </div>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Description</span>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="Describe what this pack contains..." className="w-full resize-none rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900" />
          </label>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Lead IDs</span>
            <input value={leadIds} onChange={(e) => setLeadIds(e.target.value)} placeholder="1, 2, 3, 4, 5" className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900" />
            <p className="text-xs text-zinc-400 dark:text-zinc-500">Comma-separated lead IDs to include in this pack.</p>
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => { setShowCreate(false); setName(''); setDescription(''); setLeadIds(''); setPrice(99) }}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !name.trim()}
              className="rounded-lg bg-amber-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-45"
              onClick={() => void onCreate()}
            >
              {busy ? 'Creating...' : 'Create Pack'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
