import { Link } from 'react-router-dom'

export function UpgradeBanner({
  used,
  limit,
}: {
  used: number
  limit: number
}) {
  const pct = limit > 0 ? Math.min(Math.round((used / limit) * 100), 100) : 0
  if (pct < 100) return null

  return (
    <div className="mb-6 rounded-xl border border-amber-500/30 bg-amber-50 p-4 dark:border-amber-500/20 dark:bg-amber-950/20">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-amber-900 dark:text-amber-200">Lead limit reached</h3>
          <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
            You have used all {limit} leads in your current billing period. Upgrade to a paid plan to continue adding leads.
          </p>
        </div>
        <Link
          to="/user/upgrade"
          className="shrink-0 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
        >
          Upgrade Now
        </Link>
      </div>
    </div>
  )
}
