import { Check, ImageIcon, Pencil, Trash2, Upload, Eye } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

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
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function AdminBrandingPage() {
  const [productName, setProductName] = useState('')
  const [logoUrl, setLogoUrl] = useState('')
  const [faviconUrl, setFaviconUrl] = useState('')
  const [footerCopyright, setFooterCopyright] = useState('')
  const [nameBusy, setNameBusy] = useState(false)
  const [footerBusy, setFooterBusy] = useState(false)
  const [logoBusy, setLogoBusy] = useState(false)
  const [favBusy, setFavBusy] = useState(false)
  const [previewKey, setPreviewKey] = useState(0)
  const [confirmAction, setConfirmAction] = useState<'clear-logo' | 'clear-favicon' | 'reset-footer' | null>(null)
  const [confirmBusy, setConfirmBusy] = useState(false)
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
      } catch { if (!c) toast.error('Could not load branding') }
    })()
    return () => { c = true }
  }, [])

  function bumpPreview() { setPreviewKey((k) => k + 1) }

  async function saveProductName() {
    setNameBusy(true)
    try {
      const b = await adminPatchBranding({ product_name: productName.trim() || 'LeadPilot' })
      applyBranding(b); await reloadPublicBranding()
      toast.success('Product name saved')
    } catch { toast.error('Could not save product name')
    } finally { setNameBusy(false) }
  }

  async function saveFooter() {
    setFooterBusy(true)
    try {
      const b = await adminPatchBranding({ footer_copyright: footerCopyright.trim().slice(0, 280) })
      applyBranding(b); await reloadPublicBranding()
      toast.success('Footer copyright saved')
    } catch { toast.error('Could not save footer')
    } finally { setFooterBusy(false) }
  }

  async function resetFooter() {
    setConfirmBusy(true)
    try {
      const b = await adminPatchBranding({ footer_copyright: '' })
      applyBranding(b); setFooterCopyright(''); await reloadPublicBranding()
      toast.success('Footer reset to default')
      setConfirmAction(null)
    } catch { toast.error('Could not reset footer')
    } finally { setConfirmBusy(false) }
  }

  async function onLogoFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    setLogoBusy(true)
    try {
      const b = await adminUploadLogo(f); applyBranding(b); bumpPreview(); await reloadPublicBranding()
      toast.success('Logo uploaded')
    } catch { toast.error('Upload failed (max 2MB; PNG, JPG, WebP, SVG, GIF)')
    } finally { setLogoBusy(false) }
  }

  async function onFaviconFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; e.target.value = ''
    if (!f) return
    setFavBusy(true)
    try {
      const b = await adminUploadFavicon(f); applyBranding(b); bumpPreview(); await reloadPublicBranding()
      toast.success('Favicon uploaded')
    } catch { toast.error('Upload failed (max 2MB; ICO, PNG, SVG)')
    } finally { setFavBusy(false) }
  }

  async function clearLogo() {
    setConfirmBusy(true)
    try {
      const b = await adminClearLogo(); applyBranding(b); bumpPreview(); await reloadPublicBranding()
      toast.success('Logo removed')
      setConfirmAction(null)
    } catch { toast.error('Could not remove logo')
    } finally { setConfirmBusy(false) }
  }

  async function clearFavicon() {
    setConfirmBusy(true)
    try {
      const b = await adminClearFavicon(); applyBranding(b); bumpPreview(); await reloadPublicBranding()
      toast.success('Favicon removed')
      setConfirmAction(null)
    } catch { toast.error('Could not remove favicon')
    } finally { setConfirmBusy(false) }
  }

  const logoSrc = logoUrl ? `${resolveMediaUrl(logoUrl)}?v=${previewKey}` : ''
  const favSrc = faviconUrl ? `${resolveMediaUrl(faviconUrl)}?v=${previewKey}` : ''

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Branding</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Customize your app identity &mdash; name, logo, favicon, and footer.
        </p>
      </div>

      {/* Live Preview Card */}
      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="flex items-center gap-2 border-b border-surface-border bg-zinc-50/50 px-5 py-3 dark:bg-zinc-800/50">
          <Eye className="h-4 w-4 text-zinc-400" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Live Preview</span>
        </div>
        <div className="flex items-center gap-4 px-5 py-4">
          {logoSrc ? (
            <img src={logoSrc} alt="Logo" className="h-10 w-10 rounded-lg object-contain" />
          ) : (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/15 text-sm font-bold text-amber-600">
              {productName.charAt(0) || 'L'}
            </div>
          )}
          <div>
            <p className="font-display text-base font-semibold text-zinc-900 dark:text-white">{productName || 'LeadPilot'}</p>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">Brand preview — as seen by users</p>
          </div>
        </div>
      </div>

      {/* 3-column layout */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Brand Identity */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/15 to-amber-500/5">
            <Pencil className="h-6 w-6 text-amber-600" />
          </div>
          <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Brand Identity</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Set your product name and footer copyright line.
          </p>

          <div className="mt-6 space-y-5">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400" htmlFor="bn-name">
                Product Name
              </label>
              <div className="mt-1.5 flex gap-2">
                <input
                  id="bn-name"
                  value={productName}
                  onChange={(e) => setProductName(e.target.value)}
                  className="flex-1 rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25"
                />
                <button
                  type="button"
                  disabled={nameBusy}
                  onClick={() => void saveProductName()}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  <Check className="h-3.5 w-3.5" />
                  {nameBusy ? '...' : 'Save'}
                </button>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400" htmlFor="footer-copy">
                  Footer / Copyright
                </label>
                <span className="text-xs text-zinc-400 dark:text-zinc-500">{footerCopyright.length} / 280</span>
              </div>
              <textarea
                id="footer-copy"
                value={footerCopyright}
                onChange={(e) => setFooterCopyright(e.target.value.slice(0, 280))}
                rows={3}
                maxLength={280}
                placeholder={`e.g. © ${new Date().getFullYear()} Your Company.`}
                className="mt-1.5 w-full resize-none rounded-lg border border-surface-border bg-transparent px-3 py-2 text-sm outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  type="button"
                  disabled={footerBusy}
                  onClick={() => setConfirmAction('reset-footer')}
                  className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
                >
                  Reset
                </button>
                <button
                  type="button"
                  disabled={footerBusy}
                  onClick={() => void saveFooter()}
                  className="inline-flex items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
                >
                  <Check className="h-3 w-3" />
                  {footerBusy ? '...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Logo */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500/15 to-blue-500/5">
            <ImageIcon className="h-6 w-6 text-blue-600" />
          </div>
          <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Logo</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            PNG, JPG, WebP, SVG, or GIF &mdash; max 2 MB. Displayed in the sidebar.
          </p>

          <div className="mt-6">
            {logoUrl ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center rounded-xl border border-surface-border bg-zinc-50 p-6 shadow-inner dark:bg-zinc-800">
                  <img key={logoSrc} src={logoSrc} alt="Logo preview" className="h-28 w-28 object-contain" />
                </div>
                <div className="flex gap-2">
                  <label className="flex-1 cursor-pointer rounded-lg border border-surface-border px-4 py-2.5 text-center text-sm font-medium text-zinc-600 transition hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800">
                    <Upload className="mr-1.5 inline h-4 w-4" />
                    Change
                    <input type="file" accept=".png,.jpg,.jpeg,.webp,.svg,.gif,image/*" className="hidden" onChange={onLogoFile} disabled={logoBusy} />
                  </label>
                  <button
                    type="button"
                    disabled={logoBusy}
                    onClick={() => setConfirmAction('clear-logo')}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/35 px-4 py-2.5 text-sm font-semibold text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                  >
                    <Trash2 className="h-4 w-4" />
                    Remove
                  </button>
                </div>
                <p className="truncate text-xs text-zinc-400 dark:text-zinc-500" title={logoUrl}>{logoUrl}</p>
              </div>
            ) : (
              <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-surface-border bg-zinc-50 p-8 transition hover:border-amber-500/40 hover:bg-amber-50/50 dark:bg-zinc-800/50 dark:hover:bg-amber-950/20">
                {logoBusy ? (
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-600" />
                ) : (
                  <>
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-500/10">
                      <Upload className="h-6 w-6 text-amber-600" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Click to upload logo</p>
                      <p className="mt-1 text-xs text-zinc-400">PNG, JPG, WebP, SVG, GIF &bull; up to 2 MB</p>
                    </div>
                  </>
                )}
                <input type="file" accept=".png,.jpg,.jpeg,.webp,.svg,.gif,image/*" className="hidden" onChange={onLogoFile} disabled={logoBusy} />
              </label>
            )}
          </div>
        </div>

        {/* Favicon */}
        <div className="rounded-2xl border border-surface-border bg-white p-6 shadow-sm dark:bg-zinc-900">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500/15 to-purple-500/5">
            <ImageIcon className="h-6 w-6 text-purple-600" />
          </div>
          <h2 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">Favicon</h2>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            ICO, PNG, or SVG &mdash; max 2 MB. Shows in browser tabs.
          </p>

          <div className="mt-6">
            {faviconUrl ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center rounded-xl border border-surface-border bg-zinc-50 p-6 shadow-inner dark:bg-zinc-800">
                  <img key={favSrc} src={favSrc} alt="Favicon preview" className="h-16 w-16 object-contain" />
                </div>
                <div className="flex gap-2">
                  <label className="flex-1 cursor-pointer rounded-lg border border-surface-border px-4 py-2.5 text-center text-sm font-medium text-zinc-600 transition hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800">
                    <Upload className="mr-1.5 inline h-4 w-4" />
                    Change
                    <input type="file" accept=".ico,.png,.svg,image/*" className="hidden" onChange={onFaviconFile} disabled={favBusy} />
                  </label>
                  <button
                    type="button"
                    disabled={favBusy}
                    onClick={() => setConfirmAction('clear-favicon')}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-red-500/35 px-4 py-2.5 text-sm font-semibold text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                  >
                    <Trash2 className="h-4 w-4" />
                    Remove
                  </button>
                </div>
                <p className="truncate text-xs text-zinc-400 dark:text-zinc-500" title={faviconUrl}>{faviconUrl}</p>
              </div>
            ) : (
              <label className="flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-surface-border bg-zinc-50 p-8 transition hover:border-purple-500/40 hover:bg-purple-50/50 dark:bg-zinc-800/50 dark:hover:bg-purple-950/20">
                {favBusy ? (
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-amber-500/30 border-t-amber-600" />
                ) : (
                  <>
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-500/10">
                      <Upload className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Click to upload favicon</p>
                      <p className="mt-1 text-xs text-zinc-400">ICO, PNG, SVG &bull; up to 2 MB</p>
                    </div>
                  </>
                )}
                <input type="file" accept=".ico,.png,.svg,image/*" className="hidden" onChange={onFaviconFile} disabled={favBusy} />
              </label>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmAction === 'clear-logo'}
        title="Remove Logo"
        message="Are you sure you want to remove the logo? The default icon will be shown instead."
        confirmLabel="Remove Logo"
        variant="danger"
        busy={confirmBusy}
        onConfirm={() => void clearLogo()}
        onCancel={() => setConfirmAction(null)}
      />
      <ConfirmDialog
        open={confirmAction === 'clear-favicon'}
        title="Remove Favicon"
        message="Are you sure you want to remove the favicon? The browser tab will show no icon."
        confirmLabel="Remove Favicon"
        variant="danger"
        busy={confirmBusy}
        onConfirm={() => void clearFavicon()}
        onCancel={() => setConfirmAction(null)}
      />
      <ConfirmDialog
        open={confirmAction === 'reset-footer'}
        title="Reset Footer Copyright"
        message="This will clear the custom footer copyright text and revert to the default format."
        confirmLabel="Reset"
        variant="warning"
        busy={confirmBusy}
        onConfirm={() => void resetFooter()}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}
