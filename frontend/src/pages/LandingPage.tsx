import { ArrowRight, Database, Gauge, ShieldCheck, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect } from 'react'

import { APP_NAME, DEFAULT_META_DESCRIPTION } from '@/lib/copy/appCopy'

export function LandingPage() {
  useEffect(() => {
    document.title = `${APP_NAME} | AI Lead Growth System`
    const el = document.querySelector('meta[name="description"]')
    if (el) {
      el.setAttribute(
        'content',
        `${DEFAULT_META_DESCRIPTION} Discover companies, qualify with AI, score by admin rules, and run queue-based outreach safely.`,
      )
    }
  }, [])

  return (
    <div className="min-h-screen bg-surface text-ink">
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 sm:px-6 lg:px-8">
        <header className="rounded-3xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark sm:p-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-800 dark:text-amber-200">
            <Sparkles className="h-3.5 w-3.5" />
            Human-first lead operations
          </div>
          <h1 className="mt-4 max-w-3xl font-display text-3xl font-bold tracking-tight text-ink sm:text-4xl">
            Find better-fit companies, qualify with AI, and prioritize outreach in one fast workflow.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-ink-muted sm:text-base">
            {APP_NAME} gives your team a clean, responsive workspace for company discovery, lead qualification, scoring,
            and queue-based execution. Built to stay stable even when AI or sources fail.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-500/15 dark:text-amber-200"
            >
              Open workspace
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/about"
              className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-4 py-2 text-sm font-medium text-ink-muted transition hover:bg-field/60 hover:text-ink"
            >
              Product overview
            </Link>
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <article className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark">
            <Database className="h-5 w-5 text-emerald-600 dark:text-emerald-300" />
            <h2 className="mt-3 text-sm font-semibold text-ink">Explorer Company DB</h2>
            <p className="mt-1 text-xs text-ink-muted">Search, filter by source/date, and keep records deduped and inspectable.</p>
          </article>
          <article className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark">
            <Sparkles className="h-5 w-5 text-amber-700 dark:text-amber-300" />
            <h2 className="mt-3 text-sm font-semibold text-ink">AI Qualification</h2>
            <p className="mt-1 text-xs text-ink-muted">Get summaries, problems, opportunity insight, and AI score with fallback safety.</p>
          </article>
          <article className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark">
            <Gauge className="h-5 w-5 text-indigo-600 dark:text-indigo-300" />
            <h2 className="mt-3 text-sm font-semibold text-ink">Admin-driven scoring</h2>
            <p className="mt-1 text-xs text-ink-muted">Role, signals, data completeness, and AI score controlled from admin panel.</p>
          </article>
          <article className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark">
            <ShieldCheck className="h-5 w-5 text-sky-600 dark:text-sky-300" />
            <h2 className="mt-3 text-sm font-semibold text-ink">Queue + scheduler stability</h2>
            <p className="mt-1 text-xs text-ink-muted">Priority queue, retries, worker limits, and weekly cleanup without overload.</p>
          </article>
        </section>
      </main>
    </div>
  )
}
