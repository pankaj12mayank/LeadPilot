import { create } from 'zustand'

import { getApiBaseURL } from '@/lib/api/client'
import { resolveMediaUrl } from '@/lib/utils/mediaUrl'

export type Branding = {
  product_name: string
  logo_url: string
  favicon_url: string
  /** If empty, footer shows "{year} {product_name}. All rights reserved." */
  footer_copyright: string
}

type State = {
  branding: Branding
  loaded: boolean
  /** Bumps when branding is re-fetched so logo/favicon URLs bypass browser cache. */
  mediaRevision: number
  load: () => Promise<void>
  applyFavicon: () => void
}

function applyFaviconHref(href: string) {
  const full = resolveMediaUrl(href)
  if (!full) return
  let link = document.querySelector("link[rel='icon']") as HTMLLinkElement | null
  if (!link) {
    link = document.createElement('link')
    link.rel = 'icon'
    document.head.appendChild(link)
  }
  link.href = full
}

export const useBrandingStore = create<State>((set, get) => ({
  branding: { product_name: 'LeadPilot', logo_url: '', favicon_url: '', footer_copyright: '' },
  loaded: false,
  mediaRevision: 0,
  applyFavicon: () => {
    applyFaviconHref(get().branding.favicon_url)
  },
  load: async () => {
    try {
      const res = await fetch(`${getApiBaseURL()}/public/branding`)
      if (!res.ok) throw new Error('branding')
      const data = (await res.json()) as Partial<Branding>
      const branding: Branding = {
        product_name: (data.product_name || 'LeadPilot').trim() || 'LeadPilot',
        logo_url: (data.logo_url || '').trim(),
        favicon_url: (data.favicon_url || '').trim(),
        footer_copyright: (data.footer_copyright ?? '').trim().slice(0, 280),
      }
      set({ branding, loaded: true, mediaRevision: get().mediaRevision + 1 })
      get().applyFavicon()
    } catch {
      set({ loaded: true })
    }
  },
}))
