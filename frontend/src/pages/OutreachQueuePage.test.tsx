import { act, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { OutreachQueuePage } from './OutreachQueuePage'

import type { AdminConfig } from '@/lib/api/admin'
import { useUserConfigStore } from '@/store/userConfigStore'
import type { Lead } from '@/types/models'

vi.mock('@/lib/api/leads', () => ({
  fetchLeads: vi.fn(),
}))

const { fetchLeads } = await import('@/lib/api/leads')

const BASE_CONFIG: AdminConfig = {
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
    linkedin: true,
    public_db: true,
    google_maps: true,
    indiamart: true,
    justdial: true,
    eworldtrade: true,
    global_sources: true,
    thomasnet: true,
    yelp: true,
    faire: true,
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
  ai_control: {
    ollama_enabled: true,
    api_enabled: true,
  },
  scoring_control: {
    role: 40,
    signals: 35,
    ai_score: 25,
  },
  safety_control: {
    delay_seconds: 1,
    batch_size: 10,
    retry_count: 3,
    pagination_limit: 5,
  },
  queue_priority: {
    linkedin: 'high',
    ai: 'high',
    others: 'medium',
  },
  source_registry: [
    { source_name: 'yc', source_type: 'directory', enabled: true, input_type: 'url', adapter_function: 'collect_companies_from_source_pages' },
    { source_name: 'job_board', source_type: 'job_board', enabled: true, input_type: 'keyword', adapter_function: 'collect_companies_from_source_pages' },
    { source_name: 'local', source_type: 'local', enabled: true, input_type: 'keyword', adapter_function: 'collect_companies_from_source_pages' },
    { source_name: 'manual', source_type: 'manual', enabled: true, input_type: 'file', adapter_function: 'ingest_public_companies' },
  ],
  worker_config: { worker_count: 3 },
}

function lead(overrides: Partial<Lead>): Lead {
  return {
    id: crypto.randomUUID(),
    full_name: 'Lead',
    title: '',
    company_name: 'Company',
    company_website: '',
    linkedin_url: '',
    email: '',
    phone: '',
    company_size: '',
    industry: '',
    location: '',
    source_platform: 'manual',
    notes: '',
    score: 50,
    tier: 'warm',
    status: 'new',
    personalized_message: '',
    followup_message: '',
    last_contacted_at: '',
    follow_up_reminder_at: '',
    created_at: '2026-04-29T00:00:00Z',
    updated_at: '2026-04-29T00:00:00Z',
    ...overrides,
  }
}

function setAdminConfig(overrides: Record<string, unknown> = {}) {
  useUserConfigStore.setState({
    adminConfig: {
      ...BASE_CONFIG,
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

function getRenderedLeadOrder() {
  const body = document.querySelector('tbody')
  if (!body) return []
  return Array.from(body.querySelectorAll('tr'))
    .map((row) => row.querySelector('td')?.textContent?.trim() || '')
    .filter(Boolean)
}

describe('OutreachQueuePage admin -> user sync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setAdminConfig()
  })

  it('changes lead ranking when scoring weights change', async () => {
    vi.mocked(fetchLeads).mockResolvedValue({
      items: [
        lead({
          id: 'signal-lead',
          full_name: 'Signal Lead',
          score: 74,
          signal_hiring: 1,
          signal_scaling: 1,
          signal_content_gap: 1,
        }),
        lead({
          id: 'target-lead',
          full_name: 'Target Lead',
          title: 'Fintech Founder',
          company_name: 'Target Labs',
          location: 'Mumbai',
          industry: 'SaaS',
          score: 74,
        }),
      ],
      total: 2,
      page: 1,
      page_size: 200,
      pages: 1,
    })

    setAdminConfig({
      targeting: {
        ...BASE_CONFIG.targeting,
        preferred_keywords: ['fintech'],
        preferred_locations: ['mumbai'],
        industries: ['saas'],
      },
      scoring_weights: {
        ...BASE_CONFIG.scoring_weights,
        role_weight: 90,
        signal_weight: 10,
        data_weight: 1,
      },
    })

    render(<OutreachQueuePage />)

    await waitFor(() => {
      expect(getRenderedLeadOrder().slice(0, 2)).toEqual(['Target Lead', 'Signal Lead'])
    })

    await act(async () => {
      useUserConfigStore.setState((state) => ({
        adminConfig: {
          ...state.adminConfig,
          scoring_weights: {
            ...state.adminConfig.scoring_weights,
            role_weight: 10,
            signal_weight: 90,
            data_weight: 1,
          },
        },
        lastEventTs: '2026-04-29T12:01:00Z',
        lastChangedFields: ['admin_config.scoring_weights.signal_weight'],
      }))
    })

    await waitFor(() => {
      expect(getRenderedLeadOrder().slice(0, 2)).toEqual(['Signal Lead', 'Target Lead'])
    })
  })

  it('updates UI priority order when task priority changes', async () => {
    vi.mocked(fetchLeads).mockResolvedValue({
      items: [
        lead({
          id: 'linkedin-lead',
          full_name: 'LinkedIn Lead',
          score: 62,
          source_platform: 'linkedin',
        }),
        lead({
          id: 'manual-lead',
          full_name: 'Manual Lead',
          score: 68,
          source_platform: 'manual',
        }),
      ],
      total: 2,
      page: 1,
      page_size: 200,
      pages: 1,
    })

    setAdminConfig({
      task_priority: {
        linkedin: 'low',
        scoring: 'low',
        enrichment: 'low',
        ingestion: 'high',
      },
    })

    render(<OutreachQueuePage />)

    await waitFor(() => {
      expect(getRenderedLeadOrder().slice(0, 2)).toEqual(['Manual Lead', 'LinkedIn Lead'])
    })

    await act(async () => {
      useUserConfigStore.setState((state) => ({
        adminConfig: {
          ...state.adminConfig,
          task_priority: {
            linkedin: 'high',
            scoring: 'low',
            enrichment: 'low',
            ingestion: 'low',
          },
        },
        lastEventTs: '2026-04-29T12:02:00Z',
        lastChangedFields: ['admin_config.task_priority.linkedin'],
      }))
    })

    await waitFor(() => {
      expect(getRenderedLeadOrder().slice(0, 2)).toEqual(['LinkedIn Lead', 'Manual Lead'])
    })
    expect(screen.getByText('LinkedIn')).toBeInTheDocument()
  })
})
