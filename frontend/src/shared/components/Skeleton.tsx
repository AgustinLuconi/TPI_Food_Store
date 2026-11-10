import { cn } from '@/shared/ui/cn'

/** Bloque animado que ocupa el lugar del contenido mientras carga. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div aria-hidden="true" className={cn('animate-pulse rounded bg-surface-border', className)} />
  )
}
