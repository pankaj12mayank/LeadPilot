import { Quote } from 'lucide-react'

import { testimonials } from '@/landing/data/testimonials'

export function TestimonialsSection() {
  return (
    <section className="border-t border-surface-border bg-zinc-50 dark:bg-zinc-900/50">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            Testimonials
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            See why teams love it
          </h2>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-3">
          {testimonials.map((t) => (
            <div
              key={t.name}
              className="relative rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900"
            >
              <Quote className="h-6 w-6 text-amber-600/20" />
              <p className="mt-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="mt-4 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-500/20 text-xs font-semibold text-amber-800 dark:text-amber-200">
                  {t.name.split(' ').map((n) => n[0]).join('')}
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-900 dark:text-white">{t.name}</p>
                  <p className="text-xs text-zinc-500">{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
