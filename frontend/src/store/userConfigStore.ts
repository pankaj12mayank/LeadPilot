import { create } from 'zustand'

import { fetchUserConfigSync, type UserConfigSyncPayload } from '@/lib/api/companies'
import type { AdminConfig } from '@/lib/api/admin'

const CONFIG_KEY = 'leadpilot_user_admin_config'
const EVENT_TS_KEY = 'leadpilot_user_admin_config_event_ts'
export const USER_CONFIG_UPDATED_EVENT = 'leadpilot:user-config-updated'

const DEFAULT_CONFIG: AdminConfig = {
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
    allowed_sources: ['yc', 'job_board', 'local', 'crunchbase', 'builtwith', 'manual'],
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
  session_policy: {
    expiry_days: 7,
  },
  retry_policy: {
    retry_count: 3,
  },
  task_priority: {
    linkedin: 'high',
    scoring: 'high',
    enrichment: 'medium',
    ingestion: 'low',
  },
  source_registry: [
    {
      source_name: 'yc',
      source_type: 'directory',
      enabled: true,
      input_type: 'url',
      adapter_function: 'collect_companies_from_source_pages',
    },
    {
      source_name: 'crunchbase',
      source_type: 'directory',
      enabled: true,
      input_type: 'url',
      adapter_function: 'collect_companies_from_source_pages',
    },
    {
      source_name: 'job_board',
      source_type: 'job_board',
      enabled: true,
      input_type: 'keyword',
      adapter_function: 'collect_companies_from_source_pages',
    },
    {
      source_name: 'local',
      source_type: 'local',
      enabled: true,
      input_type: 'keyword',
      adapter_function: 'collect_companies_from_source_pages',
    },
    {
      source_name: 'builtwith',
      source_type: 'directory',
      enabled: true,
      input_type: 'url',
      adapter_function: 'collect_companies_from_source_pages',
    },
    {
      source_name: 'manual',
      source_type: 'manual',
      enabled: true,
      input_type: 'file',
      adapter_function: 'ingest_public_companies',
    },
  ],
  worker_config: {
    worker_count: 3,
  },
}

type UserConfigState = {
  adminConfig: AdminConfig
  lastEventTs: string
  lastChangedFields: string[]
  loading: boolean
  syncError: string | null
  hydrated: boolean
  syncTimerId: number | null
  hydrate: () => void
  fetchLatest: () => Promise<void>
  startSync: () => Promise<void>
  stopSync: () => void
  clear: () => void
}

function persist(config: AdminConfig, ts: string): void {
  try {
    sessionStorage.setItem(CONFIG_KEY, JSON.stringify(config))
    sessionStorage.setItem(EVENT_TS_KEY, ts)
  } catch {
    /* ignore */
  }
}

function dispatchUserConfigUpdated(detail: { timestamp: string; changedFields: string[]; adminConfig: AdminConfig }): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(USER_CONFIG_UPDATED_EVENT, { detail }))
}

function applyPayload(
  set: (fn: (prev: UserConfigState) => Partial<UserConfigState>) => void,
  get: () => UserConfigState,
  payload: UserConfigSyncPayload,
): void {
  const ts = String(payload.config_event?.timestamp || '')
  const changedFields = Array.isArray(payload.config_event?.changed_fields)
    ? payload.config_event.changed_fields.map((x) => String(x || '').trim()).filter(Boolean)
    : []
  const prevTs = get().lastEventTs
  persist(payload.admin_config, ts)
  set(() => ({
    adminConfig: payload.admin_config,
    lastEventTs: ts,
    lastChangedFields: changedFields,
    loading: false,
    syncError: null,
  }))
  if (ts && ts !== prevTs) {
    dispatchUserConfigUpdated({ timestamp: ts, changedFields, adminConfig: payload.admin_config })
  }
}

export const useUserConfigStore = create<UserConfigState>((set, get) => ({
  adminConfig: DEFAULT_CONFIG,
  lastEventTs: '',
  lastChangedFields: [],
  loading: false,
  syncError: null,
  hydrated: false,
  syncTimerId: null,
  hydrate: () => {
    if (get().hydrated) return
    try {
      const raw = sessionStorage.getItem(CONFIG_KEY)
      const ts = sessionStorage.getItem(EVENT_TS_KEY) || ''
      if (raw) {
        const parsed = JSON.parse(raw) as AdminConfig
        set(() => ({ adminConfig: parsed, lastEventTs: ts, lastChangedFields: [], hydrated: true }))
        return
      }
    } catch {
      /* ignore */
    }
    set(() => ({ hydrated: true }))
  },
  fetchLatest: async () => {
    set(() => ({ loading: true, syncError: null }))
    try {
      const payload = await fetchUserConfigSync()
      applyPayload(set, get, payload)
    } catch (e) {
      set(() => ({ loading: false, syncError: e instanceof Error ? e.message : 'config_sync_failed' }))
    }
  },
  startSync: async () => {
    get().hydrate()
    if (get().syncTimerId !== null) return
    await get().fetchLatest()
    const timerId = window.setInterval(async () => {
      try {
        const payload = await fetchUserConfigSync()
        const incomingTs = String(payload.config_event?.timestamp || '')
        const currentTs = get().lastEventTs
        if (!currentTs || (incomingTs && incomingTs !== currentTs)) {
          applyPayload(set, get, payload)
          return
        }
        if (!incomingTs) {
          applyPayload(set, get, payload)
        }
      } catch {
        /* keep prior config; next interval retries */
      }
    }, 20_000)
    set(() => ({ syncTimerId: timerId }))
  },
  stopSync: () => {
    const id = get().syncTimerId
    if (id !== null) {
      window.clearInterval(id)
    }
    set(() => ({ syncTimerId: null }))
  },
  clear: () => {
    get().stopSync()
    try {
      sessionStorage.removeItem(CONFIG_KEY)
      sessionStorage.removeItem(EVENT_TS_KEY)
    } catch {
      /* ignore */
    }
    set(() => ({
      adminConfig: DEFAULT_CONFIG,
      lastEventTs: '',
      lastChangedFields: [],
      loading: false,
      syncError: null,
      hydrated: false,
    }))
  },
}))

