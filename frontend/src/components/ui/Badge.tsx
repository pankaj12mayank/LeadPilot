import { leadStatusLabel } from '@/lib/copy/appCopy'
import { cn } from '@/lib/utils/cn'

/** Lead tier + platform chip */
export type TierVariant = 'hot' | 'warm' | 'cold' | 'muted' | 'default' | 'accent' | 'platform'

const tierVariants: Record<string, string> = {
  default: 'border-surface-border bg-field/80 text-ink-muted',
  hot: 'border-red-500/35 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-950/45 dark:text-red-200',
  warm: 'border-amber-500/35 bg-amber-50 text-amber-900 dark:border-amber-500/25 dark:bg-amber-950/40 dark:text-amber-200',
  cold: 'border-slate-400/35 bg-slate-100 text-slate-800 dark:border-slate-600 dark:bg-slate-900/55 dark:text-slate-300',
  muted: 'border-surface-border bg-zinc-100 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-500',
  accent: 'border-amber-500/40 bg-amber-500/10 text-amber-800 dark:border-amber-400/35 dark:bg-amber-400/10 dark:text-amber-200',
  platform:
    'border-amber-600/25 bg-stone-100/90 font-mono text-xs uppercase text-stone-700 ring-1 ring-amber-500/15 dark:border-amber-500/20 dark:bg-zinc-900/80 dark:text-amber-100/90 dark:ring-amber-400/10',
}

/** CRM status badge colors (aligned with LinkedIn-style pipeline pills) */
const statusStyles: Record<string, string> = {
  new: 'border-rose-200/80 bg-rose-100 text-rose-900 dark:border-rose-500/35 dark:bg-rose-950/50 dark:text-rose-100',
  request_sent: 'border-violet-300/90 bg-violet-700 text-white dark:border-violet-500/50 dark:bg-violet-800 dark:text-white',
  message_sent: 'border-sky-400/80 bg-sky-600 text-white dark:border-sky-500/50 dark:bg-sky-700 dark:text-white',
  replied_got: 'border-amber-700/50 bg-amber-800 text-amber-50 dark:border-amber-600 dark:bg-amber-900 dark:text-amber-100',
  on_discussion: 'border-rose-200/80 bg-rose-100 text-rose-900 dark:border-rose-500/35 dark:bg-rose-950/50 dark:text-rose-100',
  interested: 'border-sky-200 bg-sky-100 text-sky-900 dark:border-sky-500/30 dark:bg-sky-950/40 dark:text-sky-100',
  deal: 'border-slate-500/60 bg-slate-600 text-white dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100',
  close: 'border-emerald-600/50 bg-emerald-700 text-white dark:border-emerald-500/50 dark:bg-emerald-800 dark:text-white',
  not_interested: 'border-red-600/50 bg-red-800 text-white dark:border-red-500/50 dark:bg-red-900 dark:text-white',
  // legacy
  contacted: 'border-sky-400/80 bg-sky-600 text-white dark:border-sky-500/50 dark:bg-sky-700 dark:text-white',
  replied: 'border-amber-700/50 bg-amber-800 text-amber-50 dark:border-amber-600 dark:bg-amber-900 dark:text-amber-100',
  follow_up_sent: 'border-sky-400/80 bg-sky-600 text-white dark:border-sky-500/50 dark:bg-sky-700 dark:text-white',
  meeting_scheduled: 'border-rose-200/80 bg-rose-100 text-rose-900 dark:border-rose-500/35 dark:bg-rose-950/50 dark:text-rose-100',
  deal_discussion: 'border-slate-500/60 bg-slate-600 text-white dark:border-slate-500 dark:bg-slate-800 dark:text-slate-100',
  closed: 'border-emerald-600/50 bg-emerald-700 text-white dark:border-emerald-500/50 dark:bg-emerald-800 dark:text-white',
  rejected: 'border-red-600/50 bg-red-800 text-white dark:border-red-500/50 dark:bg-red-900 dark:text-white',
  ready: 'border-sky-400/80 bg-sky-600 text-white dark:border-sky-500/50 dark:bg-sky-700 dark:text-white',
  converted: 'border-emerald-600/50 bg-emerald-700 text-white dark:border-emerald-500/50 dark:bg-emerald-800 dark:text-white',
}

export function statusBadgeClass(status: string): string {
  const k = (status || 'new').toLowerCase().replace(/\s+/g, '_')
  return statusStyles[k] ?? statusStyles.new
}

export function Badge({
  children,
  variant = 'default',
  className,
}: {
  children: React.ReactNode
  variant?: TierVariant
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium tracking-wide transition-colors duration-200',
        tierVariants[variant] ?? tierVariants.default,
        className,
      )}
    >
      {children}
    </span>
  )
}

export function StatusBadge({ status, title: titleProp }: { status: string; title?: string }) {
  const label = status ? leadStatusLabel(status) : '—'
  return (
    <span
      className={cn(
        'inline-flex max-w-full rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide',
        statusBadgeClass(status),
      )}
      title={titleProp ?? label}
    >
      {label}
    </span>
  )
}
