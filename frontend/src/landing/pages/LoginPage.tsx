import { Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'

export function LoginPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)
  const logoUrl = useBrandingStore((s) => s.branding.logo_url)
  const mediaRevision = useBrandingStore((s) => s.mediaRevision)

  return (
    <>
      <SeoHead
        title={`Sign In - ${productName || APP_NAME}`}
        description={`Sign in to ${productName} to manage leads, outreach, and analytics from one workspace.`}
        keywords={['sign in', 'login', 'workspace']}
      />
      <div className="flex min-h-[60vh] items-center justify-center px-4 py-20">
        <div className="w-full max-w-sm text-center">
          <Link to="/" className="mx-auto flex w-fit items-center gap-2">
            {logoUrl ? (
              <img
                src={`${resolveMediaUrl(logoUrl)}?v=${mediaRevision}`}
                alt={productName}
                className="h-8 w-8 rounded-lg object-contain"
              />
            ) : (
              <Sparkles className="h-5 w-5 text-amber-600" />
            )}
            <span className="font-display text-lg font-semibold text-zinc-900 dark:text-white">
              {productName || APP_NAME}
            </span>
          </Link>
          <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
            Sign in or create your account to get started.
          </p>
          <div className="mt-8">
            <Link
              to="/login?from=landing"
              className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-700"
            >
              Sign In / Register
            </Link>
          </div>
          <p className="mt-6 text-xs text-zinc-500">
            By signing in, you agree to our{' '}
            <Link to="/terms" className="underline hover:text-amber-700 dark:hover:text-amber-300">Terms</Link>
            {' '}and{' '}
            <Link to="/privacy" className="underline hover:text-amber-700 dark:hover:text-amber-300">Privacy Policy</Link>.
          </p>
        </div>
      </div>
    </>
  )
}
