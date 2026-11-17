import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { inventarioApi, produccionApi } from '../api/inventarioApi'
import type { FiltrosStock, MovimientoInput, OrdenInput, TipoItem } from '../types'

export function useItemsStock(tipo: TipoItem, filtros: FiltrosStock) {
  return useQuery({
    queryKey: [tipo === 'producto' ? 'productos' : 'ingredientes', 'stock', filtros],
    queryFn: () => inventarioApi.items(tipo, filtros),
    placeholderData: keepPreviousData,
  })
}

export function useOpciones(tipo: TipoItem, soloElaborados = false) {
  return useQuery({
    queryKey: [
      tipo === 'producto' ? 'productos' : 'ingredientes',
      'opciones-inventario',
      soloElaborados,
    ],
    queryFn: () => inventarioApi.opciones(tipo, soloElaborados),
  })
}

export function useMovimientos(tipo: TipoItem, id: number, page: number) {
  return useQuery({
    queryKey: ['inventario', 'movimientos', tipo, id, page],
    queryFn: () => inventarioApi.movimientos(tipo, id, page),
    placeholderData: keepPreviousData,
  })
}

export function useLotes(productoId: number) {
  return useQuery({
    queryKey: ['inventario', 'lotes', productoId],
    queryFn: () => inventarioApi.lotes(productoId),
  })
}

export function usePorVencer(dias: number) {
  return useQuery({
    queryKey: ['inventario', 'por-vencer', dias],
    queryFn: () => inventarioApi.porVencer(dias),
  })
}

/** Un movimiento cambia el stock que muestran el inventario y el catálogo, y los lotes. */
function useInvalidarStock() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all(
      ['inventario', 'productos', 'ingredientes'].map((k) =>
        queryClient.invalidateQueries({ queryKey: [k] }),
      ),
    )
}

export function useRegistrarMovimiento(tipo: TipoItem, id: number) {
  const invalidar = useInvalidarStock()
  return useMutation({
    mutationFn: (input: MovimientoInput) => inventarioApi.registrar(tipo, id, input),
    onSuccess: invalidar,
  })
}

export function useOrdenes(estado: string, page: number) {
  return useQuery({
    queryKey: ['produccion', 'lista', estado, page],
    queryFn: () => produccionApi.list(estado, page),
    placeholderData: keepPreviousData,
  })
}

export function useOrden(id: number) {
  return useQuery({ queryKey: ['produccion', 'detalle', id], queryFn: () => produccionApi.get(id) })
}

/** Toda acción de producción mueve reservas y stock: se invalida también el inventario. */
function useInvalidarProduccion() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all(
      ['produccion', 'inventario', 'productos', 'ingredientes'].map((k) =>
        queryClient.invalidateQueries({ queryKey: [k] }),
      ),
    )
}

export function useCrearOrden() {
  const invalidar = useInvalidarProduccion()
  return useMutation({
    mutationFn: (input: OrdenInput) => produccionApi.create(input),
    onSuccess: invalidar,
  })
}

export function useIniciarOrden() {
  const invalidar = useInvalidarProduccion()
  return useMutation({ mutationFn: produccionApi.iniciar, onSuccess: invalidar })
}

export function useCompletarOrden() {
  const invalidar = useInvalidarProduccion()
  return useMutation({
    mutationFn: ({
      id,
      lote,
    }: {
      id: number
      lote?: { codigo_lote: string; fecha_vencimiento: string }
    }) => produccionApi.completar(id, lote),
    onSuccess: invalidar,
  })
}

export function useCancelarOrden() {
  const invalidar = useInvalidarProduccion()
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) =>
      produccionApi.cancelar(id, motivo),
    onSuccess: invalidar,
  })
}
