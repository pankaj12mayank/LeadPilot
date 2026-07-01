import { Plus, Search, Shield, UserCheck, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  adminBulkDeleteUsers,
  adminCreateUser,
  adminGetStats,
  adminListUsers,
  adminSetUserActive,
  adminSetUserPassword,
  type AdminUserRow,
  type AdminWorkspaceStats,
} from '@/lib/api/admin'
import { getApiErrorMessage } from '@/lib/api/client'
import { Modal } from '@/components/ui/Modal'
import { PasswordField } from '@/components/ui/PasswordField'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { cn } from '@/lib/utils/cn'

const roleStyles: Record<string, string> = {
  admin: 'border-purple-500/30 bg-purple-500/10 text-purple-700 dark:text-purple-300',
  user: 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  buyer: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
}

const planLabels: Record<string, string> = {
  starter: 'Starter',
  growth: 'Growth',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

function fmtDate(iso: string) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}

function getInitials(email: string) {
  return email.charAt(0).toUpperCase()
}

function getAvatarColor(email: string) {
  const colors = [
    'bg-amber-500', 'bg-blue-500', 'bg-emerald-500', 'bg-violet-500',
    'bg-rose-500', 'bg-cyan-500', 'bg-orange-500', 'bg-pink-500',
  ]
  let hash = 0
  for (let i = 0; i < email.length; i++) {
    hash = email.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

export function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState<'admin' | 'user' | 'buyer'>('user')
  const [newPlanId, setNewPlanId] = useState<'starter' | 'growth' | 'pro' | 'enterprise'>('starter')
  const [pwTarget, setPwTarget] = useState<AdminUserRow | null>(null)
  const [pwValue, setPwValue] = useState('')
  const [pwBusy, setPwBusy] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<AdminUserRow | null>(null)
  const [toggleTarget, setToggleTarget] = useState<AdminUserRow | null>(null)
  const [toggleBusy, setToggleBusy] = useState(false)

  const load = useCallback(async () => {
    setLoadErr(null)
    try {
      const [u, s] = await Promise.all([adminListUsers(), adminGetStats()])
      setUsers(u)
      setStats(s)
    } catch (e) {
      setLoadErr(getApiErrorMessage(e, 'Could not load users.'))
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return users
    return users.filter((x) => x.email.toLowerCase().includes(q))
  }, [users, search])

  async function confirmToggle() {
    if (!toggleTarget) return
    setToggleBusy(true)
    try {
      const u = toggleTarget
      const up = await adminSetUserActive(u.id, !u.is_active)
      setUsers((rows) => rows.map((r) => (r.id === up.id ? up : r)))
      setStats(await adminGetStats())
      setToggleTarget(null)
      toast.success(up.is_active ? 'User activated' : 'User deactivated')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Update failed'))
    } finally { setToggleBusy(false) }
  }

  async function submitPasswordReset() {
    if (!pwTarget) return
    if (pwValue.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setPwBusy(true)
    try {
      await adminSetUserPassword(pwTarget.id, pwValue)
      setPwTarget(null); setPwValue('')
      toast.success('Password updated')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not update password'))
    } finally { setPwBusy(false) }
  }

  async function onCreate() {
    setBusy(true)
    try {
      await adminCreateUser({ email: newEmail.trim(), password: newPassword, role: newRole, plan_id: newPlanId })
      setNewEmail(''); setNewPassword(''); setNewRole('user'); setNewPlanId('starter')
      setShowAddModal(false)
      await load()
      toast.success('User created successfully')
    } catch (e) { toast.error(getApiErrorMessage(e, 'Could not create user'))
    } finally { setBusy(false) }
  }

  async function onDelete() {
    if (!deleteTarget) return
    setBusy(true)
    try {
      await adminBulkDeleteUsers([deleteTarget.id])
      await load()
      toast.success(`User "${deleteTarget.email}" removed`)
      setDeleteTarget(null)
    } catch (e) { toast.error(getApiErrorMessage(e, 'Delete failed'))
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Users</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Manage workspace accounts &mdash; create, activate, or remove users.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:from-amber-700 hover:to-amber-600"
        >
          <Plus className="h-4 w-4" />
          Add User
        </button>
      </div>

      {loadErr && (
        <div className="rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">{loadErr}</div>
      )}

      {/* Stats Cards */}
      {stats && (
        <section className="grid gap-4 sm:grid-cols-3">
          <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-white p-5 shadow-sm dark:bg-zinc-900">
            <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-zinc-500/5" />
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Total Users</p>
            <p className="mt-2 font-display text-3xl font-bold text-zinc-900 dark:text-white">{stats.registered_users}</p>
          </div>
          <div className="relative overflow-hidden rounded-2xl border border-emerald-500/25 bg-gradient-to-br from-emerald-50 to-white p-5 shadow-sm dark:border-emerald-500/20 dark:from-emerald-950/25 dark:to-zinc-900">
            <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-emerald-500/10" />
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">Active</p>
            <p className="mt-2 font-display text-3xl font-bold text-emerald-700 dark:text-emerald-300">
              {stats.active_users ?? users.filter((u) => u.is_active).length}
            </p>
          </div>
          <div className="relative overflow-hidden rounded-2xl border border-surface-border bg-gradient-to-br from-zinc-50 to-white p-5 shadow-sm dark:from-zinc-900 dark:to-zinc-900">
            <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-zinc-500/5" />
            <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Inactive</p>
            <p className="mt-2 font-display text-3xl font-bold text-zinc-500 dark:text-zinc-300">
              {stats.inactive_users ?? users.filter((u) => !u.is_active).length}
            </p>
          </div>
        </section>
      )}

      {/* User Table */}
      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="border-b border-surface-border px-5 py-4">
          <div className="relative max-w-sm">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by email..."
              className="w-full rounded-lg border border-surface-border bg-transparent py-2 pl-9 pr-3 text-sm outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25"
            />
            {search && (
              <button type="button" onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border bg-zinc-50/50 text-xs uppercase text-zinc-500 dark:bg-zinc-800/50">
                <th className="px-5 py-3 font-semibold">User</th>
                <th className="py-3 pr-4 font-semibold">Status</th>
                <th className="py-3 pr-4 font-semibold">Role</th>
                <th className="py-3 pr-4 font-semibold">Plan</th>
                <th className="py-3 pr-4 font-semibold">Last Login</th>
                <th className="py-3 pr-4 font-semibold">Created</th>
                <th className="py-3 pr-4 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-zinc-500">
                    {users.length === 0 ? (
                      <div className="flex flex-col items-center gap-2">
                        <UserCheck className="h-8 w-8 text-zinc-300 dark:text-zinc-600" />
                        <span>No users yet. Click "Add User" to create one.</span>
                      </div>
                    ) : (
                      'No matches for this search.'
                    )}
                  </td>
                </tr>
              ) : filtered.map((u) => (
                <tr key={u.id} className="border-b border-surface-border/70 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-9 w-9 items-center justify-center rounded-full ${getAvatarColor(u.email)} text-sm font-bold text-white shadow-sm`}>
                        {getInitials(u.email)}
                      </div>
                      <span className="font-medium text-zinc-900 dark:text-white">{u.email}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <button
                      type="button"
                      onClick={() => setToggleTarget(u)}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition',
                        u.is_active
                          ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                          : 'border-surface-border bg-zinc-100 text-zinc-500 dark:bg-zinc-800',
                      )}
                    >
                      <span className={cn('h-1.5 w-1.5 rounded-full', u.is_active ? 'bg-emerald-500' : 'bg-zinc-400')} />
                      {u.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={cn(
                      'inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize',
                      roleStyles[u.role || 'user'] || 'border-surface-border bg-zinc-50 text-zinc-600 dark:bg-zinc-800',
                    )}>
                      {u.role || 'user'}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <select
                      value={u.plan_id || 'starter'}
                      onChange={async (e) => {
                        try {
                          await adminUpdateUser(u.id, { plan_id: e.target.value })
                          setUsers((rows) => rows.map((r) => (r.id === u.id ? { ...r, plan_id: e.target.value } : r)))
                          toast.success('Plan updated')
                        } catch (err) { toast.error(getApiErrorMessage(err, 'Could not update plan')) }
                      }}
                      className="rounded-lg border border-surface-border bg-white px-2 py-1 text-xs font-medium dark:bg-zinc-900"
                    >
                      {Object.entries(planLabels).map(([val, label]) => (
                        <option key={val} value={val}>{label}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-3 pr-4 text-xs text-zinc-500 dark:text-zinc-400">{fmtDate(u.last_login_at)}</td>
                  <td className="py-3 pr-4 text-xs text-zinc-500 dark:text-zinc-400">{fmtDate(u.created_at)}</td>
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => { setPwTarget(u); setPwValue('') }}
                        className="rounded-lg border border-surface-border px-2.5 py-1 text-xs font-medium text-zinc-600 transition hover:border-amber-500/30 hover:text-amber-700 dark:text-zinc-400 dark:hover:text-amber-300"
                      >
                        Reset Password
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => setDeleteTarget(u)}
                        className="rounded-lg border border-red-500/35 px-2.5 py-1 text-xs font-semibold text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/30"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Toggle active confirmation */}
      {toggleTarget && (
        <ConfirmDialog
          open={true}
          title={toggleTarget.is_active ? 'Deactivate User' : 'Activate User'}
          message={
            toggleTarget.is_active
              ? `This will deactivate "${toggleTarget.email}". They will not be able to sign in until reactivated.`
              : `This will reactivate "${toggleTarget.email}" and restore access.`
          }
          confirmLabel={toggleTarget.is_active ? 'Deactivate' : 'Activate'}
          variant="warning"
          busy={toggleBusy}
          onConfirm={() => void confirmToggle()}
          onCancel={() => setToggleTarget(null)}
        />
      )}

      {/* Add User Modal */}
      <Modal
        open={showAddModal}
        title="Add User"
        titleHint="Create a new workspace account"
        onClose={() => { if (!busy) { setShowAddModal(false); setNewEmail(''); setNewPassword(''); setNewRole('user'); setNewPlanId('starter') } }}
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Role</span>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as 'admin' | 'user' | 'buyer')}
                className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900"
              >
                <option value="user">User</option>
                <option value="buyer">Buyer</option>
                <option value="admin">Admin</option>
              </select>
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Plan</span>
              <select
                value={newPlanId}
                onChange={(e) => setNewPlanId(e.target.value as 'starter' | 'growth' | 'pro' | 'enterprise')}
                className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900"
              >
                <option value="starter">Starter</option>
                <option value="growth">Growth</option>
                <option value="pro">Pro</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </label>
          </div>
          <label className="space-y-1.5">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">Email</span>
            <input
              className="w-full rounded-lg border border-surface-border bg-white px-3 py-2 text-sm dark:bg-zinc-900"
              placeholder="name@company.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              autoComplete="off"
            />
          </label>
          <PasswordField
            id="nu-pw"
            label="Temporary Password"
            value={newPassword}
            onChange={setNewPassword}
            autoComplete="new-password"
            minLength={8}
            placeholder="At least 8 characters"
          />
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => { setShowAddModal(false); setNewEmail(''); setNewPassword(''); setNewRole('user'); setNewPlanId('starter') }}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !newEmail.trim() || newPassword.length < 8}
              className="rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:from-amber-700 hover:to-amber-600 disabled:opacity-45"
              onClick={() => void onCreate()}
            >
              {busy ? 'Creating...' : 'Create Account'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Reset Password Modal */}
      <Modal
        open={!!pwTarget}
        title="Reset Password"
        titleHint={pwTarget?.email}
        onClose={() => { if (!pwBusy) { setPwTarget(null); setPwValue('') } }}
      >
        {pwTarget && (
          <div className="space-y-4">
            <p className="text-sm text-zinc-500">
              Set a new password for <span className="font-medium text-zinc-900 dark:text-white">{pwTarget.email}</span>.
            </p>
            <PasswordField
              id="admin-reset-pw"
              label="New Password"
              value={pwValue}
              onChange={setPwValue}
              autoComplete="new-password"
              minLength={8}
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={pwBusy}
                className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
                onClick={() => { setPwTarget(null); setPwValue('') }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={pwBusy || pwValue.length < 8}
                className="rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:from-amber-700 hover:to-amber-600 disabled:opacity-45"
                onClick={() => void submitPasswordReset()}
              >
                {pwBusy ? 'Saving...' : 'Save Password'}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={!!deleteTarget}
        title="Delete User"
        titleHint="This action cannot be undone"
        onClose={() => { if (!busy) setDeleteTarget(null) }}
      >
        {deleteTarget && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-50/50 p-4 dark:bg-red-950/20">
              <Shield className="h-5 w-5 text-red-500 shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-300">
                You are about to permanently delete <strong>{deleteTarget.email}</strong>.
                All associated data will be removed.
              </p>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                disabled={busy}
                className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
                onClick={() => setDeleteTarget(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="rounded-lg bg-gradient-to-r from-red-600 to-red-500 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:from-red-700 hover:to-red-600 disabled:opacity-45"
                onClick={() => void onDelete()}
              >
                {busy ? 'Deleting...' : 'Delete User'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
