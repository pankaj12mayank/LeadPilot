import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { userGetSubscription, userGetUsage, type SubscriptionInfo } from '@/lib/api/subscriptions'
import { cn } from '@/lib/utils/cn'

const planColors: Record<string, string> = {
  starter: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
  growth: 'bg-blue-500/10 text-blue-700 dark:bg-blue-500/20 dark:text-blue-300',
  pro: 'bg-amber-500/10 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
  enterprise: 'bg-purple-500/10 text-purple-700 dark:bg-purple-500/20 dark:text-purple-300',
}

export function PlanSection() {
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null)
  const [usage, setUsage] = useState<{ leads_consumed: number; lead_limit: number } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [subRes, usageRes] = await Promise.all([
          userGetSubscription(),
          userGetUsage(),
        ])
        if (subRes.has_subscription && subRes.subscription) {
          setSubscription(subRes.subscription)
        }
        setUsage(usageRes)
      } catch {
        /* ignore */
      } finally {
        setLoading(false)
      }
    }
    void load()
  }, [])

  if (loading) {
    return (
      <div className="border-t border-surface-border p-3">
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-16 rounded bg-zinc-200 dark:bg-zinc-700" />
          <div className="h-2 w-24 rounded bg-zinc-200 dark:bg-zinc-700" />
        </div>
      </div>
    )
  }

  const planId = subscription?.plan_id || 'starter'
  const planName = subscription?.plan_name || planId.charAt(0).toUpperCase() + planId.slice(1)
  const leadsConsumed = usage?.leads_consumed ?? 0
  const leadLimit = usage?.lead_limit ?? 0
  const usagePercent = leadLimit > 0 ? Math.min(100, (leadsConsumed / leadLimit) * 100) : 0

  return (
    <div className="border-t border-surface-border p-3">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
            Plan
          </span>
          <Link
            to="/user/upgrade"
            className="text-[11px] font-medium text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
          >
            Upgrade
          </Link>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize', planColors[planId] || planColors.starter)}>
            {planName}
          </span>
        </div>
        {leadLimit > 0 && (
          <div className="space-y-1">
            <div className="flex justify-between text-[10px] text-zinc-500">
              <span>Leads used</span>
              <span>{leadsConsumed} / {leadLimit}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  usagePercent >= 90 ? 'bg-red-500' : usagePercent >= 70 ? 'bg-amber-500' : 'bg-emerald-500',
                )}
                style={{ width: `${usagePercent}%` }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}