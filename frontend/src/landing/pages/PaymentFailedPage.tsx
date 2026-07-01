import { XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function PaymentFailedPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Payment Failed - ${productName || APP_NAME}`}
        description="Your payment did not go through. Please try again."
      />
      <section className="mx-auto max-w-lg px-4 py-20 text-center sm:py-28">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
          <XCircle className="h-10 w-10 text-red-600" />
        </div>
        <h1 className="mt-6 font-display text-3xl font-bold text-zinc-900 dark:text-white">
          Payment Failed
        </h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">
          Your payment could not be processed. This could be due to insufficient funds, a declined card, or a temporary issue.
        </p>
        <p className="mt-2 text-sm text-zinc-500">
          Your account has not been charged. Please try again or use a different payment method.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            to="/pricing"
            className="rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-700"
          >
            Try Again
          </Link>
          <Link
            to="/dashboard"
            className="rounded-lg border border-surface-border px-6 py-3 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            Go to Dashboard
          </Link>
        </div>
      </section>
    </>
  )
}
