import { MessageSquare, Search, Trash2, Mail, MailOpen, Loader2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, getApiErrorMessage } from '@/lib/api/client'
import { cn } from '@/lib/utils/cn'

type Contact = {
  id: string
  name: string
  email: string
  phone?: string
  message: string
  status: 'read' | 'unread'
  created_at: string
}

export function AdminInboxPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const [searchEmail, setSearchEmail] = useState('')
  const [searchMessage, setSearchMessage] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const fetchContacts = useCallback(async () => {
    setBusy(true)
    setErr(null)
    try {
      const params: Record<string, string> = {}
      if (searchEmail.trim()) params.email = searchEmail.trim()
      if (searchMessage.trim()) params.search = searchMessage.trim()
      if (statusFilter) params.status = statusFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo

      const { data } = await api.get<{ contacts: Contact[]; total: number }>('/admin/inbox', { params })
      setContacts(data.contacts || [])
      setTotal(data.total ?? data.contacts.length)
    } catch (e) {
      setErr(getApiErrorMessage(e, 'Could not load messages'))
    } finally {
      setBusy(false)
      setLoading(false)
    }
  }, [searchEmail, searchMessage, statusFilter, dateFrom, dateTo])

  useEffect(() => { void fetchContacts() }, [fetchContacts])

  const handleMarkRead = async (contact: Contact) => {
    const newStatus = contact.status === 'read' ? 'unread' : 'read'
    try {
      await api.patch(`/admin/inbox/${contact.id}`, { status: newStatus })
      setContacts((prev) =>
        prev.map((c) => (c.id === contact.id ? { ...c, status: newStatus } : c)),
      )
    } catch (e) {
      alert(getApiErrorMessage(e, 'Failed to update status'))
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this message?')) return
    try {
      await api.delete(`/admin/inbox/${id}`)
      setContacts((prev) => prev.filter((c) => c.id !== id))
      setTotal((prev) => prev - 1)
    } catch (e) {
      alert(getApiErrorMessage(e, 'Failed to delete message'))
    }
  }

  const clearFilters = () => {
    setSearchEmail('')
    setSearchMessage('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
  }

  const hasFilters = searchEmail || searchMessage || statusFilter || dateFrom || dateTo

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-zinc-900 dark:text-white">Contact Inbox</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          {contacts.filter((c) => c.status === 'unread').length} unread, {total} total message{total !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-white shadow-sm dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-2 border-b border-surface-border px-4 py-3">
          <div className="relative w-44">
            <Mail className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              value={searchEmail}
              onChange={(e) => setSearchEmail(e.target.value)}
              placeholder="Email..."
              className="w-full rounded-lg border border-surface-border bg-transparent py-1.5 pl-8 pr-2.5 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
            />
          </div>
          <div className="relative w-44">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              value={searchMessage}
              onChange={(e) => setSearchMessage(e.target.value)}
              placeholder="Message..."
              className="w-full rounded-lg border border-surface-border bg-transparent py-1.5 pl-8 pr-2.5 text-xs outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 dark:bg-zinc-900"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600"
          >
            <option value="">All</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="w-36 rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="w-36 rounded-lg border border-surface-border bg-white px-2.5 py-1.5 text-xs dark:bg-zinc-900 focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/25 hover:border-zinc-400 dark:hover:border-zinc-600"
          />
          {hasFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-xs text-amber-600 hover:text-amber-700 dark:text-amber-400 font-medium"
            >
              Clear
            </button>
          )}
          <button
            type="button"
            onClick={() => void fetchContacts()}
            disabled={busy}
            className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-50 hover:border-zinc-400 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:border-zinc-600"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
          </div>
        ) : err ? (
          <div className="px-5 py-12 text-center text-amber-600">{err}</div>
        ) : (
          <>
            <div className="divide-y divide-surface-border">
              {contacts.length === 0 ? (
                <div className="px-5 py-12 text-center text-zinc-500 dark:text-zinc-400">
                  {hasFilters ? 'No messages match your filters.' : 'No messages yet.'}
                </div>
              ) : contacts.map((contact) => (
                <div
                  key={contact.id}
                  className={cn(
                    'relative p-5 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50',
                    contact.status === 'unread' && 'bg-amber-50/50 dark:bg-amber-900/10',
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2 min-w-0">
                      <MessageSquare className="h-4 w-4 text-amber-600 flex-shrink-0" />
                      <span className={cn('font-medium', contact.status === 'unread' ? 'text-zinc-900 dark:text-white' : 'text-zinc-600 dark:text-zinc-400')}>
                        {contact.name}
                      </span>
                      <span className="text-sm text-zinc-500 truncate">({contact.email})</span>
                      {contact.phone && (
                        <span className="text-xs text-zinc-400">{contact.phone}</span>
                      )}
                      <span
                        className={cn(
                          'ml-2 inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                          contact.status === 'unread'
                            ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300'
                            : 'bg-zinc-200 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-400',
                        )}
                      >
                        {contact.status}
                      </span>
                    </div>
                    <span className="flex-shrink-0 text-xs text-zinc-400">
                      {new Date(contact.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
                    {contact.message}
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void handleMarkRead(contact)}
                      title={contact.status === 'read' ? 'Mark as unread' : 'Mark as read'}
                      className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
                    >
                      {contact.status === 'read' ? (
                        <MailOpen className="h-4 w-4" />
                      ) : (
                        <Mail className="h-4 w-4 text-amber-600" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(contact.id)}
                      title="Delete"
                      className="rounded-lg p-1.5 text-zinc-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-between border-t border-surface-border px-5 py-3">
              <span className="text-xs text-zinc-500 dark:text-zinc-400">
                Showing {contacts.length} of {total} message{total !== 1 ? 's' : ''}
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}