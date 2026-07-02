import { create } from 'zustand'

export type ThemePreference = 'light' | 'dark'

const STORAGE_KEY = 'leadpilot-theme-preference'

export function applyThemeToDocument(mode: 'light' | 'dark') {
  document.documentElement.classList.toggle('dark', mode === 'dark')
  document.documentElement.style.colorScheme = mode
}

function readPreference(): ThemePreference {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'light' || v === 'dark') return v
  } catch {
    /* ignore */
  }
  return 'light'
}

/** Call before React render (with ``window``) to align with stored preference. */
export function initDocumentTheme() {
  if (typeof window === 'undefined') return
  const pref = readPreference()
  applyThemeToDocument(pref)
}

type ThemeState = {
  preference: ThemePreference
  resolved: 'light' | 'dark'
  setPreference: (p: ThemePreference) => void
  syncResolved: () => void
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  preference: typeof window !== 'undefined' ? readPreference() : 'light',
  resolved: typeof window !== 'undefined' ? readPreference() : 'light',

  setPreference(preference) {
    try {
      localStorage.setItem(STORAGE_KEY, preference)
    } catch {
      /* ignore */
    }
    applyThemeToDocument(preference)
    set({ preference, resolved: preference })
  },

  syncResolved() {
    const pref = get().preference
    applyThemeToDocument(pref)
    set({ resolved: pref })
  },
}))
