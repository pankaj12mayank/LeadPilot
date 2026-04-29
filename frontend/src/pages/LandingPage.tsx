import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'

import { publicGetLandingConfig, publicTrackLandingEvent, type LandingConfig, type LandingSection } from '@/lib/api/landing'
import { APP_NAME } from '@/lib/copy/appCopy'
import { ThemeToggle } from '@/components/layout/ThemeToggle'
import { useThemeStore } from '@/store/themeStore'

function sortedSections(cfg: LandingConfig | null) {
  return [...(cfg?.sections || [])].filter((x) => x.enabled).sort((a, b) => (a.order || 0) - (b.order || 0))
}

function SectionBlock({ section }: { section: LandingSection }) {
  return (
    <section className="rounded-3xl border border-surface-border bg-premium-card-light p-6 shadow-card dark:bg-premium-card-dark sm:p-8">
      <h2 className="font-display text-2xl font-semibold text-ink sm:text-3xl">{section.heading || section.label}</h2>
      {section.subheading ? <p className="mt-2 text-sm text-ink-muted sm:text-base">{section.subheading}</p> : null}
      {section.body ? <p className="mt-3 text-sm leading-6 text-ink-muted sm:text-base">{section.body}</p> : null}
      {(section.items || []).length > 0 ? (
        <ul className="mt-4 grid gap-2 text-sm text-ink-muted sm:grid-cols-2">
          {(section.items || []).map((item, idx) => (
            <li key={`${section.id}-${idx}`} className="rounded-xl border border-surface-border bg-field/40 px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      ) : null}
      {section.image_url ? <img src={section.image_url} alt={section.label} loading="lazy" className="mt-4 w-full rounded-2xl object-cover" /> : null}
      {(section.cta_primary_text || section.cta_secondary_text) ? (
        <div className="mt-6 flex flex-wrap gap-3">
          {section.cta_primary_text ? (
            <Link
              to={section.cta_primary_link || '/login'}
              onClick={() => void publicTrackLandingEvent('cta_click', section.id, section.cta_primary_link || '/login')}
              className="inline-flex items-center gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-500/15 dark:text-amber-200"
            >
              {section.cta_primary_text}
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : null}
          {section.cta_secondary_text ? (
            <Link
              to={section.cta_secondary_link || '/about'}
              onClick={() => void publicTrackLandingEvent('cta_click', section.id, section.cta_secondary_link || '/about')}
              className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-4 py-2 text-sm font-medium text-ink-muted transition hover:bg-field/60 hover:text-ink"
            >
              {section.cta_secondary_text}
            </Link>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}

export function LandingPage() {
  const [cfg, setCfg] = useState<LandingConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const preference = useThemeStore((s) => s.preference)
  const setPreference = useThemeStore((s) => s.setPreference)
  const sections = useMemo(() => sortedSections(cfg), [cfg])

  useEffect(() => {
    const run = async () => {
      try {
        const config = await publicGetLandingConfig()
        setCfg(config)
        if (preference === 'system' && config.theme.default_theme !== 'system') {
          setPreference(config.theme.default_theme)
        }
      } finally {
        setLoading(false)
      }
    }
    void run()
  }, [preference, setPreference])

  useEffect(() => {
    if (!cfg) return
    document.title = cfg.seo.title || `${APP_NAME} | AI Lead Growth System`
    const ensureMeta = (name: string, content: string, prop = false) => {
      const selector = prop ? `meta[property="${name}"]` : `meta[name="${name}"]`
      let el = document.querySelector(selector) as HTMLMetaElement | null
      if (!el) {
        el = document.createElement('meta')
        if (prop) el.setAttribute('property', name)
        else el.setAttribute('name', name)
        document.head.appendChild(el)
      }
      el.setAttribute('content', content)
    }
    ensureMeta('description', cfg.seo.description || '')
    ensureMeta('keywords', (cfg.seo.keywords || []).join(', '))
    ensureMeta('og:title', cfg.seo.og_title || cfg.seo.title || '', true)
    ensureMeta('og:description', cfg.seo.og_description || cfg.seo.description || '', true)
    if (cfg.seo.og_image) ensureMeta('og:image', cfg.seo.og_image, true)
    const scriptId = 'leadpilot-landing-jsonld'
    const prev = document.getElementById(scriptId)
    if (prev) prev.remove()
    const script = document.createElement('script')
    script.id = scriptId
    script.type = 'application/ld+json'
    script.text = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': cfg.seo.structured_data_type || 'SoftwareApplication',
      name: APP_NAME,
      description: cfg.seo.description,
    })
    document.head.appendChild(script)
    if (cfg.analytics.enabled && cfg.analytics.track_page_views) {
      void publicTrackLandingEvent('page_view', 'landing', window.location.pathname)
    }
  }, [cfg])

  return (
    <div className="min-h-screen bg-surface text-ink">
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 sm:px-6 lg:px-8">
        <div className="flex items-center justify-end">
          <ThemeToggle />
        </div>
        {loading ? (
          <section className="rounded-3xl border border-surface-border bg-premium-card-light p-8 dark:bg-premium-card-dark">Loading...</section>
        ) : null}
        {sections.map((section) => (
          <SectionBlock key={section.id} section={section} />
        ))}
      </main>
    </div>
  )
}
