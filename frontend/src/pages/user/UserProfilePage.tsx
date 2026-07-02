import { Eye, EyeOff, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { userChangePassword, userUpdateProfile } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'
import { useAuthStore } from '@/store/authStore'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function UserProfilePage() {
  const authUser = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [nameBusy, setNameBusy] = useState(false)
  const [pwBusy, setPwBusy] = useState(false)
  const [showPwConfirm, setShowPwConfirm] = useState(false)

  useEffect(() => {
    if (authUser) {
      setName(authUser.name || '')
      setEmail(authUser.email || '')
    }
  }, [authUser])

  async function saveName() {
    setNameBusy(true)
    try {
      await userUpdateProfile({ name: name.trim() || undefined })
      toast.success('Name updated')
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not update name'))
    } finally {
      setNameBusy(false)
    }
  }

  async function changePassword() {
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setPwBusy(true)
    try {
      await userChangePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setShowPwConfirm(false)
      toast.success('Password changed', {
        description: 'Please login again with your new password.',
      })
      setTimeout(() => {
        logout()
        window.location.href = '/login'
      }, 1500)
    } catch (e) {
      toast.error(getApiErrorMessage(e, 'Could not change password'))
    } finally {
      setPwBusy(false)
    }
  }

  function PasswordBlock({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
    const [visible, setVisible] = useState(false)
    const id = label.toLowerCase().replace(/\s+/g, '-')
    return (
      <div className="space-y-1.5">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400" htmlFor={id}>
          {label}
        </label>
        <div className="relative">
          <input
            id={id}
            type={visible ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="w-full rounded-lg border border-surface-border bg-transparent px-3 py-2 pr-10 text-sm outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
          />
          <button
            type="button"
            tabIndex={-1}
            onClick={() => setVisible((v) => !v)}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
            aria-label={visible ? 'Hide password' : 'Show password'}
          >
            {visible ? <EyeOff className="h-3.5 w-3.5" strokeWidth={1.5} /> : <Eye className="h-3.5 w-3.5" strokeWidth={1.5} />}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Profile</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Manage your account settings and password</p>
      </div>

      {loadErr && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
          {loadErr}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Name */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Display Name</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Set your display name shown across the platform.</p>
          <div className="mt-4 flex gap-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="flex-1 rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25"
            />
            <button
              type="button"
              disabled={nameBusy}
              onClick={() => void saveName()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              {nameBusy ? '...' : 'Save'}
            </button>
          </div>
        </div>

        {/* Email (read-only) */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Email</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Your login email address. Contact support to change it.</p>
          <div className="mt-4">
            <input
              value={email}
              readOnly
              className="w-full rounded-lg border border-surface-border bg-zinc-50 px-3 py-2 text-sm text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400 cursor-not-allowed"
            />
          </div>
        </div>
      </div>

      {/* Password - full width */}
      <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
        <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Change Password</h2>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Update your password to keep your account secure.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <PasswordBlock label="Current Password" value={currentPassword} onChange={setCurrentPassword} placeholder="Enter current password" />
          <PasswordBlock label="New Password" value={newPassword} onChange={setNewPassword} placeholder="At least 8 characters" />
          <PasswordBlock label="Confirm Password" value={confirmPassword} onChange={setConfirmPassword} placeholder="Repeat new password" />
        </div>
        <button
          type="button"
          disabled={!currentPassword || !newPassword || !confirmPassword}
          onClick={() => setShowPwConfirm(true)}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-700 disabled:opacity-45"
        >
          Change Password
        </button>
      </div>

      <ConfirmDialog
        open={showPwConfirm}
        title="Change Password"
        message="Are you sure you want to change your password? You will need to use the new password next time you sign in."
        confirmLabel="Change Password"
        variant="warning"
        busy={pwBusy}
        onConfirm={() => void changePassword()}
        onCancel={() => setShowPwConfirm(false)}
      />
    </div>
  )
}