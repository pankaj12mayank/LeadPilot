import { ArrowRight, Calendar, User } from 'lucide-react'
import { Link } from 'react-router-dom'

import { blogPosts } from '@/landing/data/blog'

export function BlogSection() {
  const popular = blogPosts.slice(0, 2)
  const recent = blogPosts.slice(2, 5)

  return (
    <section className="border-t border-surface-border bg-white dark:bg-zinc-900">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
            From the blog
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
            Insights and practical advice
          </h2>
        </div>
        <div className="mt-12 grid gap-8 lg:grid-cols-2">
          {/* Popular */}
          <div>
            <h3 className="mb-6 font-display text-xl font-semibold text-zinc-900 dark:text-white">
              Popular articles
            </h3>
            <div className="space-y-6">
              {popular.map((post) => (
                <Link
                  key={post.id}
                  to={`/blog/${post.slug}`}
                  className="group block rounded-2xl border border-surface-border p-5 transition-all hover:shadow-sm"
                >
                  <span className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                    {post.category}
                  </span>
                  <h4 className="mt-1 font-display text-base font-semibold text-zinc-900 dark:text-white group-hover:text-amber-700 dark:group-hover:text-amber-300 transition-colors">
                    {post.title}
                  </h4>
                  <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2">
                    {post.excerpt}
                  </p>
                  <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" /> {post.author}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" /> {post.date}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent */}
          <div>
            <h3 className="mb-6 font-display text-xl font-semibold text-zinc-900 dark:text-white">
              Recent articles
            </h3>
            <div className="space-y-4">
              {recent.map((post) => (
                <Link
                  key={post.id}
                  to={`/blog/${post.slug}`}
                  className="group flex items-start gap-4 rounded-xl border border-surface-border p-4 transition-all hover:shadow-sm"
                >
                  <div className="min-w-0 flex-1">
                    <h4 className="font-display text-sm font-semibold text-zinc-900 dark:text-white group-hover:text-amber-700 dark:group-hover:text-amber-300 transition-colors line-clamp-2">
                      {post.title}
                    </h4>
                    <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" /> {post.date}
                      </span>
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" /> {post.author}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
            <div className="mt-6">
              <Link
                to="/blog"
                className="inline-flex items-center gap-2 text-sm font-medium text-amber-700 dark:text-amber-300 hover:gap-3 transition-all"
              >
                View All Articles <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
