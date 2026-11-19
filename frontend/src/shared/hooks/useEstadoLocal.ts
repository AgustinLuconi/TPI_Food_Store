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

/** La fecha de hoy ("2026-11-17") en la zona horaria del LOCAL, no en la del navegador. */
export function fechaEnZona(ahora: Date, zonaHoraria: string): string {
  // 'en-CA' formatea como AAAA-MM-DD.
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: zonaHoraria,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(ahora)
}

/** Hoy en el local, o undefined mientras no se conoce su zona horaria. No depende del rol (el estado del local es público). */
export function useHoyEnElLocal(): string | undefined {
  const { data } = useEstadoLocal()
  return data ? fechaEnZona(new Date(), data.zona_horaria) : undefined
}
