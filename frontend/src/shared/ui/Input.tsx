import { useId, type InputHTMLAttributes, type Ref } from 'react'
import { cn } from './cn'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string | null
  hint?: string
  ref?: Ref<HTMLInputElement>
}

export function Input({ label, error, hint, className, id, ref, ...props }: InputProps) {
  const generado = useId()
  const inputId = id ?? generado
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-semibold text-navy-900">
        {label}
        {props.required && <span className="text-danger-600"> *</span>}
      </label>
      <input
        id={inputId}
        ref={ref}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          'w-full rounded-lg border bg-white px-3 py-2 text-sm text-navy-900',
          'placeholder:text-navy-500 disabled:bg-surface-muted',
          error ? 'border-danger-600' : 'border-surface-border',
          className,
        )}
        {...props}
      />
      {error ? (
        <p id={`${inputId}-error`} role="alert" className="text-sm text-danger-700">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${inputId}-hint`} className="text-xs text-navy-500">
            {hint}
          </p>
        )
      )}
    </div>
  )
}
