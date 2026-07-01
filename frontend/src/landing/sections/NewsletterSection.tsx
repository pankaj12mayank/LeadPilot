import { useState } from 'react'
import { Send } from 'lucide-react'
import { toast } from 'sonner'

import { subscribeNewsletter } from '@/lib/api/publicMessages'
import { getApiErrorMessage } from '@/lib/api/client'

export function NewsletterSection() {
  const [email, setEmail] = useState('')
  const [subscribed, setSubscribed] = useState(false)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email) return
    setBusy(true)
    try {
      await subscribeNewsletter(email.trim())
      setSubscribed(true)
      setEmail('')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not subscribe'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="border-t border-surface-border bg-zinc-900 dark:bg-black">
      <div className="mx-auto max-w-6xl px-4 py-16 text-center sm:py-20">
        <h2 className="font-display text-2xl font-bold text-white sm:text-3xl">
          Subscribe to our newsletter
        </h2>
        <p className="mt-2 text-zinc-400">
          Follow along for product updates, sales tips, and industry news.
        </p>
        {subscribed ? (
          <p className="mt-6 text-emerald-400">Thanks for subscribing. We will be in touch.</p>
        ) : (
          <form onSubmit={handleSubmit} className="mx-auto mt-6 flex max-w-md gap-3">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
            <button
              type="submit"
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50 transition-all"
            >
              {busy ? '...' : <>Subscribe <Send className="h-4 w-4" /></>}
            </button>
          </form>
        )}
      </div>
    </section>
  )
}
