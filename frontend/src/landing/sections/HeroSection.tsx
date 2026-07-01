import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-surface-border">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-amber-500/10 via-transparent to-emerald-500/10" />
      <div className="relative mx-auto max-w-6xl px-4 py-20 text-center sm:py-28 lg:py-36">
        <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-50 px-4 py-1.5 text-xs font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
          <Sparkles className="h-3 w-3" />
          Trusted by 5,000+ sales professionals
        </div>
        <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          AI-Powered Lead{' '}
          <span className="bg-gradient-to-r from-amber-600 to-emerald-600 bg-clip-text text-transparent">
            Intelligence
          </span>
        </h1>
        <p className="mx-auto mt-3 font-display text-xl font-semibold text-amber-600 dark:text-amber-400">
          Guide every lead to conversion.
        </p>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-600 dark:text-zinc-400">
          Discover, score, and engage your ideal prospects with intelligent automation.
          Stop guessing who to call. Start closing more deals.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-amber-600/20 hover:bg-amber-700 transition-all"
          >
            Get Started <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            to="/about"
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border px-6 py-3 text-base font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-all"
          >
            Learn More
          </Link>
        </div>
        <div className="mt-12 grid grid-cols-2 gap-6 border-t border-surface-border pt-10 sm:grid-cols-4">
          {[
            { value: '5,000+', label: 'Active users' },
            { value: '1M+', label: 'Leads scored' },
            { value: '97%', label: 'Uptime' },
            { value: '4.8', label: 'Customer rating' },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="font-display text-3xl font-bold text-zinc-900 dark:text-white">{stat.value}</p>
              <p className="mt-1 text-sm text-zinc-500">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
