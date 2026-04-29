import { Bot, LayoutDashboard, ListChecks, LogOut, Palette, Shield, Users } from 'lucide-react'
import { Link, Navigate, NavLink, Outlet } from 'react-router-dom'

import { useAdminStore } from '@/store/adminStore'
import { cn } from '@/lib/utils/cn'

const nav = [
  { to: '/admin/overview#dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/overview#channels', label: 'Channels', icon: ListChecks },
  { to: '/admin/overview#ai-settings', label: 'AI Settings', icon: Bot },
  { to: '/admin/overview#logs', label: 'Logs', icon: LayoutDashboard },
  { to: '/admin/branding', label: 'Branding', icon: Palette },
  { to: '/admin/landing', label: 'Landing CMS', icon: Palette },
]

export function AdminLayout() {
  const token = useAdminStore((s) => s.token)
  const logout = useAdminStore((s) => s.logout)

  if (!token) {
    return <Navigate to="/login?next=%2Fadmin" replace />
  }

  return (
    <div className="min-h-screen bg-surface text-ink">
      <header className="border-b border-surface-border bg-gradient-to-b from-premium-card-light to-transparent px-4 py-4 dark:from-premium-card-dark">
        <div className="mx-auto flex max-w-6xl flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            to="/admin/overview"
            className="flex items-center gap-2 rounded-lg outline-none ring-offset-2 transition hover:opacity-90 focus-visible:ring-2 focus-visible:ring-amber-500/40"
          >
            <Shield className="h-5 w-5 text-amber-700 dark:text-amber-300" />
            <span className="font-display text-sm font-semibold tracking-tight">LeadPilot Admin Console</span>
          </Link>
            <button
              type="button"
              onClick={() => logout()}
              className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-3 py-2 text-ink-muted transition hover:text-ink"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
          <nav className="flex flex-wrap items-center gap-2 rounded-xl border border-surface-border bg-premium-card-light/70 p-1 text-sm dark:bg-premium-card-dark/60">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    'inline-flex items-center gap-1.5 rounded-lg px-3 py-2 font-medium transition',
                    isActive
                      ? 'bg-amber-500/15 text-ink shadow-sm'
                      : 'text-ink-muted hover:bg-field/80 hover:text-ink dark:hover:bg-white/[0.04]',
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0 opacity-90" strokeWidth={1.75} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
