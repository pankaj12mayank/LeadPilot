import { ArrowLeft, BarChart3, Database, Gauge, LayoutDashboard, Rocket, Send, Target, TrendingUp, Waypoints, Workflow } from 'lucide-react'
import { Link, Navigate, useParams } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { featuresDetail } from '@/landing/data/featuresDetail'

const iconMap: Record<string, typeof Target> = {
  Target, Send, LayoutDashboard, Waypoints, Database, BarChart3, Rocket, Gauge, Workflow, TrendingUp,
}

export function FeatureDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const productName = useBrandingStore((s) => s.branding.product_name)

  const feature = featuresDetail.find((f) => f.slug === slug)
  if (!feature) return <Navigate to="/404" replace />

  const Icon = iconMap[feature.icon] || Target

  return (
    <>
      <SeoHead
        title={`${feature.title} - ${productName || APP_NAME}`}
        description={feature.description}
        keywords={[feature.title, 'lead generation', 'sales', 'CRM']}
      />
      <section className="mx-auto max-w-3xl px-4 py-16 sm:py-20">
        <Link
          to="/features"
          className="inline-flex items-center gap-1.5 text-sm text-zinc-500 hover:text-amber-700 dark:hover:text-amber-300 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Features
        </Link>
        <div className="mt-6 flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
            <Icon className="h-7 w-7" />
          </div>
          <div>
            <h1 className="font-display text-3xl font-bold text-zinc-900 dark:text-white sm:text-4xl">
              {feature.title}
            </h1>
            <p className="mt-1 text-zinc-600 dark:text-zinc-400">{feature.description}</p>
          </div>
        </div>
        <div className="mt-10 prose prose-zinc dark:prose-invert max-w-none">
          <p className="text-base leading-relaxed text-zinc-700 dark:text-zinc-300">
            {feature.content}
          </p>
        </div>
        <div className="mt-10">
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-6 py-3 text-sm font-semibold text-white hover:bg-amber-700 transition-all"
          >
            Get Started with {feature.title}
          </Link>
        </div>
      </section>
    </>
  )
}
