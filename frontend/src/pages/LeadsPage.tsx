import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type PaginationState,
  type RowSelectionState,
} from '@tanstack/react-table'
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileDown,
  Loader2,
  Search,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { useShallow } from 'zustand/react/shallow'

import { Badge, statusBadgeClass } from '@/components/ui/Badge'
import { FilterSelect } from '@/components/ui/FilterSelect'
import { Modal } from '@/components/ui/Modal'
import {
  bulkDeleteLeads,
  downloadLeadsCsvTemplate,
  exportLeadsCsv,
  fetchLeads,
  importLeadsCsv,
  getLead,
  getLeadEmailHistory,
  getLeadHistory,
  getLeadStatusHistory,
  patchLeadStatus,
  updateLead,
  type EmailHistRow,
  type HistoryEvent,
  type StatusHistRow,
} from '@/lib/api/leads'
import { getApiErrorMessage } from '@/lib/api/client'
import { generateLeadMessage as genMsg } from '@/lib/api/messages'
import { leadStatusLabel } from '@/lib/copy/appCopy'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { cn } from '@/lib/utils/cn'
import { useLeadsUiStore } from '@/store/leadsUiStore'
import type { Lead } from '@/types/models'

const LEAD_STATUSES = [
  'new',
  'request_sent',
  'message_sent',
  'replied_got',
  'on_discussion',
  'interested',
  'deal',
  'close',
  'not_interested',
] as const

const PIPELINE_STATUS_SELECT_OPTIONS = LEAD_STATUSES.map((s) => ({
  value: s,
  label: leadStatusLabel(s),
}))

const columnHelper = createColumnHelper<Lead>()

function tierVariant(tier: string): 'hot' | 'warm' | 'cold' | 'muted' {
  const t = (tier || '').toLowerCase()
  if (t === 'hot') return 'hot'
  if (t === 'warm') return 'warm'
  if (t === 'cold') return 'cold'
  return 'muted'
}

function tierLabel(tier: string) {
  const t = (tier || '').toLowerCase()
  if (t === 'hot' || t === 'warm' || t === 'cold') return t.charAt(0).toUpperCase() + t.slice(1)
  return tier || '—'
}

function scoreTone(score: number) {
  if (score >= 80) return 'text-emerald-700 dark:text-emerald-300'
  if (score >= 50) return 'text-amber-700 dark:text-amber-200'
  return 'text-slate-600 dark:text-slate-300'
}

function fmtShort(iso: string) {
  if (!iso) return '—'
  return iso.length >= 10 ? iso.slice(0, 16).replace('T', ' ') : iso
}

function toLocalInput(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocalInput(s: string) {
  if (!s) return ''
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return ''
  return d.toISOString().slice(0, 19) + '+00:00'
}

/** Short heading for modals when ``full_name`` contains scraped LinkedIn noise. */
function leadModalTitle(fullName: string): string {
  const raw = (fullName || '').trim()
  if (!raw) return 'Contact details'
  const first = raw.split(/\s+[•·]\s*/)[0]?.trim() || raw
  const cleaned = first.split(/\s{2,}/)[0]?.trim() || first
  return cleaned.length > 72 ? `${cleaned.slice(0, 70)}…` : cleaned || 'Contact details'
}

/** Same shortening as the detail modal title; table uses ``—`` when empty. */
function contactNameTableDisplay(fullName: string): string {
  const raw = (fullName || '').trim()
  if (!raw) return '—'
  return leadModalTitle(raw)
}

function ContactNameCell({
  lead,
  patchLocal,
}: {
  lead: Lead
  patchLocal: (id: string, patch: Partial<Lead>) => void
}) {
  const [editing, setEditing] = useState(false)
  const full = lead.full_name || ''

  if (editing) {
    return (
      <input
        autoFocus
        defaultValue={full}
        title={full}
        aria-label="Edit contact name"
        className="w-full min-w-[8rem] max-w-[min(100vw,22rem)] rounded-lg border border-amber-500/40 bg-field/90 px-2 py-1 text-sm font-medium text-ink shadow-sm focus:outline-none focus:ring-1 focus:ring-amber-500/30 dark:bg-zinc-900/80"
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            ;(e.currentTarget as HTMLInputElement).value = full
            e.currentTarget.blur()
          }
        }}
        onBlur={async (e) => {
          const v = e.currentTarget.value.trim()
          setEditing(false)
          if (!v || v === full) return
          try {
            const u = await updateLead(lead.id, { full_name: v })
            patchLocal(lead.id, u)
          } catch {
            e.currentTarget.value = full
          }
        }}
      />
    )
  }

  return (
    <button
      type="button"
      title={full || 'Click to edit'}
      className="max-w-[min(100%,12rem)] truncate rounded-lg border border-transparent px-1 py-1 text-left text-sm font-medium text-ink hover:border-surface-border hover:bg-field/50 focus-visible:border-amber-500/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-amber-500/25 sm:max-w-[16rem] lg:max-w-[18rem]"
      onClick={() => setEditing(true)}
    >
      {contactNameTableDisplay(full)}
    </button>
  )
}

type TimelineRow = { at: string; kind: string; title: string; body: string }

function buildOutreachTimeline(
  h: HistoryEvent[],
  sh: StatusHistRow[],
  em: EmailHistRow[],
): TimelineRow[] {
  const rows: TimelineRow[] = []
  h.forEach((e) => {
    rows.push({
      at: e.created_at,
      kind: 'activity',
      title: e.action,
      body: e.detail ? JSON.stringify(e.detail).slice(0, 240) : '',
    })
  })
  sh.forEach((e) => {
    rows.push({
      at: e.timestamp,
      kind: 'status',
      title: `Pipeline status updated from ${leadStatusLabel(e.old_status)} to ${leadStatusLabel(e.new_status)}`,
      body: '',
    })
  })
  em.forEach((e) => {
    rows.push({
      at: e.sent_at,
      kind: 'email',
      title: `Email (${e.status})`,
      body: e.subject || '',
    })
  })
  rows.sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0))
  return rows
}

export function LeadsPage() {
  const [rows, setRows] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [exportBusy, setExportBusy] = useState(false)
  const [importBusy, setImportBusy] = useState(false)
  const importFileRef = useRef<HTMLInputElement>(null)
  const [modalLead, setModalLead] = useState<Lead | null>(null)
  const [timeline, setTimeline] = useState<TimelineRow[]>([])
  const [notesDraft, setNotesDraft] = useState('')
  const [lastContactLocal, setLastContactLocal] = useState('')
  const [followUpLocal, setFollowUpLocal] = useState('')
  const [titleDraft, setTitleDraft] = useState('')
  const [companyDraft, setCompanyDraft] = useState('')
  const [emailDraft, setEmailDraft] = useState('')
  const [websiteDraft, setWebsiteDraft] = useState('')
  const [linkedinDraft, setLinkedinDraft] = useState('')
  const [companySizeDraft, setCompanySizeDraft] = useState('')
  const [industryDraft, setIndustryDraft] = useState('')
  const [locationDraft, setLocationDraft] = useState('')
  const [phoneDraft, setPhoneDraft] = useState('')
  const [messageDraft, setMessageDraft] = useState('')
  const [saveBusy, setSaveBusy] = useState(false)
  /** Lead id currently generating message (only that row's button disabled). */
  const [genBusyLeadId, setGenBusyLeadId] = useState<string | null>(null)
  const [genErr, setGenErr] = useState<string | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({})
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 25 })

  const { filters, setSearch, setTier, setStatus, resetFilters } = useLeadsUiStore(
    useShallow((s) => ({
      filters: s.filters,
      setSearch: s.setSearch,
      setTier: s.setTier,
      setStatus: s.setStatus,
      resetFilters: s.resetFilters,
    })),
  )

  const debouncedSearch = useDebouncedValue(filters.search, 400)

  const tierFilterOptions = useMemo(
    () => [
      { value: '', label: 'All tiers' },
      { value: 'hot', label: 'Hot' },
      { value: 'warm', label: 'Warm' },
      { value: 'cold', label: 'Cold' },
    ],
    [],
  )

  const statusFilterOptions = useMemo(
    () => [{ value: '', label: 'All statuses' }, ...PIPELINE_STATUS_SELECT_OPTIONS],
    [],
  )

  const pageSizeOptions = useMemo(
    () => [10, 25, 50, 100, 200].map((n) => ({ value: String(n), label: `${n} / page` })),
    [],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setLoadErr(null)
    try {
      const r = await fetchLeads({
        page: pagination.pageIndex + 1,
        page_size: pagination.pageSize,
        search: debouncedSearch.trim() || undefined,
        status: filters.status || undefined,
        tier: filters.tier || undefined,
        sort: 'created_at_desc',
      })
      setRows(r.items)
      setTotal(r.total)
      setPages(r.pages)
    } catch {
      setLoadErr('Unable to load leads. Please refresh the page and try again.')
    } finally {
      setLoading(false)
    }
  }, [pagination.pageIndex, pagination.pageSize, debouncedSearch, filters.status, filters.tier])

  useEffect(() => {
    void load()
  }, [load])

  const activeFilterCount = useMemo(() => {
    let n = 0
    if (filters.status) n += 1
    if (filters.tier) n += 1
    if (filters.search.trim()) n += 1
    return n
  }, [filters.search, filters.status, filters.tier])

  useEffect(() => {
    setPagination((p) => ({ ...p, pageIndex: 0 }))
  }, [debouncedSearch, filters.status, filters.tier])

  const openModal = useCallback(async (lead: Lead) => {
    setModalLead(lead)
    setNotesDraft(lead.notes || '')
    setLastContactLocal(toLocalInput(lead.last_contacted_at || ''))
    setFollowUpLocal(toLocalInput(lead.follow_up_reminder_at || ''))
    setTitleDraft(lead.title || '')
    setCompanyDraft(lead.company_name || '')
    setEmailDraft(lead.email || '')
    setWebsiteDraft(lead.company_website || '')
    setLinkedinDraft(lead.linkedin_url || '')
    setCompanySizeDraft(lead.company_size || '')
    setIndustryDraft(lead.industry || '')
    setLocationDraft(lead.location || '')
    setPhoneDraft(lead.phone || '')
    setMessageDraft(lead.personalized_message || '')
    setGenErr(null)
    try {
      const [h, sh, em] = await Promise.all([
        getLeadHistory(lead.id),
        getLeadStatusHistory(lead.id),
        getLeadEmailHistory(lead.id),
      ])
      setTimeline(buildOutreachTimeline(h, sh, em))
    } catch {
      setTimeline([])
    }
  }, [])

  const patchLocal = useCallback((id: string, patch: Partial<Lead>) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)))
  }, [])

  const onStatusChange = useCallback(
    async (lead: Lead, status: string) => {
      const prev = lead.status
      patchLocal(lead.id, { status })
      try {
        const updated = await patchLeadStatus(lead.id, status)
        patchLocal(lead.id, updated)
        setModalLead((m) => (m && m.id === lead.id ? { ...m, ...updated } : m))
      } catch {
        patchLocal(lead.id, { status: prev })
      }
    },
    [patchLocal],
  )

  const columns = useMemo(
    () => [
      columnHelper.display({
        id: 'select',
        header: ({ table }) => (
          <input
            type="checkbox"
            className="rounded border-surface-border text-ink accent-amber-500"
            checked={table.getIsAllPageRowsSelected()}
            ref={(el) => {
              if (el) el.indeterminate = table.getIsSomePageRowsSelected()
            }}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            aria-label="Select all on page"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            className="rounded border-surface-border text-ink accent-amber-500"
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
            aria-label="Select row"
          />
        ),
        size: 36,
      }),
      columnHelper.accessor('full_name', {
        header: 'Contact name',
        cell: ({ row }) => (
          <ContactNameCell key={row.original.id + row.original.updated_at} lead={row.original} patchLocal={patchLocal} />
        ),
      }),
      columnHelper.accessor('company_name', {
        header: 'Organization',
        cell: ({ row }) => (
          <input
            defaultValue={row.original.company_name}
            className="w-full min-w-[100px] rounded-lg border border-transparent bg-transparent px-1 py-0.5 text-sm text-ink-muted hover:border-surface-border focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/20"
            onBlur={async (e) => {
              const v = e.target.value.trim()
              if (v === (row.original.company_name || '')) return
              try {
                const u = await updateLead(row.original.id, { company_name: v })
                patchLocal(row.original.id, u)
              } catch {
                e.target.value = row.original.company_name
              }
            }}
          />
        ),
      }),
      columnHelper.accessor('title', {
        header: 'Role',
        cell: (i) => (
          <span className="max-w-[10rem] truncate text-sm text-ink-muted" title={String(i.getValue() || '')}>
            {(i.getValue() as string) || '—'}
          </span>
        ),
      }),
      columnHelper.accessor('agency_type', {
        header: 'Agency',
        cell: (i) => (
          <span className="max-w-[5rem] truncate text-xs text-ink-muted" title={String(i.getValue() || '')}>
            {(i.getValue() as string) || '—'}
          </span>
        ),
      }),
      columnHelper.accessor('problem_seen', {
        header: 'Problem',
        cell: (i) => {
          const t = String(i.getValue() || '')
          return (
            <span className="max-w-[8rem] truncate text-xs text-ink-subtle" title={t}>
              {t || '—'}
            </span>
          )
        },
      }),
      columnHelper.accessor('solution_text', {
        header: 'Solution',
        cell: (i) => {
          const t = String(i.getValue() || '')
          return (
            <span className="max-w-[9rem] truncate text-xs text-ink-subtle" title={t}>
              {t || '—'}
            </span>
          )
        },
      }),
      columnHelper.accessor('connection_sent', {
        header: 'Conn. sent',
        cell: (i) => <span className="text-xs text-ink-subtle">{String(i.getValue() || '') || '—'}</span>,
      }),
      columnHelper.accessor('replied_yn', {
        header: 'Replied',
        cell: (i) => <span className="tabular-nums text-xs font-medium text-ink">{String(i.getValue() || 'N')}</span>,
      }),
      columnHelper.accessor('source_platform', {
        header: 'Lead source',
        cell: (i) => (
          <Badge variant="platform" className="text-[10px]">
            {i.getValue() || '—'}
          </Badge>
        ),
      }),
      columnHelper.accessor('score', {
        header: 'Lead score',
        cell: (i) => {
          const v = Number(i.getValue() ?? 0)
          return <span className={cn('tabular-nums text-sm font-semibold', scoreTone(v))}>{Math.round(v)}</span>
        },
      }),
      columnHelper.accessor('tier', {
        header: 'Qualification tier',
        cell: (i) => {
          const t = String(i.getValue() || '')
          return <Badge variant={tierVariant(t)}>{tierLabel(t)}</Badge>
        },
      }),
      columnHelper.accessor('status', {
        header: 'Pipeline status',
        cell: ({ row }) => {
          const st = row.original.status || 'new'
          return (
            <FilterSelect
              size="sm"
              className="w-full min-w-[10rem] max-w-[14rem]"
              buttonClassName={cn(
                'rounded-full border font-medium shadow-none ring-0 hover:ring-1 hover:ring-amber-500/20',
                statusBadgeClass(st),
              )}
              options={PIPELINE_STATUS_SELECT_OPTIONS}
              value={st}
              onChange={(v) => void onStatusChange(row.original, v)}
              aria-label="Pipeline status — click to change"
            />
          )
        },
      }),
      columnHelper.accessor('last_contacted_at', {
        header: 'Last contact',
        cell: (i) => <span className="text-xs text-ink-subtle">{fmtShort(String(i.getValue() || ''))}</span>,
      }),
      columnHelper.accessor('follow_up_reminder_at', {
        header: 'Next follow-up',
        cell: (i) => <span className="text-xs text-ink-subtle">{fmtShort(String(i.getValue() || ''))}</span>,
      }),
      columnHelper.display({
        id: 'actions',
        header: 'Actions',
        cell: ({ row }) => (
          <div className="flex w-[min(100%,220px)] min-w-0 flex-col items-stretch gap-2 sm:ml-auto sm:w-auto sm:min-w-[200px] sm:items-end">
            <button
              type="button"
              onClick={() => void openModal(row.original)}
              className="whitespace-nowrap rounded-lg border border-surface-border bg-field/90 px-3 py-2 text-left text-xs font-medium text-ink-muted transition hover:border-amber-500/30 hover:text-ink dark:bg-zinc-900/50 sm:text-center"
            >
              View details
            </button>
            <button
              type="button"
              onClick={async () => {
                setGenErr(null)
                const id = row.original.id
                setGenBusyLeadId(id)
                try {
                  const res = await genMsg(id)
                  patchLocal(id, {
                    personalized_message: res.message,
                  })
                  toast.success('Draft message saved to the lead (pipeline status unchanged).')
                } catch (e) {
                  const msg = getApiErrorMessage(e, 'Could not generate message')
                  setGenErr(msg)
                  toast.error(msg)
                } finally {
                  setGenBusyLeadId((cur) => (cur === id ? null : cur))
                  void load()
                }
              }}
              disabled={genBusyLeadId === row.original.id}
              title="Generate a draft outreach message (does not send email)"
              aria-label="Generate outreach message"
              className="inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-lg bg-gradient-to-r from-amber-600 to-amber-700 px-3 py-2 text-xs font-semibold text-white shadow-sm ring-1 ring-amber-500/25 transition hover:from-amber-500 hover:to-amber-600 disabled:opacity-50 dark:from-amber-500 dark:to-amber-600"
            >
              <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden />
              Generate message
            </button>
          </div>
        ),
      }),
    ],
    [genBusyLeadId, load, onStatusChange, openModal, patchLocal],
  )

  const table = useReactTable({
    data: rows,
    columns,
    state: { pagination, rowSelection },
    onPaginationChange: setPagination,
    onRowSelectionChange: setRowSelection,
    manualPagination: true,
    pageCount: Math.max(1, pages),
    enableRowSelection: true,
    getRowId: (r) => r.id,
    getCoreRowModel: getCoreRowModel(),
  })

  const selectedIds = useMemo(
    () => Object.keys(rowSelection).filter((id) => rowSelection[id]),
    [rowSelection],
  )

  async function onBulkDelete() {
    if (!selectedIds.length) return
    if (
      !window.confirm(
        `Remove ${selectedIds.length} selected leads from your workspace? This action cannot be undone.`,
      )
    )
      return
    try {
      const r = await bulkDeleteLeads(selectedIds)
      setRowSelection({})
      await load()
      toast.success(r.deleted ? `Deleted ${r.deleted} lead(s)` : 'Leads removed')
    } catch {
      toast.error('Bulk delete failed')
    }
  }

  async function onExportFiltered() {
    setExportBusy(true)
    try {
      await exportLeadsCsv({
        search: filters.search.trim() || undefined,
        status: filters.status || undefined,
        tier: filters.tier || undefined,
      })
      toast.success('Export started — check your downloads')
    } catch {
      toast.error('Export failed')
    } finally {
      setExportBusy(false)
    }
  }

  async function onExportSelected() {
    if (!selectedIds.length) return
    setExportBusy(true)
    try {
      await exportLeadsCsv({ ids: selectedIds })
      toast.success('Export started — check your downloads')
    } catch {
      toast.error('Export failed')
    } finally {
      setExportBusy(false)
    }
  }

  async function onDownloadTemplate() {
    setImportBusy(true)
    try {
      await downloadLeadsCsvTemplate()
      toast.success('Sample CSV template downloaded (same headers as export)')
    } catch {
      toast.error('Could not download template')
    } finally {
      setImportBusy(false)
    }
  }

  function onOpenImport() {
    importFileRef.current?.click()
  }

  async function onImportFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setImportBusy(true)
    try {
      const r = await importLeadsCsv(file)
      if (r.errors?.length) {
        const msg =
          r.errors.length <= 4 ? r.errors.join(' · ') : `${r.errors.length} notes (first: ${r.errors[0]})`
        if (r.created) toast.message(msg, { description: 'Some rows were skipped' })
        else toast.warning(msg)
      }
      if (r.created) {
        toast.success(`Imported ${r.created} lead(s)`)
        await load()
        setRowSelection({})
      } else if (!r.errors?.length) {
        toast.message('No rows imported (file was empty or no valid rows)')
      }
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Import failed'))
    } finally {
      setImportBusy(false)
    }
  }

  async function saveModalMeta() {
    if (!modalLead) return
    setSaveBusy(true)
    try {
      const u = await updateLead(modalLead.id, {
        title: titleDraft.trim(),
        company_name: companyDraft.trim(),
        email: emailDraft.trim(),
        company_website: websiteDraft.trim(),
        linkedin_url: linkedinDraft.trim(),
        company_size: companySizeDraft.trim(),
        industry: industryDraft.trim(),
        location: locationDraft.trim(),
        phone: phoneDraft.trim(),
        personalized_message: messageDraft,
        notes: notesDraft,
        last_contacted_at: lastContactLocal ? fromLocalInput(lastContactLocal) : '',
        follow_up_reminder_at: followUpLocal ? fromLocalInput(followUpLocal) : '',
      })
      patchLocal(modalLead.id, u)
      setModalLead(u)
      toast.success('Lead details saved')
    } catch {
      toast.error('Could not save lead details')
    } finally {
      setSaveBusy(false)
    }
  }

  if (loading && rows.length === 0) {
    return (
      <div className="mx-auto max-w-[1680px] space-y-6">
        <div className="skeleton-shimmer h-14 max-w-xl rounded-2xl" />
        <div className="flex flex-wrap gap-2">
          <div className="skeleton-shimmer h-11 w-28 rounded-xl" />
          <div className="skeleton-shimmer h-11 w-28 rounded-xl" />
          <div className="skeleton-shimmer h-11 w-28 rounded-xl" />
        </div>
        <div className="skeleton-shimmer h-[420px] w-full rounded-2xl" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1680px] space-y-6">
      {loadErr ? (
        <div className="rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">
          {loadErr}
        </div>
      ) : null}
      {genErr ? (
        <div className="rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-800 dark:bg-red-950/40 dark:text-red-200">
          {genErr}
        </div>
      ) : null}

      <section className="rounded-2xl border border-surface-border bg-premium-card-light p-4 shadow-card dark:bg-premium-card-dark sm:p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-sm font-semibold text-ink">Find leads</h2>
            <p className="text-xs text-ink-muted">
              Search runs across the full database. Filters apply together.{' '}
              {activeFilterCount > 0 ? (
                <span className="text-amber-800 dark:text-amber-200">
                  {activeFilterCount} active filter{activeFilterCount === 1 ? '' : 's'}
                </span>
              ) : (
                <span>No filters applied.</span>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={resetFilters}
            disabled={activeFilterCount === 0}
            className="shrink-0 self-start rounded-xl border border-surface-border px-3 py-2 text-xs font-semibold text-ink-muted transition hover:border-amber-500/25 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40 sm:self-auto"
          >
            Reset all
          </button>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-12 lg:items-end">
          <div className="space-y-1.5 lg:col-span-5">
            <label htmlFor="leads-search" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Search
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-subtle" />
              <input
                id="leads-search"
                value={filters.search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Name, company, email, title…"
                className="field-input rounded-xl py-3 pl-10 pr-11"
                autoComplete="off"
              />
              {filters.search.trim() !== debouncedSearch.trim() ? (
                <span
                  className="pointer-events-none absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1 text-[11px] font-medium text-ink-subtle"
                  aria-live="polite"
                >
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  Typing…
                </span>
              ) : loading && rows.length > 0 ? (
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2" aria-hidden>
                  <Loader2 className="h-4 w-4 animate-spin text-ink-subtle" />
                </span>
              ) : null}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:col-span-7">
            <div className="space-y-1.5">
              <label htmlFor="leads-tier" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Tier
              </label>
              <FilterSelect
                id="leads-tier"
                options={tierFilterOptions}
                value={filters.tier}
                onChange={setTier}
                placeholder="All tiers"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="leads-status" className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Pipeline status
              </label>
              <FilterSelect
                id="leads-status"
                options={statusFilterOptions}
                value={filters.status}
                onChange={setStatus}
                placeholder="All statuses"
              />
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 border-t border-surface-border pt-4">
          <input
            ref={importFileRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => void onImportFilePicked(e)}
            aria-label="Import leads from CSV"
          />
          <button
            type="button"
            onClick={() => void onDownloadTemplate()}
            disabled={importBusy}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-field/50 px-4 py-2.5 text-sm font-medium text-ink-muted transition hover:border-amber-500/20 hover:text-ink disabled:opacity-50"
          >
            <FileDown className="h-4 w-4" aria-hidden />
            CSV sample
          </button>
          <button
            type="button"
            onClick={onOpenImport}
            disabled={importBusy}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border px-4 py-2.5 text-sm font-medium text-ink-muted transition hover:border-emerald-500/30 hover:text-ink disabled:opacity-50"
          >
            {importBusy ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Upload className="h-4 w-4" aria-hidden />
            )}
            Import CSV
          </button>
          <button
            type="button"
            onClick={() => void onExportFiltered()}
            disabled={exportBusy}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-2.5 text-sm font-semibold text-amber-900 shadow-sm transition hover:border-amber-500/50 hover:shadow-glow-gold disabled:opacity-50 dark:text-amber-200"
          >
            <Download className="h-4 w-4" />
            Export filtered
          </button>
          <button
            type="button"
            disabled={!selectedIds.length || exportBusy}
            onClick={() => void onExportSelected()}
            className="rounded-xl border border-surface-border px-4 py-2.5 text-sm text-ink-muted transition hover:border-amber-500/20 hover:text-ink disabled:opacity-40"
          >
            Export selected
          </button>
          <button
            type="button"
            disabled={!selectedIds.length}
            onClick={() => void onBulkDelete()}
            className="inline-flex items-center gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-800 transition hover:bg-red-500/15 disabled:opacity-40 dark:text-red-200"
          >
            <Trash2 className="h-4 w-4" />
            Remove selected
          </button>
        </div>
      </section>

      <div className="overflow-hidden rounded-2xl border border-surface-border bg-premium-card-light shadow-card dark:bg-premium-card-dark">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] border-collapse text-left text-sm font-sans">
            <thead className="sticky top-0 z-20 border-b border-surface-border bg-surface-raised/95 backdrop-blur-md dark:bg-zinc-950/90">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((h) => (
                    <th key={h.id} className="px-3 py-3 text-xs font-semibold uppercase tracking-wider text-ink-muted">
                      {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td colSpan={12} className="px-4 py-16 text-center">
                    <p className="text-sm font-medium text-ink-muted">No leads found</p>
                    <p className="mt-1 text-xs text-ink-subtle">
                      Start by running a new lead search to populate your workspace, or clear filters to widen results.
                    </p>
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row, idx) => (
                  <tr
                    key={row.id}
                    className={cn(
                      'border-b border-surface-border/80 transition-colors duration-150 hover:bg-amber-500/[0.06] dark:hover:bg-amber-400/[0.05]',
                      idx % 2 === 1 ? 'bg-field/40 dark:bg-white/[0.02]' : '',
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-3 py-2.5 align-middle text-ink-muted">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-col gap-3 border-t border-surface-border bg-surface-raised/30 px-4 py-3 text-xs text-ink-subtle sm:flex-row sm:items-center sm:justify-between">
          <div>
            Showing {rows.length ? pagination.pageIndex * pagination.pageSize + 1 : 0}–
            {pagination.pageIndex * pagination.pageSize + rows.length} of {total}
          </div>
          <div className="flex items-center gap-2">
            <FilterSelect
              size="sm"
              className="w-[118px]"
              options={pageSizeOptions}
              value={String(pagination.pageSize)}
              onChange={(v) => setPagination({ pageIndex: 0, pageSize: Number(v) || 25 })}
              aria-label="Rows per page"
            />
            <button
              type="button"
              className="rounded-lg border border-surface-border p-1.5 text-ink-muted transition hover:border-amber-500/25 hover:text-ink disabled:opacity-30"
              disabled={pagination.pageIndex <= 0}
              onClick={() => setPagination((p) => ({ ...p, pageIndex: Math.max(0, p.pageIndex - 1) }))}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="tabular-nums text-ink-muted">
              Page {pagination.pageIndex + 1} / {Math.max(1, pages)}
            </span>
            <button
              type="button"
              className="rounded-lg border border-surface-border p-1.5 text-ink-muted transition hover:border-amber-500/25 hover:text-ink disabled:opacity-30"
              disabled={pagination.pageIndex + 1 >= pages}
              onClick={() => setPagination((p) => ({ ...p, pageIndex: p.pageIndex + 1 }))}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <Modal
        open={!!modalLead}
        title={modalLead ? leadModalTitle(modalLead.full_name) : 'Contact details'}
        titleHint={modalLead?.full_name}
        onClose={() => setModalLead(null)}
      >
        {modalLead ? (
          <div className="space-y-6 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={tierVariant(modalLead.tier)}>Qualification tier: {tierLabel(modalLead.tier)}</Badge>
              <span className={cn('rounded-full border border-surface-border px-2 py-0.5 text-xs tabular-nums', scoreTone(Number(modalLead.score)))}>
                Lead score {Math.round(Number(modalLead.score ?? 0))}
              </span>
              <FilterSelect
                size="sm"
                className="min-w-[200px]"
                buttonClassName={cn(
                  'rounded-full border font-medium shadow-none ring-0 hover:ring-1 hover:ring-amber-500/20',
                  statusBadgeClass(modalLead.status || 'new'),
                )}
                options={PIPELINE_STATUS_SELECT_OPTIONS}
                value={modalLead.status || 'new'}
                onChange={(v) => void onStatusChange(modalLead, v)}
                aria-label="Pipeline status — click to change"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-surface-border bg-field/60 px-3 py-2 dark:bg-zinc-900/40">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Lead source</div>
                <div className="mt-1 break-all text-ink">{modalLead.source_platform || '—'}</div>
              </div>
              <div className="rounded-xl border border-surface-border bg-field/60 px-3 py-2 dark:bg-zinc-900/40">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Created</div>
                <div className="mt-1 text-ink tabular-nums">{fmtShort(modalLead.created_at || '')}</div>
              </div>
              <div className="rounded-xl border border-surface-border bg-field/60 px-3 py-2 dark:bg-zinc-900/40">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Updated</div>
                <div className="mt-1 text-ink tabular-nums">{fmtShort(modalLead.updated_at || '')}</div>
              </div>
              <div className="sm:col-span-2">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-title">
                  Title
                </label>
                <input
                  id="m-title"
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                  placeholder="Job title or headline"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-co">
                  Company
                </label>
                <input
                  id="m-co"
                  value={companyDraft}
                  onChange={(e) => setCompanyDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                  placeholder="Organization"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-em">
                  Email
                </label>
                <input
                  id="m-em"
                  type="email"
                  value={emailDraft}
                  onChange={(e) => setEmailDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                  placeholder="name@company.com"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-web">
                  Website
                </label>
                <input
                  id="m-web"
                  value={websiteDraft}
                  onChange={(e) => setWebsiteDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                  placeholder="https://…"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-li">
                  LinkedIn
                </label>
                <input
                  id="m-li"
                  value={linkedinDraft}
                  onChange={(e) => setLinkedinDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                  placeholder="Profile URL"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-sz">
                  Company size
                </label>
                <input
                  id="m-sz"
                  value={companySizeDraft}
                  onChange={(e) => setCompanySizeDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-ind">
                  Industry
                </label>
                <input
                  id="m-ind"
                  value={industryDraft}
                  onChange={(e) => setIndustryDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-loc">
                  Location
                </label>
                <input
                  id="m-loc"
                  value={locationDraft}
                  onChange={(e) => setLocationDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle" htmlFor="m-ph">
                  Phone
                </label>
                <input
                  id="m-ph"
                  value={phoneDraft}
                  onChange={(e) => setPhoneDraft(e.target.value)}
                  className="field-input mt-1 w-full text-sm"
                />
              </div>
            </div>
            {modalLead.followup_message ? (
              <div className="rounded-xl border border-surface-border bg-field/60 px-3 py-2 dark:bg-zinc-900/40">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Follow-up draft</div>
                <div className="mt-1 whitespace-pre-wrap text-xs text-ink-muted">{modalLead.followup_message}</div>
              </div>
            ) : null}
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Internal notes</div>
              <textarea
                value={notesDraft}
                onChange={(e) => setNotesDraft(e.target.value)}
                rows={4}
                className="field-input mt-2 min-h-[100px]"
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Last contacted</div>
                <input
                  type="datetime-local"
                  value={lastContactLocal}
                  onChange={(e) => setLastContactLocal(e.target.value)}
                  className="field-input mt-2"
                />
              </div>
              <div>
                <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Follow-up reminder</div>
                <input
                  type="datetime-local"
                  value={followUpLocal}
                  onChange={(e) => setFollowUpLocal(e.target.value)}
                  className="field-input mt-2"
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={saveBusy}
                onClick={() => void saveModalMeta()}
                className="btn-primary px-4 py-2 text-xs disabled:opacity-50"
              >
                {saveBusy ? 'Saving' : 'Save Changes'}
              </button>
              <button
                type="button"
                disabled={modalLead ? genBusyLeadId === modalLead.id : false}
                onClick={async () => {
                  if (!modalLead) return
                  const id = modalLead.id
                  setGenBusyLeadId(id)
                  try {
                    const res = await genMsg(id)
                    patchLocal(id, { personalized_message: res.message })
                    const fresh = await getLead(id)
                    await openModal(fresh)
                    toast.success('Draft message saved (status unchanged until you move the pipeline).')
                  } catch (e) {
                    toast.error(getApiErrorMessage(e, 'Could not generate message'))
                  } finally {
                    setGenBusyLeadId((cur) => (cur === id ? null : cur))
                    void load()
                  }
                }}
                className="inline-flex items-center gap-2 rounded-xl border border-amber-500/35 bg-amber-500/5 px-4 py-2 text-xs font-semibold text-amber-900 transition hover:border-amber-500/50 dark:text-amber-200"
              >
                <Sparkles className="h-4 w-4" />
                Generate Outreach Message
              </button>
            </div>
            <div>
              <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">
                Recent outreach performance
              </div>
              <div className="max-h-64 space-y-2 overflow-y-auto rounded-xl border border-surface-border bg-field/50 p-3 dark:bg-zinc-900/40">
                {timeline.length === 0 ? (
                  <p className="text-xs text-ink-subtle">
                    No outreach history available. Outreach activity will appear here once leads are contacted.
                  </p>
                ) : (
                  timeline.map((t, i) => (
                    <div key={i} className="border-b border-surface-border/60 pb-2 text-xs last:border-0">
                      <div className="font-medium text-ink">{t.title}</div>
                      <div className="text-[10px] text-ink-subtle">{t.at}</div>
                      {t.body ? <div className="mt-1 text-ink-muted">{t.body}</div> : null}
                    </div>
                  ))
                )}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-ink-subtle">Outreach draft</div>
              <textarea
                value={messageDraft}
                onChange={(e) => setMessageDraft(e.target.value)}
                rows={5}
                className="field-input mt-2 w-full resize-y py-2 text-xs"
                placeholder="Generated message — edit here, then Save changes. Sending email is separate once SMTP is configured."
              />
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
