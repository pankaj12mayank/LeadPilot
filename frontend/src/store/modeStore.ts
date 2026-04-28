import { create } from 'zustand'

import type { ExplorerMode } from '@/lib/api/companies'

const MODE_KEY = 'leadpilot_mode'

type ModeState = {
  mode: ExplorerMode
  hydrate: () => void
  setMode: (mode: ExplorerMode) => void
}

export const useModeStore = create<ModeState>((set) => ({
  mode: 'explorer',
  hydrate: () => {
    try {
      const raw = sessionStorage.getItem(MODE_KEY)
      if (raw === 'linkedin' || raw === 'explorer') {
        set({ mode: raw })
      }
    } catch {
      /* ignore */
    }
  },
  setMode: (mode) => {
    try {
      sessionStorage.setItem(MODE_KEY, mode)
    } catch {
      /* ignore */
    }
    set({ mode })
  },
}))
