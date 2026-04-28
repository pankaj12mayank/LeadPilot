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

export async function adminGetControls() {
  const { data } = await adminClient.get<AdminControls>('/admin/controls')
  return data
}

export async function adminPatchControls(patch: Partial<AdminControls>) {
  const { data } = await adminClient.patch<AdminControls>('/admin/controls', patch)
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

export async function adminCreateUser(email: string, password: string) {
  const { data } = await adminClient.post<{ user: AdminUserRow }>('/admin/users', { email, password })
  return data.user
}

export async function adminBulkDeleteUsers(ids: string[]) {
  const { data } = await adminClient.post<{ deleted: number }>('/admin/users/bulk-delete', { ids })
  return data.deleted
}

export async function adminSetUserActive(userId: string, is_active: boolean) {
  const { data } = await adminClient.patch<{ user: AdminUserRow }>(`/admin/users/${encodeURIComponent(userId)}`, {
    is_active,
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
