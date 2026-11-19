import type { EstadoPedido } from '../types'

export const NOMBRE_ESTADO: Record<EstadoPedido, string> = {
  PENDIENTE: 'Pendiente de pago',
  CONFIRMADO: 'Confirmado',
  EN_PREPARACION: 'En preparación',
  EN_CAMINO: 'En camino',
  ENTREGADO: 'Entregado',
  CANCELADO: 'Cancelado',
}

/** El orden del camino feliz del pedido; CANCELADO queda aparte. */
export const CAMINO: EstadoPedido[] = [
  'PENDIENTE',
  'CONFIRMADO',
  'EN_PREPARACION',
  'EN_CAMINO',
  'ENTREGADO',
]

export const esTerminal = (e: EstadoPedido) => e === 'ENTREGADO' || e === 'CANCELADO'

/** El propietario cancela en PENDIENTE o CONFIRMADO; el personal, en cualquier estado no terminal. */
export function puedeCancelar(estado: EstadoPedido, esPersonal: boolean): boolean {
  if (esTerminal(estado)) return false
  return esPersonal || estado === 'PENDIENTE' || estado === 'CONFIRMADO'
}

/** Siguiente estado de la gestión (PENDIENTE solo avanza con el pago, no a mano). */
export function siguienteEstado(estado: EstadoPedido): EstadoPedido | null {
  const i = CAMINO.indexOf(estado)
  return i <= 0 || i >= CAMINO.length - 1 ? null : CAMINO[i + 1]
}

export const ETIQUETA_SIGUIENTE: Partial<Record<EstadoPedido, string>> = {
  CONFIRMADO: 'Pasar a preparación',
  EN_PREPARACION: 'Marcar en camino / listo para retirar',
  EN_CAMINO: 'Marcar entregado',
}

/** En retiro en el local, EN_CAMINO significa "listo para retirar" (sección 9.1). */
export function nombreDeEstado(estado: EstadoPedido, conEnvio: boolean): string {
  if (estado === 'EN_CAMINO' && !conEnvio) return 'Listo para retirar'
  return NOMBRE_ESTADO[estado]
}
