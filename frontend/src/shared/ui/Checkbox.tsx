import { useId, type InputHTMLAttributes } from 'react'
import { cn } from './cn'

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  hint?: string
}

export function Checkbox({ label, hint, className, id, ...props }: CheckboxProps) {
  const generado = useId()
  const inputId = id ?? generado
  return (
    <div className="flex items-start gap-2">
      <input
        id={inputId}
        type="checkbox"
        className={cn('mt-0.5 size-4 accent-accent-600', className)}
        aria-describedby={hint ? `${inputId}-hint` : undefined}
        {...props}
      />
      <label htmlFor={inputId} className="text-sm text-navy-900">
        <span className="font-semibold">{label}</span>
        {hint && (
          <span id={`${inputId}-hint`} className="block text-xs text-navy-500">
            {hint}
          </span>
        )}
      </label>
    </div>
  )
}
