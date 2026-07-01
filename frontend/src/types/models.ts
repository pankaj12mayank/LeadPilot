export type Lead = {
  id: string
  full_name: string
  title: string
  company_name: string
  company_website: string
  linkedin_url: string
  email: string
  phone: string
  company_size: string
  industry: string
  location: string
  source_platform: string
  notes: string
  score: number
  tier: string
  status: string
  personalized_message: string
  followup_message: string
  last_contacted_at: string
  follow_up_reminder_at: string
  created_at: string
  updated_at: string
  agency_type?: string
  problem_seen?: string
  last_active_display?: string
  connection_sent?: string
  replied_yn?: string
  solution_text?: string
  signal_hiring?: number
  signal_scaling?: number
  signal_content_gap?: number
  signal_ads_gap?: number
  priority?: string
}

export type User = {
  id: string
  email: string
  name?: string
  created_at: string
  role?: 'admin' | 'user' | 'buyer'
  plan_id?: 'starter' | 'growth' | 'pro' | 'enterprise'
  is_active?: boolean
  last_login_at?: string
}

export type AuthResponse = {
  access_token: string
  token_type: string
  user?: User
  subscription?: any
}

export type DashboardMonthPoint = {
  month: string
  count: number
}

export type DashboardTierMixRow = {
  platform: string
  hot: number
  warm: number
  cold: number
}

export type DashboardData = {
  total?: number
  total_companies?: number
  by_status?: Record<string, number>
  by_platform?: Record<string, number>
  total_leads?: number
  hot_leads?: number
  new_leads?: number
  warm_leads?: number
  cold_leads?: number
  tier_distribution?: Record<string, number>
  contacted_leads?: number
  converted_leads?: number
  conversion_rate_percent?: number
  platform_distribution?: Record<string, number>
  status_distribution?: Record<string, number>
  recent_history_events?: number
  /** Aggregated server-side for charts (avoids loading all leads on the client). */
  leads_by_month?: DashboardMonthPoint[]
  tier_mix_by_platform?: DashboardTierMixRow[]
}

export type AppSettings = Record<string, unknown>
