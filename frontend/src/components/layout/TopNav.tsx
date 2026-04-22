import { Menu } from 'lucide-react'
import type { ReactNode } from 'react'

import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { cn } from '@/lib/utils/cn'
import { useSidebarStore } from '@/store/sidebarStore'

type TopNavProps = {
  title: string
  subtitle?: string
  /** Extra controls before the theme toggle (e.g. account / sign out). */
  headerActions?: ReactNode
}

export function TopNav({ title, subtitle, headerActions }: TopNavProps) {
  const toggleMobile = useSidebarStore((s) => s.toggleMobile)

  return (
    <header className="glass-header sticky top-0 z-30 flex items-center gap-4 px-4 py-4 lg:px-8">
      <button
        type="button"
        className="flex h-10 w-10 items-center justify-center rounded-xl border border-surface-border bg-surface-raised/90 text-ink-muted shadow-sm transition hover:border-amber-500/25 hover:text-ink dark:hover:border-emerald-500/20 dark:hover:text-zinc-100 lg:hidden"
        onClick={toggleMobile}
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>
      <div className="min-w-0 flex-1">
        <h1 className={cn('type-page-title')}>{title}</h1>
        {subtitle ? (
          <p className="mt-2 max-w-3xl text-base font-normal leading-relaxed text-ink-muted">{subtitle}</p>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {headerActions}
        <ThemeToggle className="shrink-0" />
      </div>
    </header>
  )
}
