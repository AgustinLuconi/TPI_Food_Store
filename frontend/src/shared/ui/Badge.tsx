import type { ReactNode } from 'react'
import { cn } from './cn'

type Tono = 'neutral' | 'accent' | 'danger' | 'success'

const TONOS: Record<Tono, string> = {
  neutral: 'bg-surface-border text-navy-900',
  // Los badges naranjas llevan texto navy-900 (contraste WCAG).
  accent: 'bg-accent-100 text-navy-900',
  danger: 'bg-red-100 text-navy-900',
  success: 'bg-green-100 text-navy-900',
}

export function Badge({ tone = 'neutral', children }: { tone?: Tono; children: ReactNode }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        TONOS[tone],
      )}
    >
      {children}
    </span>
  )
}
