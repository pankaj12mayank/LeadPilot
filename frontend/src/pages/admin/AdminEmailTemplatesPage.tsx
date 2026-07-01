import { Edit3, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { adminGetEmailTemplates, adminSaveEmailTemplate, adminDeleteEmailTemplate } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function AdminEmailTemplatesPage() {
  const [templates, setTemplates] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<any | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const res = await adminGetEmailTemplates()
      setTemplates(res.templates || [])
    } catch { /* ignore */ }
    setLoading(false)
  }

  async function save() {
    if (!editing) return
    setSaving(true)
    try {
      await adminSaveEmailTemplate(editing)
      toast.success('Template saved')
      setEditing(null)
      load()
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save'))
    } finally { setSaving(false) }
  }

  async function remove() {
    if (!deleteId) return
    try {
      await adminDeleteEmailTemplate(deleteId)
      toast.success('Template deleted')
      setDeleteId(null)
      load()
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not delete')) }
  }

  if (loading) return <div className="p-8 text-center text-zinc-500">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Email Templates</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Manage transactional email templates.</p>
        </div>
        <button
          type="button"
          onClick={() => setEditing({ name: '', subject: '', body_html: '', variables: [] })}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
        >
          <Plus className="h-4 w-4" /> New Template
        </button>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white dark:bg-zinc-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-zinc-50 dark:bg-zinc-800/50">
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Name</th>
              <th className="px-4 py-3 text-left font-medium text-zinc-600 dark:text-zinc-400">Subject</th>
              <th className="px-4 py-3 text-right font-medium text-zinc-600 dark:text-zinc-400">Actions</th>
            </tr>
          </thead>
          <tbody>
            {templates.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-zinc-400">No templates yet</td></tr>
            )}
            {templates.map((t) => (
              <tr key={t.id} className="border-b border-surface-border last:border-0">
                <td className="px-4 py-3 font-medium text-zinc-900 dark:text-white">{t.name}</td>
                <td className="px-4 py-3 text-zinc-500">{t.subject}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditing(t)} className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800">
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button type="button" onClick={() => setDeleteId(t.id)} className="rounded-lg p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setEditing(null)}>
          <div className="w-full max-w-2xl rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">
              {editing.id ? 'Edit Template' : 'New Template'}
            </h2>
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Name</label>
                <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} className="field-input mt-1 w-full" placeholder="payment_confirmation" />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Subject</label>
                <input value={editing.subject} onChange={(e) => setEditing({ ...editing, subject: e.target.value })} className="field-input mt-1 w-full" placeholder="Payment Confirmed - {{planName}}" />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Body HTML</label>
                <textarea
                  value={editing.body_html}
                  onChange={(e) => setEditing({ ...editing, body_html: e.target.value })}
                  rows={12}
                  className="field-input mt-1 w-full resize-none font-mono text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500">Variables (comma separated)</label>
                <input
                  value={(editing.variables || []).join(', ')}
                  onChange={(e) => setEditing({ ...editing, variables: e.target.value.split(',').map((v: string) => v.trim()).filter(Boolean) })}
                  className="field-input mt-1 w-full"
                  placeholder="userName, planName, amount"
                />
              </div>
              <div className="flex gap-3">
                <button type="button" disabled={saving} onClick={() => void save()} className="btn-primary">
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button type="button" onClick={() => setEditing(null)} className="rounded-lg border border-surface-border px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteId}
        title="Delete Template"
        message="Are you sure you want to delete this email template?"
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => void remove()}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  )
}
