import { Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'
import { footerColumns } from '@/landing/data/footer'
import { socialLinks } from '@/landing/data/contact'
import { APP_NAME } from '@/lib/copy/appCopy'

export function Footer() {
  const productName = useBrandingStore((s) => s.branding.product_name)
  const logoUrl = useBrandingStore((s) => s.branding.logo_url)
  const mediaRevision = useBrandingStore((s) => s.mediaRevision)
  const footerCopyright = useBrandingStore((s) => s.branding.footer_copyright)

  return (
    <footer className="border-t border-surface-border bg-zinc-900 dark:bg-zinc-950">
      <div className="mx-auto max-w-6xl px-4 py-16">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Brand + tagline */}
          <div className="sm:col-span-2 lg:col-span-2">
            <Link to="/" className="inline-flex items-center gap-2.5">
              {logoUrl ? (
                <img
                  src={`${resolveMediaUrl(logoUrl)}?v=${mediaRevision}`}
                  alt={productName}
                  className="h-9 w-9 rounded-xl object-contain"
                />
              ) : (
                <Sparkles className="h-5 w-5 text-amber-600" />
              )}
              <span className="font-display text-lg font-semibold text-white">
                {productName || APP_NAME}
              </span>
            </Link>
            <p className="mt-4 max-w-sm text-lg font-display font-semibold leading-snug text-amber-400/90">
              Guide every lead to conversion.
            </p>
            <p className="mt-3 text-sm leading-relaxed text-zinc-400">
              Lead generation, sales pipeline tracking, and outreach analytics in one workspace.
            </p>
            <div className="mt-5 flex gap-4">
              {socialLinks.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  className="text-sm text-zinc-500 transition-colors hover:text-amber-400"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {s.label}
                </a>
              ))}
            </div>
          </div>

          {/* Quick link columns */}
          {footerColumns.map((col) => (
            <div key={col.heading}>
              <h4 className="mb-4 text-xs font-semibold uppercase tracking-widest text-zinc-500">
                {col.heading}
              </h4>
              <ul className="space-y-3">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      to={link.href}
                      className="text-sm text-zinc-400 transition-colors hover:text-white"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Copyright only */}
        <div className="mt-14 border-t border-zinc-800 pt-6 text-center">
          <p className="text-sm text-zinc-600">
            {footerCopyright
              ? footerCopyright
              : `\u00A9 ${new Date().getFullYear()} ${productName || APP_NAME}. All rights reserved.`}
          </p>
        </div>
      </div>
    </footer>
  )
}
