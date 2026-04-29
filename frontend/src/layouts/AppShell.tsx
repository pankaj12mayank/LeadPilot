import {
  BriefcaseBusiness,
  Info,
  LayoutDashboard,
  LineChart,
  ListChecks,
  LogOut,
  Search,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { toast } from 'sonner'

import { MarketingFooter } from '@/components/layout/MarketingFooter'
import { TopNav } from '@/components/layout/TopNav'
import { APP_NAME, DEFAULT_META_DESCRIPTION, ROUTE_META } from '@/lib/copy/appCopy'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/authStore'
import { useBrandingStore } from '@/store/brandingStore'
import { useSidebarStore } from '@/store/sidebarStore'
import { useUserConfigStore } from '@/store/userConfigStore'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/buyer-dashboard', label: 'Buyer dashboard', icon: BriefcaseBusiness },
  { to: '/search-leads', label: 'Explorer', icon: Search },
  { to: '/leads', label: 'Leads', icon: Users },
  { to: '/outreach-queue', label: 'Outreach queue', icon: ListChecks },
  { to: '/analytics', label: 'Analytics', icon: LineChart },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/about', label: 'About', icon: Info },
]

function pathKey(pathname: string) {
  const p = pathname.replace(/\/$/, '') || '/dashboard'
  return ROUTE_META[p] ? p : '/dashboard'
}

function NavItems({ onNavigate, role }: { onNavigate?: () => void; role: 'admin' | 'user' | 'buyer' }) {
  const visibleNav = nav.filter((item) => {
    if (role === 'buyer') {
      return (
        item.to === '/dashboard' ||
        item.to === '/buyer-dashboard' ||
        item.to === '/analytics' ||
        item.to === '/settings' ||
        item.to === '/about'
      )
    }
    if (role === 'user' && item.to === '/buyer-dashboard') {
      return false
    }
    return true
  })
  return (
    <>
      {visibleNav.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-xl border px-3 py-2.5 text-sm font-medium transition-all duration-200',
              isActive
                ? 'border-amber-500/35 bg-gradient-to-r from-amber-500/12 to-emerald-600/8 text-ink shadow-sm ring-1 ring-amber-500/20 dark:from-amber-400/15 dark:to-emerald-500/10 dark:ring-amber-400/25'
                : 'border-transparent text-ink-muted hover:border-surface-border hover:bg-field/60 hover:text-ink dark:hover:bg-white/[0.04]',
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0 opacity-90" strokeWidth={1.5} />
          {label}
        </NavLink>
      ))}
    </>
  )
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
  const mobileOpen = useSidebarStore((s) => s.mobileOpen)
  const setMobileOpen = useSidebarStore((s) => s.setMobileOpen)
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
    return () => {
      stopUserConfigSync()
    }
  }, [startUserConfigSync, stopUserConfigSync])

  useEffect(() => {
    if (configSyncError) {
      toast.error('Config sync issue', { description: configSyncError })
    }
  }, [configSyncError])

  useEffect(() => {
    if (!lastConfigEventTs) return
    toast.info('Admin rules updated', {
      description: 'Filters, scoring, and queue behavior were synced to latest config.',
    })
  }, [lastConfigEventTs])

  const configStatusLabel = configSyncError
    ? 'Config sync issue'
    : configLoading
      ? 'Syncing admin rules'
      : lastConfigEventTs
        ? `Rules synced ${new Date(lastConfigEventTs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
        : 'Rules sync ready'

  return (
    <div className="flex min-h-screen bg-surface text-ink">
      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-zinc-900/40 backdrop-blur-sm dark:bg-black/60 lg:hidden"
          aria-label="Close menu"
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-surface-border bg-premium-card-light px-4 py-6 shadow-card transition-transform dark:bg-premium-card-dark lg:static lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        <div className="mb-8 flex items-center gap-2 px-2">
          {logoUrl ? (
            <img
              src={`${resolveMediaUrl(logoUrl)}?v=${mediaRevision}`}
              alt=""
              className="h-10 w-10 shrink-0 rounded-xl border border-surface-border bg-field object-contain p-0.5"
            />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/25 to-emerald-600/15 shadow-glow-gold ring-1 ring-amber-500/25 dark:from-amber-400/20 dark:to-emerald-500/10 dark:ring-amber-400/20">
              <Sparkles className="h-5 w-5 text-amber-700 dark:text-amber-300" strokeWidth={1.5} />
            </div>
          )}
          <div className="min-w-0">
            <div className="type-brand-wordmark truncate">{productName || APP_NAME}</div>
            <div className="text-xs text-ink-subtle">Leads, LinkedIn, outreach</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          <NavItems onNavigate={() => setMobileOpen(false)} role={role} />
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-0">
        <TopNav
          title={title}
          subtitle={subtitle}
          headerActions={
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'hidden rounded-full border px-2.5 py-1 text-[11px] font-medium lg:inline',
                  configSyncError
                    ? 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300'
                    : configLoading
                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-800 dark:text-amber-200'
                      : 'border-emerald-500/25 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200',
                )}
                title={configSyncError || configStatusLabel}
              >
                {configStatusLabel}
              </span>
              <span
                className="hidden max-w-[200px] truncate text-xs text-ink-subtle lg:inline"
                title={user?.email}
              >
                {user?.email}
              </span>
              <button
                type="button"
                onClick={() => {
                  stopUserConfigSync()
                  clearUserConfig()
                  logout()
                }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-2 text-xs font-medium text-ink-muted transition hover:border-amber-500/25 hover:text-ink dark:hover:border-emerald-500/20"
              >
                <LogOut className="h-3.5 w-3.5" strokeWidth={1.5} />
                Sign out
              </button>
            </div>
          }
        />
        <div className="flex-1 overflow-auto px-4 py-8 lg:px-10 lg:py-10">
          <Outlet />
          <MarketingFooter />
        </div>
      </div>
    </div>
  )
}
