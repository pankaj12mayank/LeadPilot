import { adminClient } from '@/lib/api/adminClient'
import type { Branding } from '@/store/brandingStore'

export async function adminLogin(email: string, password: string) {
  const { data } = await adminClient.post<{ access_token: string; token_type: string }>('/admin/login', {
    email,
    password,
  })
  return data
}

export type AdminUserRow = {
  id: string
  email: string
  created_at: string
  is_active: boolean
  role?: 'admin' | 'user' | 'buyer'
  plan_id?: 'starter' | 'growth' | 'pro' | 'enterprise'
  last_login_at: string
}

export type AdminWorkspaceStats = {
  registered_users: number
  active_users?: number
  inactive_users?: number
  total_leads: number
  hot_leads: number
  contacted_leads: number
  converted_leads: number
  conversion_rate_percent: number
  total_companies?: number
}

export async function adminGetStats() {
  const { data } = await adminClient.get<AdminWorkspaceStats>('/admin/stats')
  return data
}

export type AdminControls = {
  scoring_weights: {
    role_relevance: number
    company_size: number
    signals: number
    data_completeness: number
    base_factor_mix: number
  }
  targeting_filters: {
    allowed_sources: string[]
    min_company_score: number
    preferred_locations: string[]
    preferred_keywords: string[]
  }
  schedule_timing: {
    daily_auto: string
    friday_heavy: string
    saturday_linkedin: string
    sunday_report: string
  }
}

export type AdminJobLogRow = {
  job_type: string
  run_date: string
  status: 'success' | 'partial_success' | 'failure' | string
  records_processed: number
  errors: string[]
  retry_next_scheduled_run?: boolean
}

export type AdminConfig = {
  targeting: {
    keywords: string[]
    locations: string[]
    industries: string[]
    company_types: string[]
    preferred_locations: string[]
    preferred_keywords: string[]
    min_company_score: number
  }
  sources: {
    job_boards: boolean
    startup_directories: boolean
    local_listings: boolean
    manual_seeds: boolean
    linkedin: boolean
    public_db: boolean
    google_maps: boolean
    indiamart: boolean
    justdial: boolean
    eworldtrade: boolean
    global_sources: boolean
    thomasnet: boolean
    yelp: boolean
    faire: boolean
    allowed_sources: string[]
  }
  scoring_weights: {
    role_weight: number
    signal_weight: number
    data_weight: number
    company_size_weight: number
    base_factor_mix: number
  }
  signals_config: {
    hiring_enabled: boolean
    scaling_enabled: boolean
  }
  scheduler_config: {
    daily_time: string
    weekly_time: string
    linkedin_day: string
    daily_auto: string
    friday_heavy: string
    saturday_linkedin: string
    sunday_report: string
  }
  session_policy: {
    expiry_days: number
  }
  retry_policy: {
    retry_count: number
  }
  task_priority: {
    linkedin: 'high' | 'medium' | 'low'
    scoring: 'high' | 'medium' | 'low'
    enrichment: 'high' | 'medium' | 'low'
    ingestion: 'high' | 'medium' | 'low'
  }
  ai_control: {
    ollama_enabled: boolean
    api_enabled: boolean
  }
  scoring_control: {
    role: number
    signals: number
    ai_score: number
  }
  safety_control: {
    delay_seconds: number
    batch_size: number
    retry_count: number
    pagination_limit: number
  }
  queue_priority: {
    linkedin: 'high' | 'medium' | 'low'
    ai: 'high' | 'medium' | 'low'
    others: 'high' | 'medium' | 'low'
  }
  source_registry: Array<{
    source_name: string
    source_type: 'job_board' | 'directory' | 'local' | 'manual' | 'marketplace'
    enabled: boolean
    input_type: 'url' | 'keyword' | 'file' | 'csv'
    adapter_function: string
  }>
  worker_config: {
    worker_count: number
  }
  plan_channel_access: Record<
    'starter' | 'growth' | 'pro' | 'enterprise',
    {
      channels: string[]
      lead_limit: number
    }
  >
}

export async function adminGetControls() {
  const { data } = await adminClient.get<AdminControls>('/admin/controls')
  return data
}

export async function adminPatchControls(patch: Partial<AdminControls>) {
  const { data } = await adminClient.patch<AdminControls>('/admin/controls', patch)
  return data
}

export async function adminGetConfig() {
  const { data } = await adminClient.get<AdminConfig>('/admin/config')
  return data
}

export async function adminPatchConfig(patch: Partial<AdminConfig>) {
  const { data } = await adminClient.patch<AdminConfig>('/admin/config', patch)
  return data
}

export async function adminGetJobLogs(limit = 50) {
  const { data } = await adminClient.get<{ count: number; items: AdminJobLogRow[] }>('/admin/job-logs', { params: { limit } })
  return data
}

export async function adminListUsers() {
  const { data } = await adminClient.get<{ users: AdminUserRow[] }>('/admin/users')
  return data.users
}

export async function adminCreateUser(
  email: string,
  password: string,
  role: 'admin' | 'user' | 'buyer' = 'user',
  plan_id: 'starter' | 'growth' | 'pro' | 'enterprise' = 'starter',
) {
  const { data } = await adminClient.post<{ user: AdminUserRow }>('/admin/users', {
    email,
    password,
    role,
    plan_id: role === 'admin' ? 'enterprise' : plan_id,
  })
  return data.user
}

export async function adminBulkDeleteUsers(ids: string[]) {
  const { data } = await adminClient.post<{ deleted: number }>('/admin/users/bulk-delete', { ids })
  return data.deleted
}

export async function adminSetUserActive(
  userId: string,
  is_active: boolean,
  role?: 'admin' | 'user' | 'buyer',
  plan_id?: 'starter' | 'growth' | 'pro' | 'enterprise',
) {
  const { data } = await adminClient.patch<{ user: AdminUserRow }>(`/admin/users/${encodeURIComponent(userId)}`, {
    is_active,
    role,
    plan_id,
  })
  return data.user
}

export async function adminSetUserPassword(userId: string, password: string) {
  await adminClient.post(`/admin/users/${encodeURIComponent(userId)}/password`, { password })
}

export async function adminGetBranding() {
  const { data } = await adminClient.get<Branding>('/admin/branding')
  return data
}

export async function adminPatchBranding(patch: Partial<Branding>) {
  const { data } = await adminClient.patch<Branding>('/admin/branding', patch)
  return data
}

export async function adminUploadLogo(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await adminClient.post<Branding>('/admin/branding/upload-logo', fd)
  return data
}

export async function adminUploadFavicon(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await adminClient.post<Branding>('/admin/branding/upload-favicon', fd)
  return data
}

export async function adminClearLogo() {
  const { data } = await adminClient.post<Branding>('/admin/branding/clear-logo')
  return data
}

export async function adminClearFavicon() {
  const { data } = await adminClient.post<Branding>('/admin/branding/clear-favicon')
  return data
}
