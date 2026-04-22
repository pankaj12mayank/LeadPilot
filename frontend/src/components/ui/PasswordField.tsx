import { Eye, EyeOff } from 'lucide-react'
import { useId, useState } from 'react'

import { cn } from '@/lib/utils/cn'

type PasswordFieldProps = {
  id?: string
  label: string
  value: string
  onChange: (value: string) => void
  autoComplete?: string
  required?: boolean
  minLength?: number
  placeholder?: string
  className?: string
  inputClassName?: string
  /** Screen-reader label for the visibility toggle */
  toggleAriaLabelShow?: string
  toggleAriaLabelHide?: string
}

export function PasswordField({
  id: idProp,
  label,
  value,
  onChange,
  autoComplete = 'current-password',
  required,
  minLength,
  placeholder,
  className,
  inputClassName,
  toggleAriaLabelShow = 'Show password',
  toggleAriaLabelHide = 'Hide password',
}: PasswordFieldProps) {
  const uid = useId()
  const id = idProp ?? `pw-${uid}`
  const [visible, setVisible] = useState(false)

  return (
    <div className={cn(className)}>
      <label className="text-xs font-semibold uppercase tracking-wider text-ink-muted" htmlFor={id}>
        {label}
      </label>
      <div className="relative mt-2">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn('field-input w-full pr-11', inputClassName)}
        />
        <button
          type="button"
          tabIndex={-1}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-ink-subtle transition hover:bg-field hover:text-ink dark:hover:bg-white/5"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? toggleAriaLabelHide : toggleAriaLabelShow}
        >
          {visible ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
        </button>
      </div>
    </div>
  )
}
