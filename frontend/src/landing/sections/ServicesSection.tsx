import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'

export function ServicesSection() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <section className="relative overflow-hidden border-t border-surface-border bg-zinc-900 dark:bg-black">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/5 to-emerald-500/5" />
      <div className="relative mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              What we do
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Need a solid platform you can count on? Look no further.
            </h2>
            <p className="mt-4 leading-relaxed text-zinc-400">
              We help you build a strong online presence for your business by providing
              the tools that actually generate leads, not just website traffic. {productName} is
              built for sales motion, not vanity metrics.
            </p>
            <div className="mt-6">
              <Link
                to="/features"
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-700 transition-all"
              >
                View More <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <div className="flex h-64 w-64 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-900/50 sm:h-72 sm:w-72">
              <Sparkles className="h-16 w-16 text-amber-600/30" />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
