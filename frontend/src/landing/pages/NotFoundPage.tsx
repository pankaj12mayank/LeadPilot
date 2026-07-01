import { ArrowLeft, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function NotFoundPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`404 - ${productName || APP_NAME}`}
        description="Page not found. The page you are looking for does not exist or has been moved."
        keywords={['404', 'page not found', 'error']}
      />
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-20 text-center">
        <h1 className="font-display text-8xl font-bold text-zinc-200 dark:text-zinc-800">404</h1>
        <p className="mt-4 text-xl font-semibold text-zinc-900 dark:text-white">Page not found</p>
        <p className="mt-2 max-w-md text-sm text-zinc-600 dark:text-zinc-400">
          The page you are looking for does not exist or has been moved to a new address.
        </p>
        <div className="mt-8 flex gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-700"
          >
            <Home className="h-4 w-4" /> Back to Home
          </Link>
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-5 py-2.5 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            <ArrowLeft className="h-4 w-4" /> Go Back
          </button>
        </div>
      </div>
    </>
  )
}
