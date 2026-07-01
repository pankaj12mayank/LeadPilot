import { ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'

export function AboutPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`About ${productName || APP_NAME}`}
        description={`Learn about ${productName}, the lead management and sales CRM platform built for sales teams, agencies, and growing businesses.`}
        keywords={['about', 'team', 'mission', 'lead generation company', 'sales CRM']}
      />

      {/* Hero */}
      <section className="border-b border-surface-border bg-gradient-to-br from-amber-500/5 to-emerald-500/5">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                About us
              </p>
              <h1 className="mt-2 font-display text-4xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-5xl">
                We built {productName} because we needed it ourselves
              </h1>
              <p className="mt-4 leading-relaxed text-zinc-600 dark:text-zinc-400">
                The idea came from years of using tools that were either too complicated for what
                we needed or too simple to be useful. We wanted a platform that handles the full
                cycle from finding leads to closing deals, without forcing you to learn a new
                system every quarter.
              </p>
              <p className="mt-3 leading-relaxed text-zinc-600 dark:text-zinc-400">
                Today, {productName} helps sales teams, recruiters, and agencies keep their pipelines
                organised and their outreach on track. We are a small team that moves fast and
                actually listens to customer feedback.
              </p>
            </div>
            <div className="flex items-center justify-center">
              <div className="flex h-64 w-64 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-500/10 to-emerald-500/10 sm:h-80 sm:w-80">
                <Sparkles className="h-20 w-20 text-amber-600/30" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section id="team" className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            Our team
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            The people behind the platform
          </h2>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { name: 'Alex Chen', role: 'Founder & CEO', initials: 'AC' },
            { name: 'Sarah Mitchell', role: 'Head of Product', initials: 'SM' },
            { name: 'James Rodriguez', role: 'Lead Engineer', initials: 'JR' },
            { name: 'Emily Watson', role: 'Customer Success', initials: 'EW' },
          ].map((person) => (
            <div key={person.name} className="rounded-2xl border border-surface-border bg-white p-6 text-center dark:bg-zinc-900">
              <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-amber-500/15 text-xl font-bold text-amber-800 dark:text-amber-200">
                {person.initials}
              </div>
              <h3 className="mt-4 font-display text-lg font-semibold text-zinc-900 dark:text-white">{person.name}</h3>
              <p className="text-sm text-zinc-500">{person.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-surface-border bg-zinc-900 dark:bg-black">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
          <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">
            Want to see {productName} in action?
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-zinc-400">
            Book a quick demo or jump straight in. No sales pitch, just a real conversation about
            whether we fit your workflow.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-base font-semibold text-white hover:bg-amber-700"
            >
              Get Started <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-700 px-6 py-3 text-base font-medium text-zinc-300 hover:bg-zinc-800"
            >
              Contact us
            </Link>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center">
          <h2 className="font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            Frequently asked questions
          </h2>
        </div>
        <div className="mx-auto mt-12 max-w-3xl space-y-4">
          {[
            { q: 'What is LeadPilot used for?', a: 'Teams use it for lead generation, CRM-style lead tracking, sales outreach preparation, and sales analytics across a single prospect database.' },
            { q: 'How does prospecting connect to CRM views?', a: 'Connected lead sources populate your workspace so you can apply lead scoring, monitor pipeline status, and measure outcomes without switching tools.' },
            { q: 'Who is the platform designed for?', a: 'Business owners, agencies, recruiters, consultants, sales teams, startups, and enterprise operators who need disciplined contact management and reporting.' },
            { q: 'Where can I review performance?', a: 'Use the CRM dashboard for operational KPIs and the analytics workspace for conversion rate analysis, funnel review, and source effectiveness.' },
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
