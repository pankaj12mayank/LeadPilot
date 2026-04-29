import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SearchLeadsPage } from './SearchLeadsPage'

import { useModeStore } from '@/store/modeStore'
import { useUserConfigStore } from '@/store/userConfigStore'

vi.mock('@/components/scraper/SeleniumLeadpilotPanel', () => ({
  SeleniumLeadpilotPanel: () => <div data-testid="selenium-panel" />,
}))

vi.mock('@/lib/api/leads', () => ({
  fetchLeads: vi.fn(),
}))

vi.mock('@/lib/api/companies', () => ({
  explorerSearchCompanies: vi.fn(),
  checkLinkedinSession: vi.fn(),
  runScheduledJob: vi.fn(),
}))

const { fetchLeads } = await import('@/lib/api/leads')
const { explorerSearchCompanies } = await import('@/lib/api/companies')

function setAdminConfig(overrides: Record<string, unknown> = {}) {
  useUserConfigStore.setState({
    adminConfig: {
      targeting: {
        keywords: [],
        locations: [],
        industries: [],
        company_types: [],
        preferred_locations: [],
        preferred_keywords: [],
        min_company_score: 70,
      },
      sources: {
        job_boards: true,
        startup_directories: true,
        local_listings: true,
        manual_seeds: true,
        allowed_sources: ['yc', 'job_board', 'local', 'manual'],
      },
      scoring_weights: {
        role_weight: 40,
        signal_weight: 35,
        data_weight: 25,
        company_size_weight: 20,
        base_factor_mix: 10,
      },
      signals_config: {
        hiring_enabled: true,
        scaling_enabled: true,
      },
      scheduler_config: {
        daily_time: '02:00',
        weekly_time: '03:00',
        linkedin_day: 'sat',
        daily_auto: '0 2 * * *',
        friday_heavy: '0 3 * * 5',
        saturday_linkedin: '0 10 * * 6',
        sunday_report: '0 18 * * 0',
      },
      session_policy: { expiry_days: 7 },
      retry_policy: { retry_count: 3 },
      task_priority: {
        linkedin: 'high',
        scoring: 'high',
        enrichment: 'medium',
        ingestion: 'low',
      },
      source_registry: [
        { source_name: 'yc', source_type: 'directory', enabled: true, input_type: 'url', adapter_function: 'collect_companies_from_source_pages' },
        { source_name: 'job_board', source_type: 'job_board', enabled: true, input_type: 'keyword', adapter_function: 'collect_companies_from_source_pages' },
        { source_name: 'local', source_type: 'local', enabled: true, input_type: 'keyword', adapter_function: 'collect_companies_from_source_pages' },
        { source_name: 'manual', source_type: 'manual', enabled: true, input_type: 'file', adapter_function: 'ingest_public_companies' },
      ],
      worker_config: { worker_count: 3 },
      ...overrides,
    },
    lastEventTs: '2026-04-29T12:00:00Z',
    lastChangedFields: [],
    loading: false,
    syncError: null,
    hydrated: true,
    syncTimerId: null,
  })
}

describe('SearchLeadsPage admin -> user sync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    useModeStore.setState({ mode: 'explorer' })
    setAdminConfig()
    vi.mocked(fetchLeads).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      pages: 0,
    })
  })

  it('hides disabled job_board from explorer source filters', async () => {
    setAdminConfig({
      sources: {
        job_boards: false,
        startup_directories: true,
        local_listings: true,
        manual_seeds: true,
        allowed_sources: ['yc', 'local', 'manual'],
      },
    })

    render(
      <MemoryRouter>
        <SearchLeadsPage />
      </MemoryRouter>,
    )

    await screen.findByText(/Explorer is synced to the latest admin config/i)

    const select = screen.getByDisplayValue('Source: all')
    const optionLabels = Array.from((select as HTMLSelectElement).options).map((option) => option.text)

    expect(optionLabels).not.toContain('Source: job_board')
    expect(optionLabels).toContain('Source: yc')
  })

  it('applies updated targeting defaults for new user sessions', async () => {
    setAdminConfig({
      targeting: {
        keywords: ['fintech founders'],
        locations: ['Mumbai'],
        industries: ['SaaS'],
        company_types: [],
        preferred_locations: ['Mumbai'],
        preferred_keywords: ['fintech'],
        min_company_score: 82,
      },
    })

    render(
      <MemoryRouter>
        <SearchLeadsPage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByDisplayValue('fintech founders')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Mumbai')).toBeInTheDocument()
      expect(screen.getByDisplayValue('82')).toBeInTheDocument()
    })

    expect(screen.getByText(/Keyword default: fintech founders\./i)).toBeInTheDocument()
    expect(screen.getByText(/Location default: Mumbai\./i)).toBeInTheDocument()
    expect(screen.getByText(/Score floor: 82\./i)).toBeInTheDocument()
  })

  it('shows source origin in explorer results', async () => {
    vi.mocked(explorerSearchCompanies).mockResolvedValue({
      mode: 'explorer',
      keyword: 'fintech',
      location: 'Mumbai',
      count: 1,
      results: [
        {
          id: 11,
          company_name: 'Origin Labs',
          website: 'https://originlabs.ai',
          domain: 'originlabs.ai',
          source: 'job_board',
          first_seen: '2026-04-29T12:00:00Z',
          last_updated: '2026-04-29T12:00:00Z',
          score: 78,
          priority: 'hot',
          signals: { hiring: 1, scaling: 0, content_gap: 0, ads_gap: 0 },
        },
      ],
      ingestion: {
        triggered: false,
        runs: [],
        saved_total: { created: 0, updated: 0, skipped: 0 },
        effective_sources: ['job_board'],
      },
      effective_filters: {
        source_filter: 'job_board',
        signal_hiring: false,
        signal_scaling: false,
        enabled_signal_filters: { hiring: true, scaling: true },
        enabled_sources: ['yc', 'job_board', 'local'],
      },
    })

    render(
      <MemoryRouter>
        <SearchLeadsPage />
      </MemoryRouter>,
    )

    await screen.findByText(/Explorer is synced to the latest admin config/i)
    const sourceSelect = screen.getByDisplayValue('Source: all')
    fireEvent.change(sourceSelect, { target: { value: 'job_board' } })
    fireEvent.click(screen.getByRole('button', { name: /run explorer/i }))

    await screen.findByText('Origin Labs')
    expect(screen.getByRole('link', { name: 'https://originlabs.ai' })).toBeInTheDocument()
    expect(screen.getByText('Job Board')).toBeInTheDocument()
  })
})
