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
import { cn } from '@/lib/utils/cn'

function fmtLogin(iso: string) {
  if (!iso) return '—'
  return iso.length >= 16 ? iso.slice(0, 16).replace('T', ' ') : iso
}

export function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserRow[]>([])
  const [stats, setStats] = useState<AdminWorkspaceStats | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [busy, setBusy] = useState(false)
  const [newEmail, setNewEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [pwTarget, setPwTarget] = useState<AdminUserRow | null>(null)
  const [pwValue, setPwValue] = useState('')
  const [pwBusy, setPwBusy] = useState(false)

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

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return users
    return users.filter((x) => x.email.toLowerCase().includes(q))
  }, [users, search])

  async function onToggleActive(u: AdminUserRow) {
    try {
      const up = await adminSetUserActive(u.id, !u.is_active)
      setUsers((rows) => rows.map((r) => (r.id === up.id ? up : r)))
      setStats(await adminGetStats())
      toast.success(up.is_active ? 'User activated' : 'User marked inactive')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Update failed'))
    }
  }

  async function submitPasswordReset() {
    if (!pwTarget) return
    if (pwValue.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setPwBusy(true)
    try {
      await adminSetUserPassword(pwTarget.id, pwValue)
      setPwTarget(null)
      setPwValue('')
      toast.success('Password updated')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not update password'))
    } finally {
      setPwBusy(false)
    }
  }

  async function onCreate() {
    setBusy(true)
    try {
      await adminCreateUser(newEmail.trim(), newPassword)
      setNewEmail('')
      setNewPassword('')
      await load()
      toast.success('User created')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not create user'))
    } finally {
      setBusy(false)
    }
  }

  async function onDeleteOne(userId: string, email: string) {
    if (!window.confirm(`Delete user "${email}"? This cannot be undone.`)) return
    setBusy(true)
    try {
      await adminBulkDeleteUsers([userId])
      await load()
      toast.success('User removed')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Delete failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Users</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Accounts for the user portal (not admin). Use search and row actions to manage access; last login updates
          automatically when a user signs in.
        </p>
      </section>

      {loadErr ? <p className="text-sm text-red-600 dark:text-red-400">{loadErr}</p> : null}

      {stats ? (
        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Total users</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink">{stats.registered_users}</div>
          </div>
          <div className="rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-5 shadow-card dark:border-emerald-500/20 dark:bg-emerald-950/25">
            <div className="text-xs font-semibold uppercase tracking-wider text-emerald-900 dark:text-emerald-200/90">
              Active
            </div>
            <div className="mt-2 font-display text-3xl font-bold text-emerald-800 dark:text-emerald-200">
              {stats.active_users ?? users.filter((u) => u.is_active).length}
            </div>
          </div>
          <div className="rounded-2xl border border-surface-border bg-field/60 p-5 shadow-card dark:bg-zinc-900/50">
            <div className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Inactive</div>
            <div className="mt-2 font-display text-3xl font-bold text-ink-muted">
              {stats.inactive_users ?? users.filter((u) => !u.is_active).length}
            </div>
          </div>
        </section>
      ) : null}

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark">
        <h2 className="text-sm font-semibold text-ink">Add user</h2>
        <p className="mt-1 text-xs text-ink-subtle">Share the temporary password securely; the user can change it after login when you add that flow.</p>
        <div className="mx-auto mt-4 max-w-2xl space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="nu-email">
              Email
            </label>
            <input
              id="nu-email"
              className="field-input mt-2 w-full"
              placeholder="name@company.com"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              autoComplete="off"
            />
          </div>
          <PasswordField
            id="nu-pw"
            label="Temporary password"
            value={newPassword}
            onChange={setNewPassword}
            autoComplete="new-password"
            minLength={8}
            placeholder="At least 8 characters"
          />
          <div className="flex justify-end">
            <button
              type="button"
              disabled={busy || !newEmail.trim() || newPassword.length < 8}
              className="rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:from-amber-500 hover:to-amber-600 disabled:opacity-45 dark:from-amber-500 dark:to-amber-600"
              onClick={() => void onCreate()}
            >
              {busy ? 'Creating…' : 'Create account'}
            </button>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-ink">User list</h2>
            <p className="text-xs text-ink-subtle">No bulk select. Manage accounts with clear row actions.</p>
          </div>
          <div className="max-w-2xl">
            <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted" htmlFor="user-search">
              Search by email
            </label>
            <input
              id="user-search"
              className="field-input mt-1 w-full"
              placeholder="Filter by email…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border text-xs uppercase text-ink-muted">
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Last login</th>
                <th className="py-2 pr-4">Created</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="border-b border-surface-border/80">
                  <td className="py-2 pr-4 align-middle font-medium text-ink">{u.email}</td>
                  <td className="py-2 pr-4 align-middle">
                    <button
                      type="button"
                      onClick={() => void onToggleActive(u)}
                      className={cn(
                        'rounded-full border px-2.5 py-0.5 text-xs font-medium transition',
                        u.is_active
                          ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-900 dark:text-emerald-200'
                          : 'border-surface-border bg-field/80 text-ink-muted',
                      )}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td className="py-2 pr-4 align-middle text-xs text-ink-muted tabular-nums">{fmtLogin(u.last_login_at)}</td>
                  <td className="py-2 pr-4 align-middle text-xs text-ink-muted tabular-nums">{fmtLogin(u.created_at)}</td>
                  <td className="py-2 align-middle">
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setPwTarget(u)
                          setPwValue('')
                        }}
                        className="rounded-lg border border-surface-border px-2 py-1 text-xs font-medium text-ink-muted transition hover:border-amber-500/30 hover:text-ink"
                      >
                        Set password
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void onDeleteOne(u.id, u.email)}
                        className="rounded-lg border border-red-500/35 px-2 py-1 text-xs font-semibold text-red-700 disabled:opacity-50 dark:text-red-300"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && !loadErr ? (
            <p className="mt-4 text-sm text-ink-muted">{users.length === 0 ? 'No users yet.' : 'No matches for this search.'}</p>
          ) : null}
        </div>
      </section>

      <Modal
        open={!!pwTarget}
        title={pwTarget ? `Reset password` : ''}
        titleHint={pwTarget?.email}
        onClose={() => {
          if (!pwBusy) {
            setPwTarget(null)
            setPwValue('')
          }
        }}
      >
        {pwTarget ? (
          <div className="space-y-4 text-sm">
            <p className="text-ink-muted">
              Set a new password for <span className="font-medium text-ink">{pwTarget.email}</span>.
            </p>
            <PasswordField
              id="admin-reset-pw"
              label="New password"
              value={pwValue}
              onChange={setPwValue}
              autoComplete="new-password"
              minLength={8}
            />
            <div className="flex flex-wrap justify-end gap-2 pt-2">
              <button
                type="button"
                disabled={pwBusy}
                className="rounded-xl border border-surface-border px-4 py-2 text-sm font-medium text-ink-muted transition hover:text-ink"
                onClick={() => {
                  setPwTarget(null)
                  setPwValue('')
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={pwBusy || pwValue.length < 8}
                className="rounded-xl bg-gradient-to-r from-amber-600 to-amber-700 px-4 py-2 text-sm font-semibold text-white shadow-sm disabled:opacity-45"
                onClick={() => void submitPasswordReset()}
              >
                {pwBusy ? 'Saving…' : 'Save password'}
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
