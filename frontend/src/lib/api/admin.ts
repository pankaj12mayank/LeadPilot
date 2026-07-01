import { api } from '@/lib/api/client'

export type AdminConfig = any
export type AdminJobLogRow = any
export type AdminWorkspaceStats = any
export type AdminControls = any
export type AdminUserRow = any
export type AdminProfile = any

export async function adminGetProfile(): Promise<any> {
  const { data } = await api.get('/admin/profile')
  return data
}

export async function adminUpdateProfile(body: {
  name?: string
  current_password?: string
  new_password?: string
}): Promise<any> {
  const { data } = await api.patch('/admin/profile', body)
  return data
}

export async function adminLogin(email: string, password: string): Promise<any> {
  const { data } = await api.post('/admin/login', { email, password })
  return data
}

export async function adminGetDashboard(): Promise<any> {
  const { data } = await api.get('/admin/overview')
  return data
}

export async function adminGetStats(): Promise<any> {
  const { data } = await api.get('/admin/overview')
  return data
}

export async function adminGetUsers(params?: any): Promise<any> {
  const { data } = await api.get('/admin/users', { params })
  return data
}

export async function adminListUsers(params?: any): Promise<any> {
  return adminGetUsers(params)
}

export async function adminCreateUser(body: any): Promise<any> {
  const { data } = await api.post('/admin/users', body)
  return data
}

export async function adminUpdateUser(id: string, body: any): Promise<any> {
  const { data } = await api.patch(`/admin/users/${id}`, body)
  return data
}

export async function adminDeleteUser(id: string): Promise<void> {
  await api.delete(`/admin/users/${id}`)
}

export async function adminSetUserActive(id: string, is_active: boolean): Promise<any> {
  const { data } = await api.patch(`/admin/users/${id}`, { is_active })
  return data
}

export async function adminSetUserPassword(id: string, password: string): Promise<any> {
  const { data } = await api.patch(`/admin/users/${id}/password`, { password })
  return data
}

export async function adminBulkDeleteUsers(ids: string[]): Promise<any> {
  const { data } = await api.post('/admin/users/bulk-delete', { ids })
  return data
}

export async function adminGetBranding(): Promise<any> {
  const { data } = await api.get('/admin/branding')
  return data
}

export async function adminPatchBranding(data: any): Promise<any> {
  const { data: res } = await api.patch('/admin/branding', data)
  return res
}

export async function adminUploadLogo(file: Blob): Promise<any> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/admin/branding/logo', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}

export async function adminUploadFavicon(file: Blob): Promise<any> {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/admin/branding/favicon', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}

export async function adminClearLogo(): Promise<any> {
  const { data } = await api.delete('/admin/branding/logo')
  return data
}

export async function adminClearFavicon(): Promise<any> {
  const { data } = await api.delete('/admin/branding/favicon')
  return data
}

export async function adminGetJobLogs(params?: any): Promise<any> {
  const { data } = await api.get('/admin/job-logs', { params })
  return data
}

export async function adminGetControls(): Promise<any> {
  const { data } = await api.get('/admin/scoring')
  return data
}

export async function adminPatchControls(data: any): Promise<any> {
  const { data: res } = await api.patch('/admin/scoring', data)
  return res
}

export async function adminGetConfig(): Promise<any> {
  const { data } = await api.get('/admin/sources')
  return data
}

export async function adminPatchConfig(data: any): Promise<any> {
  const { data: res } = await api.patch('/admin/sources', data)
  return res
}

export async function adminGetNewsletter(params?: any): Promise<any> {
  const { data } = await api.get('/admin/newsletter', { params })
  return data
}

export async function adminDeleteSubscriber(id: string): Promise<any> {
  const { data } = await api.delete(`/admin/newsletter/${id}`)
  return data
}

export async function adminGetInbox(params?: any): Promise<any> {
  const { data } = await api.get('/admin/inbox', { params })
  return data
}

export async function adminUpdateInboxStatus(id: string, status: string): Promise<any> {
  const { data } = await api.patch(`/admin/inbox/${id}`, { status })
  return data
}