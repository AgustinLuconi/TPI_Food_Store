import { Badge } from '@/shared/ui/Badge'
import { nombreDeEstado } from '../lib/estados'
import type { EstadoPedido } from '../types'

const TONO: Record<EstadoPedido, 'neutral' | 'accent' | 'success' | 'danger'> = {
  PENDIENTE: 'neutral',
  CONFIRMADO: 'accent',
  EN_PREPARACION: 'accent',
  EN_CAMINO: 'accent',
  ENTREGADO: 'success',
  CANCELADO: 'danger',
}

export function EstadoDelPedido({
  estado,
  conEnvio = true,
}: {
  estado: EstadoPedido
  conEnvio?: boolean
}) {
  return <Badge tone={TONO[estado]}>{nombreDeEstado(estado, conEnvio)}</Badge>
}
