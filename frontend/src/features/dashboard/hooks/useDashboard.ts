import { useQueries, useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboardApi'
import { restarDias } from '../lib/fechas'

const REFRESCO = 60_000

export const useResumen = () =>
  useQuery({
    queryKey: ['metricas', 'resumen'],
    queryFn: dashboardApi.resumen,
    refetchInterval: REFRESCO,
  })

/** La serie de ventas de los últimos `dias` días, contados desde HOY EN EL LOCAL (la fecha que informa el resumen). */
export function useVentas(dias: number, hoy: string | undefined) {
  return useQuery({
    queryKey: ['metricas', 'ventas', dias, hoy],
    queryFn: () => dashboardApi.ventas(restarDias(hoy as string, dias - 1), hoy as string),
    enabled: hoy !== undefined,
  })
}

export const useTopProductos = (limit = 5) =>
  useQuery({
    queryKey: ['metricas', 'top', limit],
    queryFn: () => dashboardApi.topProductos(limit),
  })

export const useStockBajo = (dias = 7) =>
  useQuery({
    queryKey: ['metricas', 'stock-bajo', dias],
    queryFn: () => dashboardApi.stockBajo(dias),
    refetchInterval: REFRESCO,
  })

export function useMermas(dias: number, hoy: string | undefined) {
  return useQuery({
    queryKey: ['metricas', 'mermas', dias, hoy],
    queryFn: () => dashboardApi.mermas(restarDias(hoy as string, dias - 1), hoy as string),
    enabled: hoy !== undefined,
  })
}

/** Pedidos por estado para quien no ve las métricas del ADMIN (PEDIDOS): un conteo por estado, hecho en la base. */
export function useConteoDePedidos(estados: string[]) {
  return useQueries({
    queries: estados.map((estado) => ({
      queryKey: ['metricas', 'conteo-pedidos', estado],
      queryFn: () => dashboardApi.contarPedidos(estado),
      refetchInterval: REFRESCO,
    })),
  })
}

export const useColaDePedidos = (estado: string, size = 5) =>
  useQuery({
    queryKey: ['metricas', 'cola-pedidos', estado, size],
    queryFn: () => dashboardApi.colaDePedidos(estado, size),
    refetchInterval: REFRESCO,
  })

export const useColaDeProduccion = (estado: string, size = 5) =>
  useQuery({
    queryKey: ['metricas', 'cola-produccion', estado, size],
    queryFn: () => dashboardApi.colaDeProduccion(estado, size),
    refetchInterval: REFRESCO,
  })
