import { BarChart3, Cable, CreditCard, Gauge, Inbox, LogOut, Mail, Palette, ScrollText, Shield, Sliders, User, Users, Wallet } from 'lucide-react'
import { Navigate, NavLink, Outlet } from 'react-router-dom'

import { useAdminStore } from '@/store/adminStore'
import { cn } from '@/lib/utils/cn'

const nav = [
  { to: '/admin/overview', label: 'Dashboard', icon: Gauge },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/lead-packs', label: 'Lead Packs', icon: Wallet },
  { to: '/admin/scoring', label: 'Scoring & Schedule', icon: Sliders },
  { to: '/admin/plans', label: 'Plans & Channels', icon: BarChart3 },
  { to: '/admin/sources', label: 'Source Registry', icon: Cable },
  { to: '/admin/job-logs', label: 'Job Logs', icon: ScrollText },
  { to: '/admin/branding', label: 'Branding', icon: Palette },
  { to: '/admin/profile', label: 'Profile', icon: User },
  { to: '/admin/newsletter', label: 'Newsletter', icon: Mail },
  { to: '/admin/inbox', label: 'Inbox', icon: Inbox },
  { to: '/admin/payment-gateway', label: 'Payment Gateway', icon: CreditCard },
  { to: '/admin/email-config', label: 'Email Config', icon: Mail },
  { to: '/admin/email-templates', label: 'Email Templates', icon: ScrollText },
  { to: '/admin/transactions', label: 'Transactions', icon: Wallet },
]

export function AdminLayout() {
  const token = useAdminStore((s) => s.token)
  const logout = useAdminStore((s) => s.logout)

  if (!token) {
    return <Navigate to="/login?next=%2Fadmin" replace />
  }

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-surface-border bg-white dark:bg-zinc-900">
        <div className="flex h-16 items-center gap-3 border-b border-surface-border px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 shadow-sm">
            <Shield className="h-4 w-4 text-white" />
          </div>
          <div>
            <span className="block text-sm font-semibold text-zinc-900 dark:text-white">Admin Console</span>
            <span className="block text-[11px] text-zinc-500">LeadPilot Control</span>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/admin/overview'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-amber-500/10 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300'
                    : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white',
                )
              }
            >
              <Icon className="h-4 w-4" strokeWidth={1.5} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-surface-border p-3">
          <button
            type="button"
            onClick={logout}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-surface-border px-3 py-2 text-xs font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="flex h-16 items-center border-b border-surface-border bg-white px-6 dark:bg-zinc-900">
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-white">Admin Panel</h1>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
