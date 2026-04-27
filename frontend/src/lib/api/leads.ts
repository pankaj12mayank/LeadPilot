import type { Lead } from '@/types/models'

import { api } from './client'

export type PaginatedLeads = {
  items: Lead[]
  total: number
  page: number
  page_size: number
  pages: number
}

export type FetchLeadsParams = {
  page?: number
  page_size?: number
  search?: string
  status?: string
  tier?: string
  platform?: string
  sort?: 'created_at_desc' | 'created_at_asc' | 'score_desc' | 'name_asc'
}

export async function fetchLeads(params: FetchLeadsParams = {}) {
  const { data } = await api.get<PaginatedLeads>('/leads', { params })
  return data
}

export async function createLead(body: Partial<Lead> & { full_name: string; source_platform: string }) {
  const { data } = await api.post<Lead>('/leads', body)
  return data
}

export async function updateLead(leadId: string, patch: Partial<Lead>) {
  const { data } = await api.put<Lead>(`/leads/${encodeURIComponent(leadId)}`, patch)
  return data
}

export async function patchLead(leadId: string, patch: Partial<Lead>) {
  const { data } = await api.patch<Lead>(`/leads/${encodeURIComponent(leadId)}`, patch)
  return data
}

export async function patchLeadStatus(leadId: string, status: string) {
  const { data } = await api.patch<Lead>(`/leads/${encodeURIComponent(leadId)}/status`, { status })
  return data
}

export async function deleteLead(leadId: string) {
  await api.delete(`/leads/${encodeURIComponent(leadId)}`)
}

export async function bulkDeleteLeads(ids: string[]) {
  const { data } = await api.post<{ deleted: number }>('/leads/bulk-delete', { ids })
  return data
}

export type LeadExportBody = {
  ids?: string[]
  search?: string
  status?: string
  tier?: string
  platform?: string
}

export async function exportLeadsCsv(body: LeadExportBody, filename = 'leads-export.csv') {
  const res = await api.post<Blob>('/leads/export', body, { responseType: 'blob' })
  const url = window.URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

export async function downloadLeadsCsvTemplate(filename = 'leads_import_template.csv') {
  const res = await api.get<Blob>('/leads/csv-template', { responseType: 'blob' })
  const url = window.URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

export type BulkImportResult = { created: number; errors: string[] }

export async function importLeadsCsv(file: File) {
  const body = new FormData()
  body.append('file', file)
  const { data } = await api.post<BulkImportResult>('/leads/bulk-import', body)
  return data
}

export async function getLead(leadId: string) {
  const { data } = await api.get<Lead>(`/leads/${encodeURIComponent(leadId)}`)
  return data
}

export type HistoryEvent = {
  id: number
  lead_id: string | null
  action: string
  detail: unknown
  user_id: string | null
  created_at: string
}

export type StatusHistRow = {
  history_id: number
  lead_id: string
  old_status: string
  new_status: string
  timestamp: string
}

export type EmailHistRow = {
  email_id: string
  lead_id: string
  recipient_email: string
  subject: string
  body: string
  status: string
  sent_at: string
}

export async function getLeadHistory(leadId: string) {
  const { data } = await api.get<HistoryEvent[]>(`/leads/${encodeURIComponent(leadId)}/history`)
  return data
}

export async function getLeadStatusHistory(leadId: string) {
  const { data } = await api.get<StatusHistRow[]>(`/leads/${encodeURIComponent(leadId)}/status-history`)
  return data
}

export async function getLeadEmailHistory(leadId: string) {
  const { data } = await api.get<EmailHistRow[]>(`/leads/${encodeURIComponent(leadId)}/email-history`)
  return data
}
