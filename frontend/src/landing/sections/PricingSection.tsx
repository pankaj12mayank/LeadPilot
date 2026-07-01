import { Check } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { publicGetPlans, type PublicPlan } from '@/lib/api/publicPlans'
import { cn } from '@/lib/utils/cn'

export function PricingSection({ compact }: { compact?: boolean }) {
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

  const displayPlans = plans
  if (compact && displayPlans.length > 3) displayPlans.length = 3

  if (loading) {
    return (
      <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20 text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-600 mx-auto" />
        </div>
      </section>
    )
  }

  if (displayPlans.length === 0) {
    return (
      <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">Pricing</p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            Plans coming soon
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-zinc-600 dark:text-zinc-400">
            We are setting up our pricing tiers. Check back shortly or contact us for early access.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            Pricing
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            Choose the right plan for your business
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-zinc-600 dark:text-zinc-400">
            No hidden fees, no surprise charges. Pick a plan and upgrade when you outgrow it.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-3">
          {displayPlans.map((plan) => (
            <div
              key={plan.id}
              className={cn(
                'relative rounded-2xl border p-6 transition-all',
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
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{plan.description}</p>
              <div className="mt-4 flex items-baseline gap-1">
                  <span className="font-display text-4xl font-bold text-zinc-900 dark:text-white">${plan.monthly_price}</span>
                <span className="text-sm text-zinc-500">/month</span>
              </div>
              <ul className="mt-6 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                to={plan.is_free ? '/login' : `/subscribe/${plan.id}`}
                className={cn(
                  'mt-6 flex w-full items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-all',
                  plan.highlighted
                    ? 'bg-amber-600 text-white hover:bg-amber-700'
                    : 'border border-surface-border text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800',
                )}
              >
                {plan.is_free ? 'Get Started Free' : `Subscribe - $${plan.monthly_price}/mo`}
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
