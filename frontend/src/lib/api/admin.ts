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
}

export async function adminGetStats() {
  const { data } = await adminClient.get<AdminWorkspaceStats>('/admin/stats')
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
