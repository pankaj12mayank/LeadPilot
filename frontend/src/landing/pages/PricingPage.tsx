import { Check } from 'lucide-react'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { PricingSection } from '@/landing/sections/PricingSection'

const comparisons = [
  { feature: 'Lead database', starter: true, growth: true, pro: true },
  { feature: 'Lead scoring', starter: 'Basic', growth: 'Advanced', pro: 'Custom models' },
  { feature: 'Email outreach', starter: true, growth: true, pro: true },
  { feature: 'LinkedIn outreach', starter: false, growth: true, pro: true },
  { feature: 'Multi-channel sequences', starter: false, growth: false, pro: true },
  { feature: 'Team seats', starter: '1 seat', growth: '3 seats', pro: 'Unlimited' },
  { feature: 'API access', starter: false, growth: false, pro: true },
  { feature: 'Dedicated support', starter: 'Standard', growth: 'Priority', pro: 'Account manager' },
]

export function PricingPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Pricing - ${productName || APP_NAME}`}
        description={`Compare ${productName} pricing plans. Starter $29/mo, Growth $49/mo, Pro $69/mo. No hidden fees, no long-term contracts.`}
        keywords={['pricing', 'plans', 'starter', 'growth', 'pro', 'lead generation pricing']}
      />
      <PricingSection />

      {/* Comparison table */}
      <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
          <h2 className="text-center font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            Compare plans side by side
          </h2>
          <div className="mt-12 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="pb-4 text-left font-display text-base font-semibold text-zinc-900 dark:text-white">Feature</th>
                  <th className="pb-4 text-center font-display text-base font-semibold text-zinc-900 dark:text-white">Starter</th>
                  <th className="pb-4 text-center font-display text-base font-semibold text-amber-700 dark:text-amber-300">Growth</th>
                  <th className="pb-4 text-center font-display text-base font-semibold text-zinc-900 dark:text-white">Pro</th>
                </tr>
              </thead>
              <tbody>
                {comparisons.map((row) => (
                  <tr key={row.feature} className="border-b border-surface-border/50">
                    <td className="py-3 text-zinc-700 dark:text-zinc-300">{row.feature}</td>
                    {([row.starter, row.growth, row.pro] as const).map((val, i) => (
                      <td key={i} className="py-3 text-center">
                        {val === true ? (
                          <Check className="mx-auto h-4 w-4 text-emerald-600" />
                        ) : val === false ? (
                          <span className="text-zinc-300 dark:text-zinc-600">&mdash;</span>
                        ) : (
                          <span className="text-zinc-600 dark:text-zinc-400">{val}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <h2 className="text-center font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
          Pricing FAQ
        </h2>
        <div className="mx-auto mt-12 max-w-3xl space-y-4">
          {[
            { q: 'Can I upgrade or downgrade anytime?', a: 'Yes. You can change your plan at any point. Changes take effect immediately and we prorate the difference.' },
            { q: 'Is there a free trial?', a: 'Yes, all plans come with a 14-day free trial. No credit card required.' },
            { q: 'What happens when I exceed lead limits?', a: 'We will notify you before you hit the cap. You can upgrade your plan or purchase additional lead credits.' },
            { q: 'Do you offer annual discounts?', a: 'Yes, annual billing gives you two months free compared to monthly billing.' },
          ].map((faq) => (
            <details key={faq.q} className="group rounded-2xl border border-surface-border bg-white p-5 dark:bg-zinc-900">
              <summary className="flex cursor-pointer items-center justify-between font-display text-base font-semibold text-zinc-900 dark:text-white">
                {faq.q}
                <span className="text-zinc-400 group-open:rotate-180 transition-transform">&#x25BC;</span>
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">{faq.a}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  )
}
