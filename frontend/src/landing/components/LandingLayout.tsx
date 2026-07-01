import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'

import { Header } from './Header'
import { Footer } from './Footer'
import { ScrollToTop } from './ScrollToTop'
import { useBrandingStore } from '@/store/brandingStore'

export function LandingLayout() {
  const loadBranding = useBrandingStore((s) => s.load)
  const loaded = useBrandingStore((s) => s.loaded)

  useEffect(() => {
    if (!loaded) void loadBranding()
  }, [loadBranding, loaded])

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-white">
      <ScrollToTop />
      <Header />
      <main>
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
