import { useEffect, useState } from 'react'

import {
  adminClearFavicon,
  adminClearLogo,
  adminGetBranding,
  adminPatchBranding,
  adminUploadFavicon,
  adminUploadLogo,
} from '@/lib/api/admin'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { useBrandingStore, type Branding } from '@/store/brandingStore'

export function AdminBrandingPage() {
  const [productName, setProductName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [faviconUrl, setFaviconUrl] = useState('')
  const [footerCopyright, setFooterCopyright] = useState('')
  const [brandingMsg, setBrandingMsg] = useState<string | null>(null)
  const [brandingBusy, setBrandingBusy] = useState(false)
  const [footerBusy, setFooterBusy] = useState(false)
  const [logoBusy, setLogoBusy] = useState(false)
  const [favBusy, setFavBusy] = useState(false)
  const [previewKey, setPreviewKey] = useState(0)
  const reloadPublicBranding = useBrandingStore((s) => s.load)

  const applyBranding = (b: Partial<Branding>) => {
    if (b.product_name != null) setProductName(b.product_name || 'LeadPilot')
    if (b.logo_url !== undefined) setLogoUrl(b.logo_url || '')
    if (b.favicon_url !== undefined) setFaviconUrl(b.favicon_url || '')
    if (b.footer_copyright !== undefined) setFooterCopyright(b.footer_copyright || '')
  }

  useEffect(() => {
    let c = false
    ;(async () => {
      try {
        const b = await adminGetBranding()
        if (!c) applyBranding(b)
      } catch {
        if (!c) setBrandingMsg('Could not load branding.')
      }
    })()
    return () => {
      c = true
    }
  }, [])

  function bumpPreview() {
    setPreviewKey((k) => k + 1)
  }

  async function saveProductName() {
    setBrandingMsg(null)
    setBrandingBusy(true)
    try {
      const b = await adminPatchBranding({
        product_name: productName.trim() || 'LeadPilot',
      })
      applyBranding(b)
      await reloadPublicBranding()
      setBrandingMsg('Product name saved.')
    } catch {
      setBrandingMsg('Could not save product name.')
    } finally {
      setBrandingBusy(false)
    }
  }

  async function saveFooterCopyright() {
    setBrandingMsg(null)
    setFooterBusy(true)
    try {
      const b = await adminPatchBranding({
        footer_copyright: footerCopyright.trim().slice(0, 280),
      })
      applyBranding(b)
      await reloadPublicBranding()
      setBrandingMsg('Footer / copyright line saved.')
    } catch {
      setBrandingMsg('Could not save footer line.')
    } finally {
      setFooterBusy(false)
    }
  }

  async function resetFooterCopyright() {
    setBrandingMsg(null)
    setFooterBusy(true)
    try {
      const b = await adminPatchBranding({ footer_copyright: '' })
      applyBranding(b)
      setFooterCopyright('')
      await reloadPublicBranding()
      setBrandingMsg('Footer reset to default (current year + product name).')
    } catch {
      setBrandingMsg('Could not reset footer line.')
    } finally {
      setFooterBusy(false)
    }
  }

  async function onLogoFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setBrandingMsg(null)
    setLogoBusy(true)
    try {
      const b = await adminUploadLogo(f)
      applyBranding(b)
      bumpPreview()
      await reloadPublicBranding()
      setBrandingMsg('Logo uploaded — user portal sidebar will show it on the next navigation or refresh.')
    } catch {
      setBrandingMsg('Logo upload failed (max 2 MB; PNG, JPG, WebP, SVG, or GIF).')
    } finally {
      setLogoBusy(false)
    }
  }

  async function onFaviconFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setBrandingMsg(null)
    setFavBusy(true)
    try {
      const b = await adminUploadFavicon(f)
      applyBranding(b)
      bumpPreview()
      await reloadPublicBranding()
      setBrandingMsg('Favicon uploaded.')
    } catch {
      setBrandingMsg('Favicon upload failed (max 2 MB; ICO, PNG, or SVG).')
    } finally {
      setFavBusy(false)
    }
  }

  async function clearLogo() {
    setBrandingMsg(null)
    setLogoBusy(true)
    try {
      const b = await adminClearLogo()
      applyBranding(b)
      bumpPreview()
      await reloadPublicBranding()
      setBrandingMsg('Logo removed.')
    } catch {
      setBrandingMsg('Could not remove logo.')
    } finally {
      setLogoBusy(false)
    }
  }

  async function clearFavicon() {
    setBrandingMsg(null)
    setFavBusy(true)
    try {
      const b = await adminClearFavicon()
      applyBranding(b)
      bumpPreview()
      await reloadPublicBranding()
      setBrandingMsg('Favicon removed.')
    } catch {
      setBrandingMsg('Could not remove favicon.')
    } finally {
      setFavBusy(false)
    }
  }

  const logoSrc = logoUrl ? `${resolveMediaUrl(logoUrl)}?v=${previewKey}` : ''
  const favSrc = faviconUrl ? `${resolveMediaUrl(faviconUrl)}?v=${previewKey}` : ''

  return (
    <div className="space-y-10">
      <section>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink">Branding</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink-muted">
          Product name, footer, sidebar logo, and favicon. Files are stored under{' '}
          <span className="font-mono text-xs text-ink-subtle">storage/branding</span> and served at{' '}
          <span className="font-mono text-xs text-ink-subtle">/branding/*</span>.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
          <h2 className="font-display text-base font-semibold text-ink">Step 1: Brand identity</h2>
          <p className="mt-1 text-xs text-ink-subtle">Set app name and footer line seen by users in the product shell.</p>
          <div className="mt-4 space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="bn-name">
              Product name
            </label>
            <input
              id="bn-name"
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="field-input w-full"
            />
            <div className="flex justify-end pt-1">
              <button
                type="button"
                disabled={brandingBusy || footerBusy}
                onClick={() => void saveProductName()}
                className="rounded-xl border border-surface-border px-4 py-2.5 text-sm font-semibold text-ink-muted transition hover:border-amber-500/30 hover:text-ink disabled:opacity-50"
              >
                {brandingBusy ? 'Saving…' : 'Save name'}
              </button>
            </div>
          </div>

          <div className="mt-6 space-y-2">
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor="footer-copy">
              Footer / copyright line
            </label>
            <textarea
              id="footer-copy"
              value={footerCopyright}
              onChange={(e) => setFooterCopyright(e.target.value.slice(0, 280))}
              rows={3}
              maxLength={280}
              placeholder={`e.g. © ${new Date().getFullYear()} Your Company. All rights reserved.`}
              className="field-input min-h-[5.5rem] w-full resize-y font-mono text-sm"
            />
            <p className="text-right text-[11px] text-ink-subtle tabular-nums">{footerCopyright.length} / 280</p>
            <div className="flex flex-wrap justify-end gap-2 pt-1">
              <button
                type="button"
                disabled={footerBusy || brandingBusy}
                onClick={() => void saveFooterCopyright()}
                className="rounded-xl border border-surface-border px-4 py-2.5 text-sm font-semibold text-ink-muted transition hover:border-amber-500/30 hover:text-ink disabled:opacity-50"
              >
                {footerBusy ? 'Saving…' : 'Save footer'}
              </button>
              <button
                type="button"
                disabled={footerBusy || brandingBusy}
                onClick={() => void resetFooterCopyright()}
                className="rounded-xl border border-surface-border px-4 py-2.5 text-sm font-semibold text-ink-muted transition hover:border-amber-500/30 hover:text-ink disabled:opacity-50"
              >
                Use default line
              </button>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
          <h2 className="font-display text-base font-semibold text-ink">Step 2: Logo</h2>
          <p className="mt-1 text-xs text-ink-subtle">PNG, JPG, WebP, SVG, or GIF - max 2 MB.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="btn-primary cursor-pointer px-4 py-2 text-sm disabled:opacity-50">
              <input type="file" accept=".png,.jpg,.jpeg,.webp,.svg,.gif,image/*" className="hidden" onChange={onLogoFile} disabled={logoBusy} />
              {logoBusy ? 'Uploading…' : 'Upload logo'}
            </label>
            {logoUrl ? (
              <button
                type="button"
                disabled={logoBusy}
                onClick={() => void clearLogo()}
                className="rounded-xl border border-red-500/35 px-3 py-2 text-xs font-semibold text-red-800 dark:text-red-300"
              >
                Remove
              </button>
            ) : null}
          </div>
          {logoUrl ? (
            <div className="mt-4 space-y-2">
              <div className="inline-flex overflow-hidden rounded-xl border border-surface-border bg-field p-2 shadow-inner">
                <img key={logoSrc} src={logoSrc} alt="Logo preview" className="h-20 w-20 object-contain sm:h-24 sm:w-24" />
              </div>
              <p className="break-all font-mono text-[11px] text-ink-muted">{logoUrl}</p>
            </div>
          ) : (
            <p className="mt-3 text-xs text-ink-muted">No logo yet.</p>
          )}
        </div>

        <div className="rounded-2xl border border-surface-border bg-premium-card-light p-5 shadow-card dark:bg-premium-card-dark">
          <h2 className="font-display text-base font-semibold text-ink">Step 3: Favicon</h2>
          <p className="mt-1 text-xs text-ink-subtle">ICO, PNG, or SVG - max 2 MB.</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <label className="btn-primary cursor-pointer px-4 py-2 text-sm disabled:opacity-50">
              <input type="file" accept=".ico,.png,.svg,image/*" className="hidden" onChange={onFaviconFile} disabled={favBusy} />
              {favBusy ? 'Uploading…' : 'Upload favicon'}
            </label>
            {faviconUrl ? (
              <button
                type="button"
                disabled={favBusy}
                onClick={() => void clearFavicon()}
                className="rounded-xl border border-red-500/35 px-3 py-2 text-xs font-semibold text-red-800 dark:text-red-300"
              >
                Remove
              </button>
            ) : null}
          </div>
          {faviconUrl ? (
            <div className="mt-4 space-y-2">
              <div className="inline-flex overflow-hidden rounded-lg border border-surface-border bg-field p-2 shadow-inner">
                <img key={favSrc} src={favSrc} alt="Favicon preview" className="h-12 w-12 object-contain" />
              </div>
              <p className="break-all font-mono text-[11px] text-ink-muted">{faviconUrl}</p>
            </div>
          ) : (
            <p className="mt-3 text-xs text-ink-muted">No favicon yet.</p>
          )}
        </div>
      </section>

      {brandingMsg ? (
        <p className="rounded-xl border border-surface-border bg-premium-card-light px-4 py-3 text-sm text-ink-muted dark:bg-premium-card-dark">
          {brandingMsg}
        </p>
      ) : null}
    </div>
  )
}
