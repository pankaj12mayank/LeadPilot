/**
 * Application copy: professional B2B SaaS tone, consistent terminology, SEO-oriented labels.
 * Do not import from API modules to avoid circular dependencies.
 */

export const APP_NAME = 'LeadPilot'

export const DEFAULT_META_DESCRIPTION =
  'LeadPilot is a lead management and sales CRM platform for prospecting, lead scoring, outreach tracking, sales analytics, and pipeline visibility. Built for sales teams, agencies, and growing businesses.'

export const ROUTE_META: Record<
  string,
  { title: string; subtitle: string; documentDescription?: string }
> = {
  '/dashboard': {
    title: 'Sales Performance Overview',
    subtitle:
      'Lead activity, pipeline health, and conversion signals across lead sources, lead scoring tiers, and sales outreach stages.',
    documentDescription:
      'CRM dashboard for sales performance, lead tracking, and sales pipeline visibility. Monitor customer acquisition metrics and lead management KPIs.',
  },
  '/search-leads': {
    title: 'LinkedIn people search',
    subtitle:
      'Run LinkedIn-only prospecting with keyword, location, and safety controls. Qualified rows go to your database for scoring and outreach.',
    documentDescription:
      'LinkedIn people search and lead generation: live job status, prospect preview, and CRM handoff.',
  },
  '/leads': {
    title: 'Contact and Lead Management',
    subtitle:
      'Filter your prospect database, update CRM pipeline status, capture notes, and export for sales analytics or sales outreach sequences.',
    documentDescription:
      'Lead tracking software and contact management for sales teams. Lead scoring, status updates, and conversion optimization in one table.',
  },
  '/outreach-queue': {
    title: 'Outreach Queue',
    subtitle:
      'Manage active outreach pipeline, prioritize by lead score, and review last contacted timestamps for follow-up actions.',
    documentDescription:
      'Outreach queue for sales pipeline management. View non-closed leads, filter by status and score, and prioritize outreach by qualification score.',
  },
  '/analytics': {
    title: 'Sales Analytics',
    subtitle:
      'Conversion rate analysis, outreach performance trends, and source effectiveness for pipeline decisions and business intelligence.',
    documentDescription:
      'Sales analytics tools for conversion optimization, prospect engagement metrics, and closed deal performance reporting.',
  },
  '/settings': {
    title: 'Workspace Settings',
    subtitle:
      'AI message configuration, delay and safety defaults, export preferences, and workspace notes for administrators.',
    documentDescription:
      'Account settings and platform preferences for outreach automation, lead scoring context, and export pipeline configuration.',
  },
  '/about': {
    title: 'About',
    subtitle: 'Product overview and frequently asked questions for your workspace.',
    documentDescription: 'About LeadPilot: lead management workspace, prospecting, and CRM-style tracking.',
  },
}

/** API status value to professional label (values unchanged for API compatibility) */
export const LEAD_STATUS_LABELS: Record<string, string> = {
  new: 'New',
  request_sent: 'Contacted',
  message_sent: 'Contacted',
  replied_got: 'Replied',
  on_discussion: 'Follow-up',
  interested: 'Interested',
  deal: 'Deal',
  close: 'Closed',
  not_interested: 'Not interested',
  // legacy (API may still return until edited)
  contacted: 'Contacted',
  replied: 'Replied',
  follow_up: 'Follow-up',
  follow_up_sent: 'Follow-up',
  meeting_scheduled: 'Follow-up',
  deal_discussion: 'Deal',
  closed: 'Closed',
  rejected: 'Not interested',
  ready: 'Contacted',
  converted: 'Closed',
}

export function leadStatusLabel(status: string): string {
  const k = (status || 'new').toLowerCase()
  return LEAD_STATUS_LABELS[k] ?? status.replace(/_/g, ' ')
}

/** Footer keyword links for internal discovery (same app routes) */
export const SEO_FOOTER_LINKS: ReadonlyArray<{ to: string; label: string }> = [
  { to: '/search-leads', label: 'Lead generation software' },
  { to: '/leads', label: 'Sales outreach platform' },
  { to: '/dashboard', label: 'CRM dashboard' },
  { to: '/leads', label: 'Lead tracking software' },
  { to: '/leads', label: 'Prospect database management' },
  { to: '/analytics', label: 'Sales analytics tools' },
  { to: '/dashboard', label: 'Customer acquisition platform' },
  { to: '/dashboard', label: 'Lead scoring system' },
  { to: '/search-leads', label: 'Sales workflow automation' },
  { to: '/analytics', label: 'Business growth tools' },
]
