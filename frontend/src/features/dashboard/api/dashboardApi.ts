import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import type { FilaDeCola, Mermas, Resumen, StockBajo, TopProducto, Ventas } from '../types'

const M = '/admin/metrics'

export const dashboardApi = {
  resumen: () => api.get<Resumen>(`${M}/resumen`).then((r) => r.data),
  ventas: (desde: string, hasta: string) =>
    api.get<Ventas>(`${M}/ventas`, { params: { desde, hasta } }).then((r) => r.data),
  topProductos: (limit: number) =>
    api.get<TopProducto[]>(`${M}/top-productos`, { params: { limit } }).then((r) => r.data),
  stockBajo: (dias: number) =>
    api.get<StockBajo>(`${M}/stock-bajo`, { params: { dias } }).then((r) => r.data),
  mermas: (desde: string, hasta: string) =>
    api.get<Mermas>(`${M}/mermas`, { params: { desde, hasta } }).then((r) => r.data),

  /** Cantidad de pedidos de un estado: el `total` del listado paginado lo cuenta la base (size=1 trae una fila). */
  contarPedidos: (estado: string) =>
    api
      .get<Paginated<unknown>>('/pedidos', { params: { estado, size: 1 } })
      .then((r) => r.data.total),

  /** Las primeras filas de una cola de pedidos (por ejemplo, los confirmados que esperan preparación). */
  colaDePedidos: (estado: string, size: number): Promise<{ total: number; filas: FilaDeCola[] }> =>
    api
      .get<Paginated<{ id: number; cliente_nombre: string; total: string; con_envio: boolean }>>(
        '/pedidos',
        { params: { estado, size } },
      )
      .then((r) => ({
        total: r.data.total,
        filas: r.data.items.map((p) => ({
          id: p.id,
          titulo: `Pedido #${p.id}`,
          detalle: `${p.cliente_nombre} · ${p.con_envio ? 'envío' : 'retiro'}`,
        })),
      })),

  colaDeProduccion: (
    estado: string,
    size: number,
  ): Promise<{ total: number; filas: FilaDeCola[] }> =>
    api
      .get<Paginated<{ id: number; nombre: string; cantidad_a_producir: string }>>('/produccion', {
        params: { estado, size },
      })
      .then((r) => ({
        total: r.data.total,
        filas: r.data.items.map((o) => ({
          id: o.id,
          titulo: `Orden #${o.id}`,
          detalle: `${o.nombre} · ${Number(o.cantidad_a_producir)} u.`,
        })),
      })),
}
