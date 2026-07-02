import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type AdminState = {
  token: string | null
  email: string | null
  setToken: (t: string | null, email?: string | null) => void
  logout: () => void
}

export const useAdminStore = create<AdminState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      setToken: (t, email) => set({ token: t, email: email ?? null }),
      logout: () => set({ token: null, email: null }),
    }),
    { name: 'leadpilot-admin' },
  ),
)
