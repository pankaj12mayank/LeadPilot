import {
  BarChart3,
  BriefcaseBusiness,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Search,
  Settings,
  Sparkles,
  User,
  Users,
  Receipt,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { toast } from 'sonner'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { PlanSection } from '@/components/layout/PlanSection'
import { ExpiredBanner } from '@/components/SubscriptionGate'
import { APP_NAME, DEFAULT_META_DESCRIPTION, ROUTE_META } from '@/lib/copy/appCopy'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/authStore'
import { useBrandingStore } from '@/store/brandingStore'
import { useUserConfigStore } from '@/store/userConfigStore'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/buyer-dashboard', label: 'Buyer', icon: BriefcaseBusiness },
  { to: '/search-leads', label: 'Explorer', icon: Search },
  { to: '/leads', label: 'Leads', icon: Users },
  { to: '/outreach-queue', label: 'Outreach', icon: ListChecks },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/user/transactions', label: 'Transactions', icon: Receipt },
  { to: '/user/profile', label: 'Profile', icon: User },
]

function pathKey(pathname: string) {
  const p = pathname.replace(/\/$/, '') || '/dashboard'
  return ROUTE_META[p] ? p : '/dashboard'
}

export function AppShell() {
  const { pathname } = useLocation()
  const productName = useBrandingStore((s) => s.branding.product_name)
  const logoUrl = useBrandingStore((s) => s.branding.logo_url)
  const mediaRevision = useBrandingStore((s) => s.mediaRevision)
  const { user, logout } = useAuthStore()
  const role = (user?.role || 'user') as 'admin' | 'user' | 'buyer'
  const startUserConfigSync = useUserConfigStore((s) => s.startSync)
  const stopUserConfigSync = useUserConfigStore((s) => s.stopSync)
  const clearUserConfig = useUserConfigStore((s) => s.clear)
  const configLoading = useUserConfigStore((s) => s.loading)
  const configSyncError = useUserConfigStore((s) => s.syncError)
  const lastConfigEventTs = useUserConfigStore((s) => s.lastEventTs)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const key = pathKey(pathname)
  const { title, subtitle, documentDescription } = ROUTE_META[key]

  useEffect(() => {
    document.title = `${title} | ${productName || APP_NAME}`
    const el = document.querySelector('meta[name="description"]')
    if (el) {
      el.setAttribute('content', documentDescription ?? DEFAULT_META_DESCRIPTION)
    }
  }, [title, documentDescription, productName])

  useEffect(() => {
    void startUserConfigSync()
    return () => { stopUserConfigSync() }
  }, [startUserConfigSync, stopUserConfigSync])

  useEffect(() => {
    if (configSyncError) toast.error('Config sync issue', { description: configSyncError })
  }, [configSyncError])

  useEffect(() => {
    if (!lastConfigEventTs) return
    toast.info('Admin rules updated', { description: 'Filters, scoring, and queue synced.' })
  }, [lastConfigEventTs])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const visibleNav = nav.filter((item) => {
    if (role === 'buyer') return ['/dashboard', '/buyer-dashboard', '/analytics', '/settings'].includes(item.to)
    if (role === 'user' && item.to === '/buyer-dashboard') return false
    return true
  })

  const configStatusLabel = configSyncError
    ? 'Config sync issue'
    : configLoading
      ? 'Syncing...'
      : lastConfigEventTs
        ? `Synced ${new Date(lastConfigEventTs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
        : 'Ready'

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-surface-border bg-white shadow-lg transition-transform duration-300 dark:bg-zinc-900 lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-3 border-b border-surface-border px-5">
          {logoUrl ? (
            <img
              src={`${resolveMediaUrl(logoUrl)}?v=${mediaRevision}`}
              alt=""
              className="h-8 w-8 shrink-0 rounded-lg object-contain"
            />
          ) : (
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/20">
              <Sparkles className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            </div>
          )}
          <span className="font-display text-base font-semibold text-zinc-900 dark:text-white">
            {productName || APP_NAME}
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1">
          {visibleNav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150',
                  isActive
                    ? 'bg-amber-500/10 text-amber-700 dark:bg-amber-400/10 dark:text-amber-300'
                    : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white',
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" strokeWidth={1.5} />
              {label}
            </NavLink>
          ))}
        </nav>

        <PlanSection />

        {/* User section */}
        <div className="border-t border-surface-border p-3">
          <div className="flex items-center gap-3 rounded-lg px-3 py-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-amber-500/20 text-xs font-semibold text-amber-700 dark:text-amber-300">
              {(user?.email || 'U')[0].toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-zinc-900 dark:text-white">{user?.email}</div>
              <div className="text-xs text-zinc-500 capitalize">{role}</div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Header */}
        <header className="flex h-16 items-center gap-4 border-b border-surface-border bg-white px-4 dark:bg-zinc-900 lg:px-6">
          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-white lg:hidden"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-semibold text-zinc-900 dark:text-white">{title}</h1>
            {subtitle && <p className="truncate text-xs text-zinc-500">{subtitle}</p>}
          </div>

          <div className="flex items-center gap-2">
            <span
              className={cn(
                'hidden rounded-md border px-2 py-1 text-[11px] font-medium lg:inline-block',
                configSyncError
                  ? 'border-red-500/30 bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300'
                  : configLoading
                    ? 'border-amber-500/30 bg-amber-50 text-amber-800 dark:bg-amber-950/30 dark:text-amber-200'
                    : 'border-emerald-500/25 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200',
              )}
            >
              {configStatusLabel}
            </span>

            <ThemeToggle />

            {/* User dropdown */}
            <div className="relative" ref={userMenuRef}>
              <button
                type="button"
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/15 text-xs font-semibold text-amber-700 hover:bg-amber-500/25 dark:text-amber-300"
              >
                {(user?.email || 'U')[0].toUpperCase()}
              </button>
              {userMenuOpen && (
                <div className="absolute right-0 top-full mt-2 w-48 rounded-lg border border-surface-border bg-white py-1 shadow-lg dark:bg-zinc-900">
                  <div className="border-b border-surface-border px-4 py-2">
                    <p className="truncate text-sm font-medium text-zinc-900 dark:text-white">{user?.email}</p>
                    <p className="text-xs text-zinc-500 capitalize">{role}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setUserMenuOpen(false)
                      stopUserConfigSync()
                      clearUserConfig()
                      logout()
                    }}
                    className="flex w-full items-center gap-2 px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
                  >
                    <LogOut className="h-4 w-4" strokeWidth={1.5} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <ExpiredBanner />
          <Outlet />
        </main>
      </div>
    </div>
  )
}
