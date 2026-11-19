import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { pedidosApi } from '../api/pedidosApi'
import { esTerminal } from '../lib/estados'
import type { EstadoPedido, FiltrosPedidos, PedidoNuevo } from '../types'

export const pedidosKeys = { all: ['pedidos'] as const }

export function usePedidos(filtros: FiltrosPedidos) {
  return useQuery({
    queryKey: [...pedidosKeys.all, 'lista', filtros],
    queryFn: () => pedidosApi.list(filtros),
    placeholderData: keepPreviousData,
  })
}

/**
 * El seguimiento consulta el pedido (y su historial) periódicamente mientras no esté en un estado terminal
 * (refetchInterval de TanStack Query, sección 11.2).
 */
export function usePedido(id: number, refrescarCada = 8000) {
  return useQuery({
    queryKey: [...pedidosKeys.all, 'detalle', id],
    queryFn: () => pedidosApi.get(id),
    refetchInterval: (query) =>
      query.state.data && esTerminal(query.state.data.estado_codigo) ? false : refrescarCada,
  })
}

/** Filtros extendidos de la gestión: además del estado, un rango de fechas (días del local). */
export function usePedidosDeGestion(filtros: FiltrosPedidos & { desde?: string; hasta?: string }) {
  return useQuery({
    queryKey: [...pedidosKeys.all, 'gestion', filtros],
    queryFn: () => pedidosApi.listGestion(filtros),
    placeholderData: keepPreviousData,
  })
}

export function useFormasDePago() {
  return useQuery({
    queryKey: ['pagos', 'formas'],
    queryFn: pedidosApi.paymentMethods,
    staleTime: 5 * 60_000,
  })
}

/** Cotiza el envío de una dirección con coordenadas. Un 422 (fuera de zona) es una respuesta, no un fallo a reintentar. */
export function useCotizacion(punto: { lat: number; lng: number } | null, subtotal: number) {
  return useQuery({
    queryKey: ['envio', 'cotizacion', punto?.lat, punto?.lng, subtotal],
    queryFn: () => pedidosApi.quote(punto!.lat, punto!.lng, subtotal),
    enabled: punto !== null && subtotal > 0,
    retry: false,
  })
}

/** Cualquier cambio en un pedido invalida los listados y el detalle (y el stock que muestra el catálogo). */
function useInvalidar() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: pedidosKeys.all })
}

export function useCrearPedido() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ body, clave }: { body: PedidoNuevo; clave: string }) =>
      pedidosApi.create(body, clave),
    onSuccess: invalidar,
  })
}

export function useCancelarPedido() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) => pedidosApi.cancel(id, motivo),
    onSuccess: invalidar,
  })
}

export function useRegistrarPago() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ pedidoId, monto, clave }: { pedidoId: number; monto: string; clave: string }) =>
      pedidosApi.registerPayment(pedidoId, monto, clave),
    onSuccess: invalidar,
  })
}

export function useCambiarEstado() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ id, estado }: { id: number; estado: EstadoPedido }) =>
      pedidosApi.changeState(id, estado),
    onSuccess: invalidar,
  })
}
