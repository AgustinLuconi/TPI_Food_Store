/**
 * Contexto de las páginas de resultado /success y /error (sección 11.4): el resultado de una acción
 * navega allí con su contexto en `location.state`. No hay notificaciones efímeras.
 */
export interface ResultadoState {
  titulo: string
  mensaje: string
  volverA: string
  volverLabel: string
}

export function esResultadoState(valor: unknown): valor is ResultadoState {
  if (typeof valor !== 'object' || valor === null) return false
  const v = valor as Record<string, unknown>
  return (
    typeof v.titulo === 'string' &&
    typeof v.mensaje === 'string' &&
    typeof v.volverA === 'string' &&
    typeof v.volverLabel === 'string'
  )
}
