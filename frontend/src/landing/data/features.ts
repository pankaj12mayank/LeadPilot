import type { LucideIcon } from 'lucide-react'
import { Database, BarChart3, Target, Send, LayoutDashboard, Waypoints, Rocket, Gauge, Workflow, TrendingUp } from 'lucide-react'

export type FeatureItem = {
  icon: LucideIcon
  title: string
  description: string
  link: string
}

export const features: FeatureItem[] = [
  {
    icon: Target,
    title: 'Lead generation software',
    description:
      'Discover high-quality leads from LinkedIn and other sources. Filter by industry, location, role, and more to build a targeted prospect list in minutes.',
    link: '/features/lead-generation-software',
  },
  {
    icon: Send,
    title: 'Sales outreach platform',
    description:
      'Automate personalized email and LinkedIn outreach sequences. Track opens, replies, and engagement from one dashboard.',
    link: '/features/sales-outreach-platform',
  },
  {
    icon: LayoutDashboard,
    title: 'CRM dashboard',
    description:
      'Monitor lead activity, deal stages, conversion trends, and team workload at a glance with live charts and custom reports.',
    link: '/features/crm-dashboard',
  },
  {
    icon: Waypoints,
    title: 'Lead tracking software',
    description:
      'Track every interaction from first touch to closed deal. Log emails, calls, notes, and status changes automatically.',
    link: '/features/lead-tracking-software',
  },
  {
    icon: Database,
    title: 'Prospect database management',
    description:
      'Import, merge, enrich, and segment your prospect database. Automatic deduplication and company enrichment keep your data clean.',
    link: '/features/prospect-database-management',
  },
  {
    icon: BarChart3,
    title: 'Sales analytics tools',
    description:
      'Understand which channels drive conversions, where deals stall, and what your team needs to hit quota.',
    link: '/features/sales-analytics-tools',
  },
  {
    icon: Rocket,
    title: 'Customer acquisition platform',
    description:
      'From prospecting to closing, get every tool you need to acquire customers at scale in one subscription.',
    link: '/features/customer-acquisition-platform',
  },
  {
    icon: Gauge,
    title: 'Lead scoring system',
    description:
      'Rank prospects by engagement, fit, and buying signals. Prioritise your outreach and close more deals with less effort.',
    link: '/features/lead-scoring-system',
  },
  {
    icon: Workflow,
    title: 'Sales workflow automation',
    description:
      'Set up automated sequences, triggers, and follow-up rules that work while you sleep.',
    link: '/features/sales-workflow-automation',
  },
  {
    icon: TrendingUp,
    title: 'Business growth tools',
    description:
      'Combine team collaboration, pipeline analytics, and smart automation into one growth engine.',
    link: '/features/business-growth-tools',
  },
]
