import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import type {
  FiltrosStock,
  ItemStock,
  Lote,
  LotePorVencer,
  Movimiento,
  MovimientoInput,
  Orden,
  OrdenInput,
  TipoItem,
} from '../types'

const BASE: Record<TipoItem, string> = { producto: '/productos', ingrediente: '/ingredientes' }

export const inventarioApi = {
  /** Productos o insumos con su stock real y disponible (la API los informa al ADMIN y al STOCK). */
  items: (tipo: TipoItem, { search, estado, page, size, orden }: FiltrosStock) =>
    api
      .get<Paginated<ItemStock>>(BASE[tipo], {
        params: {
          search: search || undefined,
          estado,
          page,
          size,
          orden: orden?.campo,
          sentido: orden?.sentido,
        },
      })
      .then((r) => r.data),

  /** Todos los activos (hasta 100) para los combos. */
  opciones: (tipo: TipoItem, soloElaborados = false) =>
    api
      .get<Paginated<ItemStock>>(BASE[tipo], {
        params: { estado: 'activos', size: 100, es_elaborado: soloElaborados || undefined },
      })
      .then((r) => r.data.items),

  movimientos: (tipo: TipoItem, id: number, page: number) =>
    api
      .get<Paginated<Movimiento>>(`${BASE[tipo]}/${id}/movimientos`, { params: { page, size: 8 } })
      .then((r) => r.data),

  /** En productos puede devolver varios movimientos (uno por lote afectado, FEFO). */
  registrar: (tipo: TipoItem, id: number, input: MovimientoInput) =>
    api.post(`${BASE[tipo]}/${id}/movimientos`, input).then(() => undefined),

  lotes: (productoId: number) =>
    api.get<Lote[]>(`/productos/${productoId}/lotes`).then((r) => r.data),

  porVencer: (dias: number) =>
    api.get<LotePorVencer[]>('/inventario/por-vencer', { params: { dias } }).then((r) => r.data),
}

export const produccionApi = {
  list: (estado: string, page: number) =>
    api
      .get<Paginated<Orden>>('/produccion', {
        params: { estado: estado || undefined, page, size: 10 },
      })
      .then((r) => r.data),

  get: (id: number) => api.get<Orden>(`/produccion/${id}`).then((r) => r.data),

  create: (input: OrdenInput) => api.post<Orden>('/produccion', input).then((r) => r.data),

  iniciar: (id: number) => api.patch<Orden>(`/produccion/${id}/iniciar`).then((r) => r.data),

  completar: (id: number, lote?: { codigo_lote: string; fecha_vencimiento: string }) =>
    api.patch<Orden>(`/produccion/${id}/completar`, lote ?? {}).then((r) => r.data),

  cancelar: (id: number, motivo: string) =>
    api.patch<Orden>(`/produccion/${id}/cancelar`, { motivo }).then((r) => r.data),
}
