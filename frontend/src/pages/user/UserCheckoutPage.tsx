import { ArrowLeft, Check, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { useAuthStore } from '@/store/authStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { publicGetPlans, type PublicPlan } from '@/lib/api/publicPlans'
import { createSubscription } from '@/lib/api/subscriptions'
import { getApiErrorMessage } from '@/lib/api/client'

export function UserCheckoutPage() {
  const { planId } = useParams<{ planId: string }>()
  const { user } = useAuthStore()
  const productName = useBrandingStore((s) => s.branding.product_name)
  const [plan, setPlan] = useState<PublicPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [gateway, setGateway] = useState<'stripe' | 'razorpay'>('stripe')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let c = false
    ;(async () => {
      const plans = await publicGetPlans()
      const found = plans.find((p) => p.id === planId)
      if (!c) { setPlan(found || null); setLoading(false) }
    })()
    return () => { c = true }
  }, [planId])

  if (!loading && !plan) return <Navigate to="/user/upgrade" replace />

  async function handleSubscribe() {
    if (!plan) return
    setBusy(true)
    setError('')
    try {
      const result = await createSubscription(plan.id, gateway)
      if (result.is_free) {
        window.location.href = '/payment/success?subscription_id=' + result.subscription_id
        return
      }
      if (gateway === 'stripe' && result.url) {
        window.location.href = result.url
      } else if (gateway === 'razorpay') {
        const razorpayKey = result.publishable_key
        const options = {
          key: razorpayKey,
          subscription_id: result.order_id,
          name: productName || APP_NAME,
          description: plan.name,
          prefill: { email: user?.email || '', name: user?.name || '' },
          handler: function (response: any) {
            window.location.href = `/payment/success?subscription_id=${result.subscription_id}&payment_id=${response.razorpay_payment_id}&order_id=${response.razorpay_order_id}&signature=${response.razorpay_signature}`
          },
          modal: {
            ondismiss: function () { setBusy(false) },
          },
        }
        const rzp = new (window as any).Razorpay(options)
        rzp.open()
      }
    } catch (e) {
      setError(getApiErrorMessage(e, 'Payment could not be initiated'))
      setBusy(false)
    }
  }

  if (loading || !plan) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber-600" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link
        to="/user/upgrade"
        className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-amber-700 dark:hover:text-amber-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Plans
      </Link>

      <div className="rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900">
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Complete your subscription</h1>

        <div className="mt-6 flex items-center justify-between rounded-xl border border-surface-border bg-zinc-50 p-4 dark:bg-zinc-800">
          <div>
            <p className="font-semibold text-zinc-900 dark:text-white">{plan.name}</p>
            <p className="text-sm text-zinc-500">{plan.description}</p>
          </div>
          <div className="text-right">
            <p className="font-display text-2xl font-bold text-zinc-900 dark:text-white">${plan.monthly_price}</p>
            <p className="text-xs text-zinc-500">/month</p>
          </div>
        </div>

        {plan.features.length > 0 && (
          <ul className="mt-4 space-y-2">
            {plan.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                <Check className="h-4 w-4 text-emerald-600" />
                {f}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Payment Method</label>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setGateway('stripe')}
              className={`rounded-xl border-2 p-4 text-center text-sm font-medium transition-all ${
                gateway === 'stripe'
                  ? 'border-amber-500 bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300'
                  : 'border-surface-border text-zinc-600 hover:border-zinc-300 dark:text-zinc-400'
              }`}
            >
              Pay with Card
              <span className="block text-xs text-zinc-400 mt-1">Stripe</span>
            </button>
            <button
              type="button"
              onClick={() => setGateway('razorpay')}
              className={`rounded-xl border-2 p-4 text-center text-sm font-medium transition-all ${
                gateway === 'razorpay'
                  ? 'border-amber-500 bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-300'
                  : 'border-surface-border text-zinc-600 hover:border-zinc-300 dark:text-zinc-400'
              }`}
            >
              Pay with UPI / Card
              <span className="block text-xs text-zinc-400 mt-1">Razorpay</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">
            {error}
          </div>
        )}

        <button
          type="button"
          disabled={busy}
          onClick={() => void handleSubscribe()}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-base font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : null}
          {busy ? 'Processing...' : `Pay $${plan.monthly_price}/month`}
        </button>

        <p className="mt-4 text-center text-xs text-zinc-400">
          Your payment is processed securely. No payment info is stored on our servers.
        </p>
      </div>
    </div>
  )
}
