import { Mail, MapPin, Phone } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { contactInfo } from '@/landing/data/contact'
import { submitContact } from '@/lib/api/publicMessages'
import { getApiErrorMessage } from '@/lib/api/client'

export function ContactSection() {
  const [cName, setCName] = useState('')
  const [cEmail, setCEmail] = useState('')
  const [cMessage, setCMessage] = useState('')
  const [contactBusy, setContactBusy] = useState(false)
  const [contactSent, setContactSent] = useState(false)

  async function handleContactSubmit(e: React.FormEvent) {
    e.preventDefault()
    setContactBusy(true)
    try {
      await submitContact({ name: cName.trim(), email: cEmail.trim(), message: cMessage.trim() })
      setContactSent(true)
      setCName(''); setCEmail(''); setCMessage('')
    } catch (err) {
      toast.error(getApiErrorMessage(err, 'Could not send message'))
    } finally {
      setContactBusy(false)
    }
  }
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
          Contact
        </p>
        <h2 className="mt-2 font-display text-3xl font-bold tracking-tight text-zinc-900 dark:text-white sm:text-4xl">
          Get in touch
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-zinc-600 dark:text-zinc-400">
          Have a question or want to see a demo? We would love to hear from you.
        </p>
      </div>
      <div className="mt-12 grid gap-8 lg:grid-cols-2">
        <div className="space-y-6">
          {[
            { icon: MapPin, label: 'Address', value: contactInfo.address },
            { icon: Phone, label: 'Phone', value: contactInfo.phone },
            { icon: Mail, label: 'Email', value: contactInfo.email },
          ].map((item) => {
            const Icon = item.icon
            return (
              <div key={item.label} className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-700 dark:text-amber-300">
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-900 dark:text-white">{item.label}</p>
                  <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{item.value}</p>
                </div>
              </div>
            )
          })}
        </div>
        <form onSubmit={handleContactSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500" htmlFor="name">
                Name
              </label>
              <input id="name" value={cName} onChange={(e) => setCName(e.target.value)} type="text" required className="field-input mt-1" placeholder="Your name" />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500" htmlFor="contact-email">
                Email
              </label>
              <input id="contact-email" value={cEmail} onChange={(e) => setCEmail(e.target.value)} type="email" required className="field-input mt-1" placeholder="you@example.com" />
            </div>
          </div>
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-zinc-500" htmlFor="message">
              Message
            </label>
            <textarea
              id="message"
              value={cMessage}
              onChange={(e) => setCMessage(e.target.value)}
              required
              rows={4}
              className="field-input mt-1 resize-none"
              placeholder="Tell us about your project or question..."
            />
          </div>
          <button type="submit" disabled={contactBusy} className="btn-primary">
            {contactBusy ? 'Sending...' : 'Send Message'}
          </button>
          {contactSent && (
            <p className="text-sm text-emerald-600 dark:text-emerald-400">Thanks for reaching out. We will get back to you shortly.</p>
          )}
        </form>
      </div>
    </section>
  )
}
