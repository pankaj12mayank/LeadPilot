import { AlertCircle } from 'lucide-react'

type ApiLoadErrorProps = {
  message: string
  title?: string
  onRetry?: () => void
  retryLabel?: string
}

export function ApiLoadError({
  message,
  title = 'Could not load data',
  onRetry,
  retryLabel = 'Try again',
}: ApiLoadErrorProps) {
  return (
    <div className="mx-auto max-w-lg rounded-2xl border border-red-500/25 bg-red-50/90 p-6 shadow-card dark:bg-red-950/35">
      <div className="flex gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600 dark:text-red-400" aria-hidden />
        <div className="min-w-0 space-y-2">
          <h2 className="font-display text-base font-semibold text-red-900 dark:text-red-100">{title}</h2>
          <p className="text-sm leading-relaxed text-red-800/95 dark:text-red-200/90">{message}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 inline-flex items-center justify-center rounded-xl border border-red-500/40 bg-white/80 px-4 py-2 text-sm font-semibold text-red-900 shadow-sm transition hover:bg-white dark:bg-red-950/50 dark:text-red-100 dark:hover:bg-red-900/40"
            >
              {retryLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}
