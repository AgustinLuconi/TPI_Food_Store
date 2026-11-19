import { cn } from '@/shared/ui/cn'
import { CAMINO, nombreDeEstado } from '../lib/estados'
import type { EstadoPedido } from '../types'

/** Barra de progreso del camino feliz. Un pedido cancelado no la muestra. */
export function PasosDelPedido({ estado, conEnvio }: { estado: EstadoPedido; conEnvio: boolean }) {
  if (estado === 'CANCELADO') return null
  const actual = CAMINO.indexOf(estado)
  return (
    <ol aria-label="Progreso del pedido" className="grid grid-cols-5 gap-1 text-center text-xs">
      {CAMINO.map((e, i) => (
        <li
          key={e}
          aria-current={i === actual ? 'step' : undefined}
          className="flex flex-col items-center gap-1"
        >
          <span
            className={cn(
              'h-2 w-full rounded-full',
              i < actual && 'bg-success-600',
              i === actual && 'bg-accent-600',
              i > actual && 'bg-surface-border',
            )}
          />
          <span className={cn('font-semibold', i === actual ? 'text-navy-900' : 'text-navy-500')}>
            {nombreDeEstado(e, conEnvio)}
          </span>
        </li>
      ))}
    </ol>
  )
}
