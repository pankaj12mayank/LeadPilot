import { Moon, Sun } from 'lucide-react'

import { cn } from '@/lib/utils/cn'
import { useThemeStore } from '@/store/themeStore'

export function ThemeToggle({ className }: { className?: string }) {
  const preference = useThemeStore((s) => s.preference)
  const setPreference = useThemeStore((s) => s.setPreference)

  return (
    <div
      className={cn(
        'inline-flex rounded-xl border border-surface-border bg-surface-raised/80 p-1 shadow-sm backdrop-blur-sm dark:bg-zinc-900/60',
        className,
      )}
      role="group"
      aria-label="Theme"
    >
      <button
        type="button"
        title="Light"
        aria-pressed={preference === 'light'}
        aria-label="Light theme"
        onClick={() => setPreference('light')}
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200',
          preference === 'light'
            ? 'bg-gradient-to-br from-amber-500/25 to-amber-600/15 text-amber-700 shadow-sm ring-1 ring-amber-500/30 dark:from-amber-400/20 dark:to-amber-600/10 dark:text-amber-300 dark:ring-amber-400/25'
            : 'text-ink-muted hover:bg-white/60 hover:text-ink dark:hover:bg-white/5 dark:hover:text-zinc-200',
        )}
      >
        <Sun className="h-4 w-4" strokeWidth={1.75} />
      </button>
      <button
        type="button"
        title="Dark"
        aria-pressed={preference === 'dark'}
        aria-label="Dark theme"
        onClick={() => setPreference('dark')}
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200',
          preference === 'dark'
            ? 'bg-gradient-to-br from-amber-500/25 to-amber-600/15 text-amber-700 shadow-sm ring-1 ring-amber-500/30 dark:from-amber-400/20 dark:to-amber-600/10 dark:text-amber-300 dark:ring-amber-400/25'
            : 'text-ink-muted hover:bg-white/60 hover:text-ink dark:hover:bg-white/5 dark:hover:text-zinc-200',
        )}
      >
        <Moon className="h-4 w-4" strokeWidth={1.75} />
      </button>
    </div>
  )
}
