import { Calendar, Clock, User } from 'lucide-react'
import { Link } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { blogPosts } from '@/landing/data/blog'

export function BlogPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Blog - ${productName || APP_NAME}`}
        description={`Read the latest articles on lead generation, sales tips, business growth, and product updates from the ${productName} team.`}
        keywords={['blog', 'sales tips', 'lead generation', 'business growth', 'articles']}
      />

      <section className="border-b border-surface-border bg-gradient-to-br from-amber-500/5 to-emerald-500/5">
        <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
          <h1 className="font-display text-4xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-5xl">
            Blog
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-zinc-600 dark:text-zinc-400">
            Insights, tips, and practical advice for sales professionals.
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-12">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {blogPosts.map((post) => (
            <Link
              key={post.id}
              to={`/blog/${post.slug}`}
              className="group rounded-2xl border border-surface-border bg-white p-5 transition-all hover:shadow-sm dark:bg-zinc-900"
            >
              <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                {post.category}
              </span>
              <h2 className="mt-2 font-display text-lg font-semibold text-zinc-900 dark:text-white group-hover:text-amber-700 dark:group-hover:text-amber-300 transition-colors">
                {post.title}
              </h2>
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 line-clamp-3">{post.excerpt}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-zinc-500">
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" /> {post.author}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> {post.date}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {post.readTime}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </>
  )
}
