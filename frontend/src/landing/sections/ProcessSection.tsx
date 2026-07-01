import { services } from '@/landing/data/services'

export function ProcessSection() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
          Our process
        </p>
        <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
          How we work
        </h2>
      </div>
      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {services.map((s) => {
          const Icon = s.icon
          return (
            <div
              key={s.step}
              className="group relative rounded-2xl border border-surface-border bg-white p-6 dark:bg-zinc-900"
            >
              <span className="font-display text-5xl font-bold text-zinc-200 dark:text-zinc-800 transition-colors group-hover:text-amber-600/20">
                {s.step}
              </span>
              <div className="mt-4 flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-display text-lg font-semibold text-zinc-900 dark:text-white">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                {s.description}
              </p>
            </div>
          )
        })}
      </div>
    </section>
  )
}
