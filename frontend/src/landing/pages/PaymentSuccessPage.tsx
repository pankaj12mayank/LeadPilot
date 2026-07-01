import { CheckCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { verifyRazorpayPayment } from '@/lib/api/subscriptions'

export function PaymentSuccessPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)
  const [searchParams] = useSearchParams()
  const [verified, setVerified] = useState(false)
  const subscriptionId = searchParams.get('subscription_id') || ''
  const paymentId = searchParams.get('payment_id') || ''
  const orderId = searchParams.get('order_id') || ''
  const signature = searchParams.get('signature') || ''

  useEffect(() => {
    if (paymentId && orderId && signature && subscriptionId) {
      verifyRazorpayPayment(paymentId, orderId, signature, subscriptionId)
        .then(() => setVerified(true))
        .catch(() => setVerified(true))
    } else {
      setVerified(true)
    }
  }, [paymentId, orderId, signature, subscriptionId])

  return (
    <>
      <SeoHead
        title={`Payment Successful - ${productName || APP_NAME}`}
        description="Your payment was successful. Welcome aboard!"
      />
      <section className="mx-auto max-w-lg px-4 py-20 text-center sm:py-28">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
          <CheckCircle className="h-10 w-10 text-emerald-600" />
        </div>
        <h1 className="mt-6 font-display text-3xl font-bold text-zinc-900 dark:text-white">
          Payment Successful!
        </h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">
          Thank you for subscribing. Your plan is now active and you have full access to all features.
          {!verified && ' Verifying payment...'}
        </p>
        <p className="mt-2 text-sm text-zinc-500">
          A confirmation email has been sent to your registered email address.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            to="/dashboard"
            className="rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-700"
          >
            Go to Dashboard
          </Link>
        </div>
      </section>
    </>
  )
}
