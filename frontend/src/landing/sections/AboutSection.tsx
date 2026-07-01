import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'

export function AboutSection() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
              About us
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
              What we do and why it matters
            </h2>
            <p className="mt-4 leading-relaxed text-zinc-600 dark:text-zinc-400">
              {productName} was built by sales people who got tired of expensive platforms
              that do half the job. We wanted a tool that actually helps you find the right
              people, understand if they are worth pursuing, and reach out without jumping
              between five different apps.
            </p>
            <p className="mt-3 leading-relaxed text-zinc-600 dark:text-zinc-400">
              Today, teams from solo founders to fifty-person agencies use {productName} to
              keep their pipeline full and their outreach organised. No annual contracts,
              no hidden fees, no training required.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/about"
                className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-700 transition-all"
              >
                More about us <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/contact"
                className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-5 py-2.5 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-all"
              >
                Contact us
              </Link>
            </div>
          </div>
          <div className="relative flex items-center justify-center">
            <div className="flex h-72 w-72 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500/10 to-emerald-500/10 sm:h-80 sm:w-80">
              <Sparkles className="h-16 w-16 text-amber-600/40" />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
