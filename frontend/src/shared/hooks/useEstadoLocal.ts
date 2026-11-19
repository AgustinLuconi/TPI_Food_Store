import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/axiosInstance'

export interface EstadoLocal {
  abierto: boolean
  /** Instante ISO en la zona horaria del local; null si ya está abierto. */
  proxima_apertura: string | null
  zona_horaria: string
}

/**
 * ¿Está abierto el local? Es público: lo usan el carrito y el checkout para deshabilitar el pedido con el motivo
 * y la próxima apertura (sección 11.2), y el panel para mostrar el estado. Se refresca cada minuto.
 */
export function useEstadoLocal() {
  return useQuery({
    queryKey: ['config', 'estado-local'],
    queryFn: () => api.get<EstadoLocal>('/config/estado-local').then((r) => r.data),
    refetchInterval: 60_000,
  })
}
