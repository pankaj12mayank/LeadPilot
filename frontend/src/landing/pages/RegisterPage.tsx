import { Link, Navigate } from 'react-router-dom'

import { useAuthStore } from '@/store/authStore'
import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function RegisterPage() {
  const token = useAuthStore((s) => s.token)
  const productName = useBrandingStore((s) => s.branding.product_name)

  if (token) return <Navigate to="/dashboard" replace />

  return (
    <>
      <SeoHead
        title={`Create Account - ${productName || APP_NAME}`}
        description={`Create your ${productName} workspace for prospecting, outreach, and pipeline management.`}
        keywords={['register', 'sign up', 'create account', 'workspace']}
      />
      <div className="flex min-h-[60vh] items-center justify-center px-4 py-20">
        <div className="w-full max-w-sm text-center">
          <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Start your 14-day free trial. No credit card needed.
          </p>
          <div className="mt-8 space-y-3">
            <Link
              to="/login"
              className="block rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-700"
            >
              Get Started Free
            </Link>
          </div>
          <p className="mt-6 text-xs text-zinc-500">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-amber-700 hover:underline dark:text-amber-300">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </>
  )
}
