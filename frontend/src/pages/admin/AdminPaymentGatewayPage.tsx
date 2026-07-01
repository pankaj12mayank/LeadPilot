import { Eye, EyeOff, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminGetGatewayConfig, adminSaveGatewayConfig } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'

export function AdminPaymentGatewayPage() {
  const [gateway, setGateway] = useState<'stripe' | 'razorpay'>('stripe')
  const [pk, setPk] = useState('')
  const [sk, setSk] = useState('')
  const [ws, setWs] = useState('')
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showSk, setShowSk] = useState(false)
  const [showWs, setShowWs] = useState(false)

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const cfg = await adminGetGatewayConfig(gateway)
        if (!c) { setPk(cfg.publishable_key || ''); setActive(cfg.is_active || false) }
      } catch { /* ignore */ }
      if (!c) setLoading(false)
    })()
    return () => { c = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gateway])

  async function save() {
    setSaving(true)
    try {
      const body: any = { is_active: active }
      if (pk) body.publishable_key = pk
      if (sk) body.secret_key = sk
      if (ws) body.webhook_secret = ws
      await adminSaveGatewayConfig(gateway, body)
      toast.success(`${gateway} config saved`)
      setSk(''); setWs('')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save'))
    } finally { setSaving(false) }
  }

  if (loading) return <div className="text-sm text-zinc-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Payment Gateway</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Configure Stripe and Razorpay API keys.</p>
      </div>

      <div className="flex gap-2">
        {(['stripe', 'razorpay'] as const).map((g) => (
          <button
            key={g}
            type="button"
            onClick={() => setGateway(g)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
              gateway === g
                ? 'bg-amber-600 text-white'
                : 'border border-surface-border text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400'
            }`}
          >
            {g === 'stripe' ? 'Stripe' : 'Razorpay'}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900">
        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="rounded" />
            <span className="text-sm font-medium text-zinc-900 dark:text-white">Gateway Active</span>
          </label>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Publishable Key</label>
            <input value={pk} onChange={(e) => setPk(e.target.value)} className="field-input mt-1 w-full" />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Secret Key</label>
            <div className="relative mt-1">
              <input
                type={showSk ? 'text' : 'password'}
                value={sk}
                onChange={(e) => setSk(e.target.value)}
                className="field-input w-full pr-10"
                placeholder="Leave blank to keep existing"
              />
              <button type="button" onClick={() => setShowSk(!showSk)} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400">
                {showSk ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Webhook Secret</label>
            <div className="relative mt-1">
              <input
                type={showWs ? 'text' : 'password'}
                value={ws}
                onChange={(e) => setWs(e.target.value)}
                className="field-input w-full pr-10"
                placeholder="Leave blank to keep existing"
              />
              <button type="button" onClick={() => setShowWs(!showWs)} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400">
                {showWs ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button type="button" disabled={saving} onClick={() => void save()} className="btn-primary inline-flex items-center gap-2">
            <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save'}
          </button>
        </div>

        <div className="mt-6 rounded-xl border border-amber-500/20 bg-amber-50 p-4 dark:bg-amber-950/20">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">Webhook URLs</p>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Set these URLs in your {gateway} dashboard:
          </p>
          <code className="mt-2 block rounded-lg bg-zinc-100 p-2 text-xs dark:bg-zinc-800">
            {window.location.origin}/api/webhooks/{gateway}
          </code>
        </div>
      </div>
    </div>
  )
}
