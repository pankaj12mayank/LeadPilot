import { X } from 'lucide-react'
import { useEffect, type ReactNode } from 'react'

import { cn } from '@/lib/utils/cn'

type ModalProps = {
  open: boolean
  title: ReactNode
  /** Optional native tooltip when title is plain text */
  titleHint?: string
  onClose: () => void
  children: ReactNode
  className?: string
}

export function Modal({ open, title, titleHint, onClose, children, className }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-zinc-900/50 backdrop-blur-md dark:bg-black/70"
        aria-label="Close modal"
        onClick={onClose}
      />
      <div
        className={cn(
          'relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-surface-border bg-surface-card/95 p-6 shadow-glow backdrop-blur-xl dark:bg-zinc-950/90',
          className,
        )}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2
            id="modal-title"
            title={titleHint}
            className="min-w-0 max-w-[calc(100%-2.5rem)] font-display text-xl font-semibold leading-snug tracking-tight text-ink sm:text-2xl"
          >
            <span className="line-clamp-2 break-words">{title}</span>
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-ink-subtle transition hover:bg-field hover:text-ink dark:hover:bg-white/5"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
