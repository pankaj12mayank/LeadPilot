import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LandingPage } from './LandingPage'

import { useThemeStore } from '@/store/themeStore'

const mockedConfig = {
  sections: [
    {
      id: 'hero',
      label: 'Hero Section',
      enabled: true,
      order: 2,
      heading: 'Hero Heading',
      subheading: 'Hero Subheading',
      body: 'Hero Body',
      cta_primary_text: 'Login',
      cta_primary_link: '/login',
    },
    {
      id: 'problem',
      label: 'Problem Section',
      enabled: true,
      order: 1,
      heading: 'Problem Heading',
      items: ['Pain 1', 'Pain 2'],
    },
    {
      id: 'faq',
      label: 'FAQ Section',
      enabled: false,
      order: 3,
      heading: 'FAQ Hidden',
    },
  ],
  seo: {
    title: 'Landing SEO Title',
    description: 'Landing SEO Description',
    keywords: ['lead generation', 'b2b'],
    og_title: 'OG Landing',
    og_description: 'OG Desc',
    og_image: '',
    structured_data_type: 'SoftwareApplication',
  },
  geo: { enabled: true, location_label: 'Mumbai', keyword_focus: 'AI leads' },
  theme: {
    default_theme: 'dark' as const,
    brand_colors: { primary: '#000' },
    font_family: 'Inter',
  },
  analytics: {
    enabled: true,
    track_page_views: true,
    track_cta_clicks: true,
    track_conversions: true,
  },
}

const trackSpy = vi.fn()
vi.mock('@/lib/api/landing', () => ({
  publicGetLandingConfig: vi.fn(async () => mockedConfig),
  publicTrackLandingEvent: (...args: unknown[]) => trackSpy(...args),
}))

describe('LandingPage dynamic rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useThemeStore.setState({ preference: 'system', resolved: 'light' })
    document.title = 'reset'
    document.head.querySelectorAll('meta[name="description"],meta[name="keywords"],meta[property^="og:"]').forEach((el) => el.remove())
    const ld = document.getElementById('leadpilot-landing-jsonld')
    if (ld) ld.remove()
  })

  it('renders enabled sections ordered by order and hides disabled section', async () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )

    await screen.findByText('Problem Heading')
    expect(screen.queryByText('FAQ Hidden')).not.toBeInTheDocument()
    const headings = screen.getAllByRole('heading', { level: 2 }).map((x) => x.textContent || '')
    expect(headings.indexOf('Problem Heading')).toBeLessThan(headings.indexOf('Hero Heading'))
  })

  it('applies SEO tags and tracks page/cta events', async () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    )
    await screen.findByText('Hero Heading')

    expect(document.title).toBe('Landing SEO Title')
    const desc = document.querySelector('meta[name="description"]')
    expect(desc?.getAttribute('content')).toBe('Landing SEO Description')
    const keywords = document.querySelector('meta[name="keywords"]')
    expect(keywords?.getAttribute('content')).toContain('lead generation')
    const ld = document.getElementById('leadpilot-landing-jsonld')
    expect(ld).not.toBeNull()

    await waitFor(() => {
      expect(trackSpy).toHaveBeenCalledWith('page_view', 'landing', expect.any(String))
    })
    fireEvent.click(screen.getByRole('link', { name: /login/i }))
    expect(trackSpy).toHaveBeenCalledWith('cta_click', 'hero', '/login')
  })
})
