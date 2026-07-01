import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { HomePage } from './HomePage'

const mockBranding = {
  branding: { product_name: 'LeadPilot', logo_url: '', favicon_url: '', footer_copyright: '' },
  mediaRevision: 0,
  loaded: true,
  load: vi.fn(),
}
vi.mock('@/store/brandingStore', () => ({
  useBrandingStore: (selector: (s: typeof mockBranding) => unknown) => selector(mockBranding),
}))

const mockTheme = { preference: 'system', resolved: 'light', setPreference: vi.fn(), syncResolved: vi.fn() }
vi.mock('@/store/themeStore', () => ({
  useThemeStore: (selector: (s: typeof mockTheme) => unknown) => selector(mockTheme),
}))

const mockAuth = { token: null, user: null, logout: vi.fn() }
vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (s: typeof mockAuth) => unknown) => selector(mockAuth),
}))

describe('HomePage', () => {
  it('renders the hero section with heading', async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/AI-Powered Lead/i)).toBeTruthy()
  })

  it('renders the features section', async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/Everything you need/i)).toBeTruthy()
  })

  it('renders the pricing section', async () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )
    expect(await screen.findByText(/Choose the right plan/i)).toBeTruthy()
  })
})
