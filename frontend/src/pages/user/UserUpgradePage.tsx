import { Check, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { publicGetPlans, type PublicPlan } from '@/lib/api/publicPlans'
import { cn } from '@/lib/utils/cn'

export function UserUpgradePage() {
  const [plans, setPlans] = useState<PublicPlan[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let c = false
    ;(async () => {
      const remote = await publicGetPlans()
      if (!c) { setPlans(remote); setLoading(false) }
    })()
    return () => { c = true }
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
      </div>
    )
  }

  if (plans.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Upgrade Plan</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">No plans are available at the moment.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Upgrade Your Plan</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Choose a plan that fits your needs. Upgrade anytime.</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={cn(
              'relative flex flex-col rounded-2xl border p-6 transition-all',
              plan.highlighted
                ? 'border-amber-500/30 bg-amber-50/50 shadow-lg shadow-amber-500/5 dark:bg-amber-950/20 dark:shadow-amber-500/10'
                : 'border-surface-border bg-white dark:bg-zinc-900',
            )}
          >
            {plan.highlighted && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-amber-600 px-4 py-1 text-xs font-semibold text-white">
                Popular
              </span>
            )}
            <h3 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">{plan.name}</h3>
            <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2">{plan.description}</p>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="font-display text-4xl font-bold text-zinc-900 dark:text-white">${plan.monthly_price}</span>
              <span className="text-sm text-zinc-500">/month</span>
            </div>
            <ul className="mt-6 flex-1 space-y-3">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                  {f}
                </li>
              ))}
            </ul>
            {plan.is_free ? (
              <Link
                to="/dashboard"
                className="mt-6 flex w-full items-center justify-center rounded-lg border border-surface-border px-4 py-2.5 text-sm font-semibold text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
              >
                Current Plan
              </Link>
            ) : (
              <Link
                to={`/user/checkout/${plan.id}`}
                className={cn(
                  'mt-6 flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-all',
                  plan.highlighted
                    ? 'bg-amber-600 text-white hover:bg-amber-700'
                    : 'border border-surface-border text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800',
                )}
              >
                Subscribe - ${plan.monthly_price}/mo
              </Link>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
