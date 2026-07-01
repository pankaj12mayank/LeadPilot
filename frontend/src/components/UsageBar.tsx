export function UsageBar({
  used,
  limit,
  label,
}: {
  used: number
  limit: number
  label?: string
}) {
  const pct = limit > 0 ? Math.min(Math.round((used / limit) * 100), 100) : 0
  const color =
    pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-emerald-500'

  return (
    <div>
      {label && (
        <p className="mb-1 text-xs font-medium text-zinc-500 dark:text-zinc-400">{label}</p>
      )}
      <div className="flex items-center gap-3">
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
          <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        </div>
        <span className="shrink-0 text-xs font-semibold text-zinc-600 dark:text-zinc-300">
          {used}/{limit}
        </span>
      </div>
    </div>
  )
}
