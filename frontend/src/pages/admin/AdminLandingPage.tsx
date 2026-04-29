import { useEffect, useMemo, useState } from 'react'
import { GripVertical, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import {
  adminGenerateLandingContent,
  adminGetLandingConfig,
  adminPatchLandingConfig,
  type LandingConfig,
  type LandingSection,
} from '@/lib/api/landing'

function reorderByDrag(items: LandingSection[], fromId: string, toId: string): LandingSection[] {
  const next = [...items]
  const from = next.findIndex((x) => x.id === fromId)
  const to = next.findIndex((x) => x.id === toId)
  if (from < 0 || to < 0 || from === to) return items
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return next.map((x, i) => ({ ...x, order: i + 1 }))
}

export function AdminLandingPage() {
  const [cfg, setCfg] = useState<LandingConfig | null>(null)
  const [dragId, setDragId] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void adminGetLandingConfig().then(setCfg)
  }, [])

  const sections = useMemo(() => [...(cfg?.sections || [])].sort((a, b) => a.order - b.order), [cfg])

  const save = async () => {
    if (!cfg) return
    setBusy(true)
    try {
      const saved = await adminPatchLandingConfig(cfg)
      setCfg(saved)
      toast.success('Landing CMS saved')
    } finally {
      setBusy(false)
    }
  }

  const generate = async () => {
    if (!cfg) return
    const out = await adminGenerateLandingContent(cfg.geo.location_label, cfg.geo.keyword_focus)
    setCfg({
      ...cfg,
      sections: cfg.sections.map((s) =>
        s.id === 'hero'
          ? {
              ...s,
              heading: String(out.hero_heading || s.heading || ''),
              subheading: String(out.hero_subheading || s.subheading || ''),
              cta_primary_text: String(out.cta_text || s.cta_primary_text || ''),
            }
          : s,
      ),
    })
    toast.success('AI draft generated for hero section')
  }

  if (!cfg) return <div className="rounded-2xl border border-surface-border p-4">Loading landing CMS...</div>

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-4 dark:bg-premium-card-dark">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="font-display text-xl font-semibold">Landing CMS</h1>
          <div className="flex gap-2">
            <button type="button" onClick={generate} className="inline-flex items-center gap-1 rounded-lg border border-surface-border px-3 py-2 text-sm">
              <Sparkles className="h-4 w-4" />
              Generate Content
            </button>
            <button type="button" disabled={busy} onClick={() => void save()} className="rounded-lg bg-amber-500/20 px-3 py-2 text-sm font-semibold">
              Save
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 rounded-2xl border border-surface-border p-4 sm:grid-cols-2">
        <label className="text-sm">Default Theme
          <select
            className="mt-1 w-full rounded-lg border border-surface-border bg-transparent px-3 py-2"
            value={cfg.theme.default_theme}
            onChange={(e) => setCfg({ ...cfg, theme: { ...cfg.theme, default_theme: e.target.value as LandingConfig['theme']['default_theme'] } })}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <label className="text-sm">Font Family
          <input className="mt-1 w-full rounded-lg border border-surface-border bg-transparent px-3 py-2" value={cfg.theme.font_family} onChange={(e) => setCfg({ ...cfg, theme: { ...cfg.theme, font_family: e.target.value } })} />
        </label>
      </section>

      <section className="grid gap-3">
        {sections.map((section) => (
          <article
            key={section.id}
            draggable
            onDragStart={() => setDragId(section.id)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => setCfg({ ...cfg, sections: reorderByDrag(sections, dragId, section.id) })}
            className="rounded-2xl border border-surface-border bg-premium-card-light p-4 dark:bg-premium-card-dark"
          >
            <div className="mb-3 flex items-center justify-between">
              <div className="inline-flex items-center gap-2">
                <GripVertical className="h-4 w-4 text-ink-muted" />
                <strong>{section.label}</strong>
              </div>
              <label className="inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={section.enabled}
                  onChange={(e) =>
                    setCfg({
                      ...cfg,
                      sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, enabled: e.target.checked } : s)),
                    })
                  }
                />
                Enabled
              </label>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <input className="rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm" value={section.heading || ''} placeholder="Heading" onChange={(e) => setCfg({ ...cfg, sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, heading: e.target.value } : s)) })} />
              <input className="rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm" value={section.subheading || ''} placeholder="Subheading" onChange={(e) => setCfg({ ...cfg, sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, subheading: e.target.value } : s)) })} />
              <textarea className="sm:col-span-2 rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm" rows={3} value={section.body || ''} placeholder="Body" onChange={(e) => setCfg({ ...cfg, sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, body: e.target.value } : s)) })} />
              <input className="rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm" value={section.image_url || ''} placeholder="Image URL" onChange={(e) => setCfg({ ...cfg, sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, image_url: e.target.value } : s)) })} />
              <input className="rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm" value={section.items?.join('\n') || ''} placeholder="List items (newline separated)" onChange={(e) => setCfg({ ...cfg, sections: cfg.sections.map((s) => (s.id === section.id ? { ...s, items: e.target.value.split('\n').map((x) => x.trim()).filter(Boolean) } : s)) })} />
            </div>
          </article>
        ))}
      </section>
    </div>
  )
}
