import { Cable, Plus, RefreshCw, Search, Trash2, Wifi, WifiOff } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  adminGetConfig,
  adminPatchConfig,
  type AdminConfig,
} from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'
import { Modal } from '@/components/ui/Modal'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils/cn'

const sourceTypeColors: Record<string, string> = {
  job_board: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  directory: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  local: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  manual: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  marketplace: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300',
}

const sourceTypes = ['job_board', 'directory', 'local', 'manual', 'marketplace']
const inputTypes = ['url', 'keyword', 'file', 'csv']

export function AdminSourcesPage() {
  const [adminConfig, setAdminConfig] = useState<AdminConfig | null>(null)
  const [dirty, setDirty] = useState(false)
  const [showSave, setShowSave] = useState(false)
  const [saving, setSaving] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddSource, setShowAddSource] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Add/edit form state
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [formName, setFormName] = useState('')
  const [formType, setFormType] = useState<string>('directory')
  const [formInput, setFormInput] = useState<string>('url')
  const [formAdapter, setFormAdapter] = useState('')
  const [formEnabled, setFormEnabled] = useState(true)

  const load = useCallback(async () => {
    try {
      setAdminConfig(await adminGetConfig())
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not load config'))
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function saveSources() {
    if (!adminConfig) return
    setSaving(true)
    try {
      setAdminConfig(await adminPatchConfig(adminConfig))
      setShowSave(false)
      setDirty(false)
      toast.success('Source registry updated')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not save'))
    } finally { setSaving(false) }
  }

  const registry = adminConfig?.source_registry || []
  const totalSources = registry.length
  const enabledCount = registry.filter((s: any) => s.enabled).length
  const disabledCount = totalSources - enabledCount

  const filteredRegistry = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return registry
    return registry.filter((s: any) =>
      s.source_name.toLowerCase().includes(q) || s.source_type.toLowerCase().includes(q)
    )
  }, [registry, searchQuery])

  function openAdd() {
    setEditIdx(null)
    setFormName('')
    setFormType('directory')
    setFormInput('url')
    setFormAdapter('')
    setFormEnabled(true)
    setShowAddSource(true)
  }

  function openEdit(idx: number) {
    const src = registry[idx]
    if (!src) return
    setEditIdx(idx)
    setFormName(src.source_name)
    setFormType(src.source_type)
    setFormInput(src.input_type)
    setFormAdapter(src.adapter_function)
    setFormEnabled(src.enabled)
    setShowAddSource(true)
  }

  function saveSourceEntry() {
    if (!adminConfig) return
    const entry = {
      source_name: formName.trim(),
      source_type: formType as 'job_board' | 'directory' | 'local' | 'manual' | 'marketplace',
      enabled: formEnabled,
      input_type: formInput as 'url' | 'keyword' | 'file' | 'csv',
      adapter_function: formAdapter.trim() || 'generic_adapter',
    }
    const next = [...registry]
    if (editIdx !== null) {
      next[editIdx] = entry
    } else {
      next.push(entry)
    }
    setAdminConfig({ ...adminConfig, source_registry: next })
    setShowAddSource(false)
    setDirty(true)
    toast.success(editIdx !== null ? 'Source updated' : 'Source added')
  }

  function deleteSource() {
    if (!adminConfig || deleteTarget === null) return
    setDeleting(true)
    try {
      const next = registry.filter((_: any, i: any) => i !== deleteTarget)
      setAdminConfig({ ...adminConfig, source_registry: next })
      setDeleteTarget(null)
      setDirty(true)
      toast.success('Source removed')
    } finally { setDeleting(false) }
  }

  function toggleEnabled(idx: number) {
    if (!adminConfig) return
    const next = [...registry]
    next[idx] = { ...next[idx], enabled: !next[idx].enabled }
    setAdminConfig({ ...adminConfig, source_registry: next })
    setDirty(true)
  }

  if (!adminConfig) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Source Registry</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Register, enable, disable, or remove data sources</p>
        </div>
        <button
          type="button"
          disabled={!dirty}
          onClick={() => setShowSave(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-45"
        >
          <RefreshCw className={cn('h-4 w-4', saving && 'animate-spin')} />
          Save Changes
        </button>
      </div>

      {/* Status cards - based on registry only */}
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10">
              <Cable className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Total Sources</p>
              <p className="mt-1 font-display text-2xl font-bold text-zinc-900 dark:text-white">{totalSources}</p>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10">
              <Wifi className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Enabled</p>
              <p className="mt-1 font-display text-2xl font-bold text-emerald-600 dark:text-emerald-400">{enabledCount}</p>
            </div>
          </div>
        </div>
        <div className="rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-500/10">
              <WifiOff className="h-5 w-5 text-zinc-500" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Disabled</p>
              <p className="mt-1 font-display text-2xl font-bold text-zinc-500 dark:text-zinc-300">{disabledCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Source Registry Table */}
      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-surface-border px-4 py-3">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-white">
            Registered Sources
            {totalSources > 0 && <span className="ml-1.5 text-xs font-normal text-zinc-500">({totalSources})</span>}
          </h2>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-44 rounded-lg border border-surface-border bg-transparent py-1.5 pl-8 pr-2.5 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
              />
            </div>
            <button
              type="button"
              onClick={() => openAdd()}
              className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-amber-700"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Source
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-zinc-50/50 text-xs uppercase text-zinc-500 dark:bg-zinc-800/50">
                <th className="px-5 py-3 font-semibold">Source</th>
                <th className="py-3 pr-4 font-semibold">Type</th>
                <th className="py-3 pr-4 font-semibold">Status</th>
                <th className="py-3 pr-4 font-semibold">Input</th>
                <th className="py-3 pr-4 font-semibold">Adapter</th>
                <th className="py-3 pr-4 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRegistry.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-zinc-500 dark:text-zinc-400">
                    {totalSources === 0 ? 'No sources registered. Click "Add Source" to register one.' : 'No matches for search.'}
                  </td>
                </tr>
              ) : filteredRegistry.map((src: any) => {
                const realIdx = registry.indexOf(src)
                return (
                  <tr key={realIdx} className="border-b border-surface-border/70 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                    <td className="px-5 py-3 font-medium text-zinc-900 dark:text-white">{src.source_name}</td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${sourceTypeColors[src.source_type] || 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400'}`}>
                        {src.source_type}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <button
                        type="button"
                        onClick={() => toggleEnabled(realIdx)}
                        className={cn(
                          'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition',
                          src.enabled
                            ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-500/20'
                            : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700',
                        )}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${src.enabled ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
                        {src.enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs text-zinc-500 dark:text-zinc-400">{src.input_type}</td>
                    <td className="py-3 pr-4 font-mono text-[11px] text-zinc-500 dark:text-zinc-400">{src.adapter_function}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(realIdx)}
                          className="rounded-lg border border-surface-border px-2.5 py-1 text-xs font-medium text-zinc-600 transition hover:border-amber-500/30 hover:text-amber-700 dark:text-zinc-400 dark:hover:text-amber-300"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(realIdx)}
                          className="rounded-lg border border-red-500/35 px-2.5 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Source Modal */}
      <Modal
        open={showAddSource}
        title={editIdx !== null ? 'Edit Source' : 'Add Source'}
        titleHint="Register a new data source"
        onClose={() => { setShowAddSource(false); setEditIdx(null) }}
      >
        <div className="space-y-4">
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Source Name</span>
            <input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="e.g. AngelList, Crunchbase"
              className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Source Type</span>
              <select value={formType} onChange={(e) => setFormType(e.target.value)} className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900">
                {sourceTypes.map((t) => (
                  <option key={t} value={t}>{t.replace('_', ' ')}</option>
                ))}
              </select>
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Input Type</span>
              <select value={formInput} onChange={(e) => setFormInput(e.target.value)} className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900">
                {inputTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
          </div>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Adapter Function</span>
            <input
              value={formAdapter}
              onChange={(e) => setFormAdapter(e.target.value)}
              placeholder="generic_adapter"
              className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 font-mono text-sm dark:bg-zinc-900"
            />
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-surface-border px-4 py-3 cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-800">
            <input
              type="checkbox"
              checked={formEnabled}
              onChange={(e) => setFormEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-surface-border text-amber-600 focus:ring-amber-500"
            />
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Keep enabled after creation</span>
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => { setShowAddSource(false); setEditIdx(null) }}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!formName.trim()}
              onClick={() => saveSourceEntry()}
              className="rounded-lg bg-amber-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-45"
            >
              {editIdx !== null ? 'Update Source' : 'Add Source'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="Remove Source"
        message="Are you sure you want to remove this source from the registry? This action cannot be undone."
        confirmLabel="Remove"
        variant="danger"
        busy={deleting}
        onConfirm={() => void deleteSource()}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Save confirmation */}
      <ConfirmDialog
        open={showSave}
        title="Save Source Registry"
        message="This will update all registered sources. Are you sure?"
        confirmLabel="Save Changes"
        variant="warning"
        busy={saving}
        onConfirm={() => void saveSources()}
        onCancel={() => setShowSave(false)}
      />
    </div>
  )
}
