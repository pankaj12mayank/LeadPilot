import {
  Info,
  LayoutDashboard,
  Layers,
  LineChart,
  LogOut,
  Search,
  Settings,
  Sparkles,
  Users,
} from 'lucide-react'
import { useEffect } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { MarketingFooter } from '@/components/layout/MarketingFooter'
import { TopNav } from '@/components/layout/TopNav'
import { APP_NAME, DEFAULT_META_DESCRIPTION, ROUTE_META } from '@/lib/copy/appCopy'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/authStore'
import { useBrandingStore } from '@/store/brandingStore'
import { useSidebarStore } from '@/store/sidebarStore'

const nav = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/search-leads', label: 'Lead search', icon: Search },
  { to: '/leads', label: 'Leads', icon: Users },
  { to: '/platforms', label: 'Platforms', icon: Layers },
  { to: '/analytics', label: 'Analytics', icon: LineChart },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/about', label: 'About', icon: Info },
]

function pathKey(pathname: string) {
  const p = pathname.replace(/\/$/, '') || '/dashboard'
  return ROUTE_META[p] ? p : '/dashboard'
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {nav.map(({ to, label, icon: Icon }) => (
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
            <div className="text-xs text-ink-subtle">Leads, platforms, outreach</div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          <NavItems onNavigate={() => setMobileOpen(false)} />
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col lg:pl-0">
        <TopNav
          title={title}
          subtitle={subtitle}
          headerActions={
            <div className="flex items-center gap-2">
              <span
                className="hidden max-w-[200px] truncate text-xs text-ink-subtle lg:inline"
                title={user?.email}
              >
                {user?.email}
              </span>
              <button
                type="button"
                onClick={() => logout()}
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
