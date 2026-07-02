import { Menu, Moon, Sparkles, Sun, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { headerLinks } from '@/landing/data/navigation'
import { cn } from '@/lib/utils/cn'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

export function Header() {
  const { pathname } = useLocation()
  const token = useAuthStore((s) => s.token)
  const productName = useBrandingStore((s) => s.branding.product_name)
  const logoUrl = useBrandingStore((s) => s.branding.logo_url)
  const mediaRevision = useBrandingStore((s) => s.mediaRevision)
  const themePref = useThemeStore((s) => s.preference)
  const setTheme = useThemeStore((s) => s.setPreference)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  function cycleTheme() {
    const order: Array<'light' | 'dark'> = ['light', 'dark']
    const idx = order.indexOf(themePref === 'system' ? 'light' : themePref)
    setTheme(order[(idx + 1) % order.length])
  }

  const isDark = themePref === 'dark'

  return (
    <header
      className={cn(
        'sticky top-0 z-40 border-b border-surface-border transition-all duration-200',
        scrolled
          ? 'bg-white/90 backdrop-blur-md dark:bg-zinc-900/90'
          : 'bg-white dark:bg-zinc-900',
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          {logoUrl ? (
            <img
              src={`${resolveMediaUrl(logoUrl)}?v=${mediaRevision}`}
              alt={productName}
              className="h-8 w-8 rounded-lg object-contain"
            />
          ) : (
            <Sparkles className="h-5 w-5 text-amber-600" />
          )}
          <span className="font-display text-lg font-semibold text-zinc-900 dark:text-white">
            {productName}
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {headerLinks.map((link) => {
            const isActive = pathname === link.href
            return (
              <Link
                key={link.label}
                to={link.href}
                className={cn(
                  'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'text-amber-700 dark:text-amber-300'
                    : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white',
                )}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={cycleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
            title={`Theme: ${themePref}`}
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {token ? (
            <Link
              to="/dashboard"
              className="hidden rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 sm:inline-block"
            >
              Dashboard
            </Link>
          ) : (
            <Link
              to="/login"
              className="hidden rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 sm:inline-block"
            >
              Sign In
            </Link>
          )}

          <button
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 lg:hidden"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-surface-border bg-white px-4 pb-4 pt-2 dark:bg-zinc-900 lg:hidden">
          <nav className="flex flex-col gap-1">
            {headerLinks.map((link) => {
              const isActive = pathname === link.href
              return (
                <Link
                  key={link.label}
                  to={link.href}
                  className={cn(
                    'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'text-amber-700 dark:text-amber-300'
                      : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white',
                  )}
                >
                  {link.label}
                </Link>
              )
            })}
            {!token && (
              <Link
                to="/login"
                className="mt-2 rounded-lg bg-amber-600 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-amber-700"
              >
                Sign In
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  )
}
