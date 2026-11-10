import type { HTMLAttributes } from 'react'
import { cn } from './cn'

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-xl border border-surface-border bg-white p-5 shadow-sm', className)}
      {...props}
    />
  )
}
