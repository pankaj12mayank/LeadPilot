import { Plus, Save, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminGetPlans, adminCreatePlan, adminUpdatePlan, adminDeletePlan } from '@/lib/api/subscriptions'
import type { PlanType } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function AdminPlansPage() {
  const [plans, setPlans] = useState<PlanType[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<PlanType | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const res = await adminGetPlans()
      setPlans(res.plans || [])
    } catch { toast.error('Could not load plans') }
    setLoading(false)
  }

  async function savePlan() {
    if (!editing) return
    try {
      if (editing.id) {
        await adminUpdatePlan(editing.id, editing)
        toast.success('Plan updated')
      } else {
        await adminCreatePlan(editing)
        toast.success('Plan created')
      }
      setEditing(null)
      load()
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save plan')) }
  }

  async function removePlan() {
    if (!deleteId) return
    try {
      await adminDeletePlan(deleteId)
      toast.success('Plan deleted')
      setDeleteId(null)
      load()
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not delete plan')) }
  }

  if (loading) return <div className="p-8 text-center text-zinc-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Plans</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Manage subscription plans and pricing.</p>
        </div>
        <button
          type="button"
          onClick={() => setEditing({ id: '', name: '', description: '', monthly_price: 0, currency: 'usd', features: [], highlighted: false, is_free: false, lead_limit: 0, stripe_price_id: '', razorpay_plan_id: '', sort_order: 0, is_active: true })}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
        >
          <Plus className="h-4 w-4" /> New Plan
        </button>
      </div>

      <div className="space-y-4">
        {plans.map((plan) => (
          <div key={plan.id} className="rounded-2xl border border-surface-border bg-white p-5 dark:bg-zinc-900">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">{plan.name}</h3>
                  {plan.is_free && <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300">Free</span>}
                  {plan.highlighted && <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:text-amber-300">Popular</span>}
                  {!plan.is_active && <span className="rounded-full bg-zinc-500/10 px-2.5 py-0.5 text-xs font-medium text-zinc-500">Inactive</span>}
                </div>
                <p className="mt-1 text-sm text-zinc-500">{plan.description}</p>
                <p className="mt-2 font-display text-2xl font-bold text-zinc-900 dark:text-white">
                  ${plan.monthly_price}
                  <span className="text-sm font-normal text-zinc-500">/{plan.currency?.toUpperCase() || 'USD'} /month</span>
                </p>
                <p className="mt-1 text-xs text-zinc-400">Lead limit: {plan.lead_limit}</p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setEditing({ ...plan, features: [...(plan.features || [])] })}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400"
                >
                  Edit
                </button>
                {!['Free', 'Starter', 'Pro', 'Custom'].includes(plan.name) && (
                  <button
                    type="button"
                    onClick={() => setDeleteId(plan.id)}
                    className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 dark:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
            {plan.features.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {plan.features.map((f) => (
                  <span key={f} className="rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">{f}</span>
                ))}
              </div>
            )}
            {(plan.stripe_price_id || plan.razorpay_plan_id) && (
              <div className="mt-2 flex gap-4 text-xs text-zinc-400">
                {plan.stripe_price_id && <span>Stripe: {plan.stripe_price_id}</span>}
                {plan.razorpay_plan_id && <span>Razorpay: {plan.razorpay_plan_id}</span>}
              </div>
            )}
          </div>
        ))}
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setEditing(null)}>
          <div className="w-full max-w-lg rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">
              {editing.id ? `Edit ${editing.name}` : 'New Plan'}
            </h2>
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Name</label>
                  <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className="field-input mt-1 w-full" />
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Price ($)</label>
                  <input type="number" value={editing.monthly_price} onChange={(e) => setEditing({ ...editing, monthly_price: Number(e.target.value) })} className="field-input mt-1 w-full" />
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Currency</label>
                  <select value={editing.currency} onChange={(e) => setEditing({ ...editing, currency: e.target.value })} className="field-input mt-1 w-full">
                    <option value="usd">USD</option>
                    <option value="inr">INR</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Lead Limit</label>
                  <input type="number" value={editing.lead_limit} onChange={(e) => setEditing({ ...editing, lead_limit: Number(e.target.value) })} className="field-input mt-1 w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Description</label>
                <input value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} className="field-input mt-1 w-full" />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Features (one per line)</label>
                <textarea
                  value={(editing.features || []).join('\n')}
                  onChange={(e) => setEditing({ ...editing, features: e.target.value.split('\n').filter(Boolean) })}
                  rows={4}
                  className="field-input mt-1 w-full resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Stripe Price ID</label>
                  <input value={editing.stripe_price_id || ''} onChange={(e) => setEditing({ ...editing, stripe_price_id: e.target.value })} className="field-input mt-1 w-full" />
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Razorpay Plan ID</label>
                  <input value={editing.razorpay_plan_id || ''} onChange={(e) => setEditing({ ...editing, razorpay_plan_id: e.target.value })} className="field-input mt-1 w-full" />
                </div>
              </div>
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={editing.highlighted} onChange={(e) => setEditing({ ...editing, highlighted: e.target.checked })} />
                  Popular
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={editing.is_free} onChange={(e) => setEditing({ ...editing, is_free: e.target.checked })} />
                  Free Plan
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} />
                  Active
                </label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => void savePlan()} className="btn-primary inline-flex items-center gap-2">
                  <Save className="h-4 w-4" /> Save
                </button>
                <button type="button" onClick={() => setEditing(null)} className="rounded-lg border border-surface-border px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog open={!!deleteId} title="Delete Plan" message="Are you sure? This cannot be undone." confirmLabel="Delete" variant="danger" onConfirm={() => void removePlan()} onCancel={() => setDeleteId(null)} />
    </div>
  )
}
