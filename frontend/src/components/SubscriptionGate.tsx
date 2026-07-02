import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { userGetSubscription } from '@/lib/api/subscriptions'

export function useSubscriptionStatus() {
  const [status, setStatus] = useState<'loading' | 'active' | 'expired' | 'none'>('loading')
  const [subscription, setSubscription] = useState<any>(null)

  useEffect(() => {
    async function check() {
      try {
        const res = await userGetSubscription()
        if (res.has_subscription && res.subscription) {
          const sub = res.subscription
          setSubscription(sub)
          const now = new Date()
          const endDate = sub.period_end ? new Date(sub.period_end) : null
          if (endDate && endDate < now) {
            setStatus('expired')
          } else {
            setStatus('active')
          }
        } else {
          setStatus('none')
        }
      } catch {
        setStatus('none')
      }
    }
    void check()
  }, [])

  return { status, subscription }
}

export function ExpiredBanner() {
  const { status } = useSubscriptionStatus()

  if (status !== 'expired') return null

  return (
    <div className="relative overflow-hidden rounded-2xl border border-red-500/30 bg-red-50 p-4 dark:bg-red-950/30">
      <div className="absolute right-0 top-0 h-16 w-16 translate-x-4 -translate-y-4 rounded-full bg-red-500/10" />
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <h3 className="font-semibold text-red-800 dark:text-red-200">Subscription Expired</h3>
          <p className="mt-1 text-sm text-red-700/90 dark:text-red-300/90">
            Your subscription has expired. Renew now to regain access to all features and leads.
          </p>
        </div>
        <Link
          to="/user/upgrade"
          className="shrink-0 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
        >
          Renew Now
        </Link>
      </div>
    </div>
  )
}