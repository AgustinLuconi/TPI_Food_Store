import { useNavigate } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import type { ResultadoState } from '@/shared/types/resultado'

/**
 * El resultado de una acción navega a /success o /error con su contexto en location.state
 * (sección 11.4: sin notificaciones efímeras).
 */
export function useResultado() {
  const navigate = useNavigate()
  return {
    exito: (resultado: ResultadoState) => navigate(RUTAS.exito, { state: resultado }),
    fallo: (resultado: ResultadoState) => navigate(RUTAS.error, { state: resultado }),
  }
}
