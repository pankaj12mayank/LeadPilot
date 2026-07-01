import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function PrivacyPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Privacy Policy - ${productName || APP_NAME}`}
        description={`Privacy policy for ${productName}. Learn how we collect, use, and protect your data.`}
        keywords={['privacy policy', 'privacy', 'data protection', 'GDPR']}
      />
      <div className="mx-auto max-w-3xl px-4 py-16 sm:py-20">
        <h1 className="font-display text-4xl font-bold tracking-tight text-zinc-900 dark:text-white">
          Privacy Policy
        </h1>
        <p className="mt-2 text-sm text-zinc-500">Last updated: January 2026</p>

        <div className="mt-10 space-y-8 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">1. Information We Collect</h2>
            <p className="mt-2">
              We collect information you provide when creating an account, such as your name and email address.
              We also collect data about how you use the platform, including pages visited and features used.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">2. How We Use Your Information</h2>
            <p className="mt-2">
              We use your information to provide and improve the service, communicate with you about your account,
              send product updates, and ensure platform security. We do not sell your personal data.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">3. Data Security</h2>
            <p className="mt-2">
              We implement industry-standard security measures including encryption at rest and in transit,
              regular security audits, and access controls to protect your data.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">4. Data Retention</h2>
            <p className="mt-2">
              We retain your data for as long as your account is active. You can request deletion of your data
              at any time by contacting us.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">5. Your Rights</h2>
            <p className="mt-2">
              Depending on your location, you may have rights regarding your personal data, including access,
              correction, deletion, and portability. Contact us to exercise these rights.
            </p>
          </section>
          <section>
            <h2 className="font-display text-xl font-semibold text-zinc-900 dark:text-white">6. Contact</h2>
            <p className="mt-2">
              For privacy-related inquiries, contact us at hello@leadpilot.io.
            </p>
          </section>
        </div>
      </div>
    </>
  )
}
