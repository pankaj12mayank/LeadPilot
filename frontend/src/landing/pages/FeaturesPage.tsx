import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { features } from '@/landing/data/features'

export function FeaturesPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Features - ${productName || APP_NAME}`}
        description={`Explore ${productName} features: lead database, smart lead scoring, sales analytics, multi-channel outreach, compliance tools, and team collaboration.`}
        keywords={['features', 'lead scoring', 'sales analytics', 'outreach', 'CRM features']}
      />

      <section className="border-b border-surface-border bg-gradient-to-br from-amber-500/5 to-emerald-500/5">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
          <h1 className="font-display text-4xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-5xl">
            Everything you need to close more deals
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-600 dark:text-zinc-400">
            No feature bloat. Just the tools that actually move the needle on your sales numbers.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="grid gap-10">
          {features.map((f, i) => {
            const Icon = f.icon
            return (
              <Link
                to={f.link}
                key={f.title}
                className={`flex flex-col gap-6 rounded-2xl p-4 transition-all hover:bg-zinc-50 dark:hover:bg-zinc-800/50 ${i % 2 === 0 ? 'lg:flex-row' : 'lg:flex-row-reverse'} items-center`}
              >
                <div className="flex-1">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
                    <Icon className="h-6 w-6" />
                  </div>
                  <h2 className="mt-4 font-display text-2xl font-bold text-zinc-900 dark:text-white">{f.title}</h2>
                  <p className="mt-3 leading-relaxed text-zinc-600 dark:text-zinc-400">{f.description}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-amber-700 dark:text-amber-300 group-hover:gap-2 transition-all">
                    View More <ArrowRight className="h-3 w-3" />
                  </span>
                </div>
                <div className="flex-1 flex items-center justify-center">
                  <div className="flex h-56 w-56 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500/5 to-emerald-500/5 border border-surface-border sm:h-64 sm:w-64">
                    <Icon className="h-16 w-16 text-amber-600/30" />
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </section>

      <section className="border-t border-surface-border bg-zinc-900 dark:bg-black">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
          <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">
            Ready to try it out?
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-zinc-400">
            Start your free trial. No credit card required. No contracts.
          </p>
          <Link
            to="/login"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-base font-semibold text-white hover:bg-amber-700"
          >
            Get Started <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </>
  )
}
