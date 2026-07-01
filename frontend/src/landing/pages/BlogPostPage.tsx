import { ArrowLeft, Calendar, Clock, User } from 'lucide-react'
import { Link, useParams, Navigate } from 'react-router-dom'

import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { blogPosts } from '@/landing/data/blog'

export function BlogPostPage() {
  const { slug } = useParams<{ slug: string }>()
  const productName = useBrandingStore((s) => s.branding.product_name)
  const post = blogPosts.find((p) => p.slug === slug)

  if (!post) return <Navigate to="/blog" replace />

  return (
    <>
      <SeoHead
        title={`${post.title} - ${productName || APP_NAME}`}
        description={post.excerpt}
        keywords={[post.category, post.title]}
      />

      <article className="mx-auto max-w-3xl px-4 py-12">
        <Link
          to="/blog"
          className="mb-8 inline-flex items-center gap-2 text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" /> Back to blog
        </Link>

        <header>
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            {post.category}
          </span>
          <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            {post.title}
          </h1>
          <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-zinc-500">
            <span className="flex items-center gap-1">
              <User className="h-4 w-4" /> {post.author}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" /> {post.date}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" /> {post.readTime}
            </span>
          </div>
        </header>

        <div className="mt-8 leading-relaxed text-zinc-600 dark:text-zinc-400 space-y-4">
          {post.body?.split('\n\n').map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </div>

        <div className="mt-10 border-t border-surface-border pt-8">
          <Link
            to="/blog"
            className="inline-flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-300 hover:gap-3 transition-all"
          >
            <ArrowLeft className="h-4 w-4" /> More articles
          </Link>
        </div>
      </article>
    </>
  )
}
