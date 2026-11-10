import { useId, type SelectHTMLAttributes } from 'react'
import { cn } from './cn'

export interface SelectOption {
  value: string
  label: string
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label: string
  options: SelectOption[]
  error?: string | null
  /** Oculta la etiqueta visualmente (sigue disponible para lectores de pantalla). */
  hideLabel?: boolean
}

export function Select({ label, options, error, hideLabel, className, id, ...props }: SelectProps) {
  const generado = useId()
  const selectId = id ?? generado

  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={selectId}
        className={cn('text-sm font-semibold text-navy-900', hideLabel && 'sr-only')}
      >
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        className={cn(
          'w-full rounded-lg border bg-white px-3 py-2 text-sm text-navy-900',
          error ? 'border-danger-600' : 'border-surface-border',
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && (
        <p role="alert" className="text-sm text-danger-700">
          {error}
        </p>
      )}
    </div>
  )
}
