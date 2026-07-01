import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function TermsPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Terms of Service - ${productName || APP_NAME}`}
        description={`Terms of service for ${productName}. Understand your rights and responsibilities when using our platform.`}
        keywords={['terms of service', 'terms', 'legal', 'conditions']}
      />
      <div className="mx-auto max-w-3xl px-4 py-16 sm:py-20">
        <h1 className="font-display text-4xl font-bold tracking-tight text-zinc-900 dark:text-white">
          Terms of Service
        </h1>
        <p className="mt-2 text-sm text-zinc-500">Last updated: January 2026</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">1. Acceptance of Terms</h2>
            <p className="mt-2">
              By accessing or using {productName}, you agree to be bound by these Terms of Service. If you do not agree,
              please do not use the platform.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">2. Description of Service</h2>
            <p className="mt-2">
              {productName} provides lead generation, lead scoring, outreach tracking, and sales analytics tools to businesses
              and professionals. We reserve the right to modify or discontinue features at any time.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">3. User Responsibilities</h2>
            <p className="mt-2">
              You are responsible for maintaining the confidentiality of your account credentials and for all activity
              that occurs under your account. You agree not to use the platform for any unlawful purpose.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">4. Data and Privacy</h2>
            <p className="mt-2">
              Your use of the platform is also governed by our Privacy Policy. We take data protection seriously and
              implement appropriate security measures to protect your information.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">5. Limitation of Liability</h2>
            <p className="mt-2">
              {productName} is provided as is without any warranty. We are not liable for any damages arising from your
              use of the platform, to the maximum extent permitted by law.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">6. Contact</h2>
            <p className="mt-2">
              If you have any questions about these terms, please contact us at hello@leadpilot.io.
            </p>
          </section>
        </div>
      </div>
    </>
  )
}
