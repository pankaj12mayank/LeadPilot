import { Save, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminGetEmailConfig, adminSaveEmailConfig, adminTestEmail } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'

export function AdminEmailConfigPage() {
  const [host, setHost] = useState('')
  const [port, setPort] = useState(587)
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [fromEmail, setFromEmail] = useState('')
  const [fromName, setFromName] = useState('')
  const [active, setActive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const cfg = await adminGetEmailConfig()
        if (!c && cfg && cfg.smtp_host) {
          setHost(cfg.smtp_host || '')
          setPort(cfg.smtp_port || 587)
          setUser(cfg.smtp_user || '')
          setFromEmail(cfg.from_email || '')
          setFromName(cfg.from_name || '')
          setActive(cfg.is_active || false)
        }
      } catch { /* ignore */ }
      if (!c) setLoading(false)
    })()
    return () => { c = true }
  }, [])

  async function save() {
    setSaving(true)
    try {
      const body: any = { smtp_host: host, smtp_port: port, smtp_user: user, from_email: fromEmail, from_name: fromName, is_active: active }
      if (pass) body.smtp_pass = pass
      await adminSaveEmailConfig(body)
      toast.success('Email config saved')
      setPass('')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save'))
    } finally { setSaving(false) }
  }

  async function test() {
    setTesting(true)
    try {
      await adminTestEmail()
      toast.success('Test email sent! Check your inbox.')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Test failed'))
    } finally { setTesting(false) }
  }

  if (loading) return <div className="p-8 text-center text-zinc-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Email Configuration</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Configure SMTP settings for sending transactional emails.</p>
      </div>

      <div className="rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">SMTP Host</label>
            <input value={host} onChange={(e) => setHost(e.target.value)} className="field-input mt-1 w-full" placeholder="smtp.gmail.com" />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">SMTP Port</label>
            <input type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} className="field-input mt-1 w-full" />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">SMTP Username</label>
            <input value={user} onChange={(e) => setUser(e.target.value)} className="field-input mt-1 w-full" placeholder="your@email.com" />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">SMTP Password</label>
            <input type="password" value={pass} onChange={(e) => setPass(e.target.value)} className="field-input mt-1 w-full" placeholder="Leave blank to keep existing" />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">From Email</label>
            <input value={fromEmail} onChange={(e) => setFromEmail(e.target.value)} className="field-input mt-1 w-full" />
          </div>
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">From Name</label>
            <input value={fromName} onChange={(e) => setFromName(e.target.value)} className="field-input mt-1 w-full" />
          </div>
        </div>

        <label className="mt-4 flex items-center gap-3">
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} className="rounded" />
          <span className="text-sm font-medium text-zinc-900 dark:text-white">Active (send emails)</span>
        </label>

        <div className="mt-6 flex gap-3">
          <button type="button" disabled={saving} onClick={() => void save()} className="btn-primary inline-flex items-center gap-2">
            <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save'}
          </button>
          <button type="button" disabled={testing} onClick={() => void test()} className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400">
            <Send className="h-4 w-4" /> {testing ? 'Sending...' : 'Test Email'}
          </button>
        </div>
      </div>
    </div>
  )
}
