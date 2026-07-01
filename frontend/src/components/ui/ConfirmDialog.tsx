import { AlertTriangle } from 'lucide-react'

import { Modal } from './Modal'

type ConfirmDialogProps = {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'warning' | 'default'
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const btnStyles = {
    danger: 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white',
    warning: 'bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 text-white',
    default: 'bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-700 hover:to-amber-600 text-white',
  }

  const iconColors = {
    danger: 'text-red-500',
    warning: 'text-amber-500',
    default: 'text-amber-500',
  }

  return (
    <Modal open={open} title="" onClose={() => { if (!busy) onCancel() }}>
      <div className="space-y-4">
        <div className="flex items-start gap-4">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${variant === 'danger' ? 'bg-red-100 dark:bg-red-950/30' : 'bg-amber-100 dark:bg-amber-950/30'}`}>
            <AlertTriangle className={`h-5 w-5 ${iconColors[variant]}`} />
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-zinc-900 dark:text-white">{title}</h3>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{message}</p>
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className={`inline-flex items-center gap-2 rounded-lg px-5 py-2 text-sm font-semibold shadow-sm disabled:opacity-45 ${btnStyles[variant]}`}
          >
            {busy ? 'Please wait...' : confirmLabel}
          </button>
        </div>
      </div>
    </Modal>
  )
}
