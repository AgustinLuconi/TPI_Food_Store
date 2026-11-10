import type { ButtonHTMLAttributes } from 'react'
import { cn } from './cn'

type Variante = 'primary' | 'secondary' | 'danger' | 'ghost'
type Tamano = 'sm' | 'md'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variante
  size?: Tamano
  loading?: boolean
}

const VARIANTES: Record<Variante, string> = {
  // accent-600 con texto blanco en negrita (contraste WCAG); accent-700 al pasar el mouse.
  primary: 'bg-accent-600 text-white font-bold hover:bg-accent-700',
  secondary:
    'bg-white text-navy-900 font-semibold border border-surface-border hover:bg-surface-muted',
  danger: 'bg-danger-600 text-white font-bold hover:bg-danger-700',
  ghost: 'bg-transparent text-navy-700 font-semibold hover:bg-surface-border',
}

const TAMANOS: Record<Tamano, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg transition-colors',
        'focus-visible:ring-2 focus-visible:ring-accent-600 focus-visible:ring-offset-2',
        'disabled:cursor-not-allowed disabled:opacity-60',
        VARIANTES[variant],
        TAMANOS[size],
        className,
      )}
      {...props}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
        />
      )}
      {children}
    </button>
  )
}
