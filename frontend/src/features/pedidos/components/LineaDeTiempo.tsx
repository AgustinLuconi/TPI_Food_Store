import { formatearFecha } from '@/shared/lib/formato'
import { nombreDeEstado } from '../lib/estados'
import type { HistorialItem } from '../types'

/** El historial del pedido, del primer registro al último. Cada cambio de estado deja una fila (append-only). */
export function LineaDeTiempo({
  historial,
  conEnvio,
}: {
  historial: HistorialItem[]
  conEnvio: boolean
}) {
  return (
    <ol className="flex flex-col gap-3 border-l-2 border-surface-border pl-4">
      {historial.map((h, i) => (
        <li key={h.id} className="relative">
          <span
            aria-hidden="true"
            className={`absolute -left-[1.4rem] top-1.5 size-3 rounded-full ${i === historial.length - 1 ? 'bg-accent-600' : 'bg-surface-border'}`}
          />
          <p className="font-semibold text-navy-900">{nombreDeEstado(h.estado_hasta, conEnvio)}</p>
          <p className="text-xs text-navy-500">{formatearFecha(h.created_at, true)}</p>
          {h.motivo && <p className="text-sm text-navy-700">Motivo: {h.motivo}</p>}
        </li>
      ))}
    </ol>
  )
}
