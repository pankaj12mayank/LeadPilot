import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { features } from '@/landing/data/features'

export function FeaturesSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
          Features
        </p>
        <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
          Everything you need to fill your pipeline
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-zinc-600 dark:text-zinc-400">
          No fluff, no feature bloat. Just the tools that actually move the needle on your sales numbers.
        </p>
      </div>
      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => {
          const Icon = f.icon
          return (
            <Link
              key={f.title}
              to={f.link}
              className="group rounded-2xl border border-surface-border bg-white p-6 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 dark:bg-zinc-900"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-lg font-semibold text-zinc-900 dark:text-white">
                {f.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                {f.description}
              </p>
              <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-amber-700 dark:text-amber-300 group-hover:gap-2 transition-all">
                Read More <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
