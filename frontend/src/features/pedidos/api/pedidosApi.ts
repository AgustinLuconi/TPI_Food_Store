import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import type {
  Cotizacion,
  EstadoPedido,
  FiltrosPedidos,
  FormaDePago,
  Pedido,
  PedidoItem,
  PedidoNuevo,
} from '../types'

export const pedidosApi = {
  /** Propios (CLIENT) o todos (ADMIN, PEDIDOS). */
  list: ({ estado, page, size }: FiltrosPedidos) =>
    api
      .get<Paginated<PedidoItem>>('/pedidos', {
        params: { estado: estado || undefined, page, size },
      })
      .then((r) => r.data),

  /** Listado del personal: además del estado, filtra por fechas (días del calendario del local). */
  listGestion: ({
    estado,
    page,
    size,
    desde,
    hasta,
  }: FiltrosPedidos & { desde?: string; hasta?: string }) =>
    api
      .get<Paginated<PedidoItem>>('/pedidos', {
        params: {
          estado: estado || undefined,
          page,
          size,
          desde: desde || undefined,
          hasta: hasta || undefined,
        },
      })
      .then((r) => r.data),

  get: (id: number) => api.get<Pedido>(`/pedidos/${id}`).then((r) => r.data),

  /** La Idempotency-Key se genera UNA vez por intento: un doble clic devuelve el mismo pedido. */
  create: (body: PedidoNuevo, idempotencyKey: string) =>
    api
      .post<Pedido>('/pedidos', body, { headers: { 'Idempotency-Key': idempotencyKey } })
      .then((r) => r.data),

  cancel: (id: number, motivo: string) =>
    api.post<Pedido>(`/pedidos/${id}/cancelar`, { motivo }).then((r) => r.data),

  changeState: (id: number, estado: EstadoPedido) =>
    api.patch<Pedido>(`/pedidos/${id}/estado`, { estado }).then((r) => r.data),

  /** Fuera de toda zona responde 422 OUTSIDE_COVERAGE: no existe una cotización. */
  quote: (lat: number, lng: number, subtotal: number) =>
    api
      .post<Cotizacion>('/envio/cotizar', { lat, lng, subtotal: subtotal.toFixed(2) })
      .then((r) => r.data),

  paymentMethods: () => api.get<FormaDePago[]>('/pagos/formas').then((r) => r.data),

  /** Registro manual (efectivo o transferencia) por el personal. Confirma el pedido en la misma transacción. */
  registerPayment: (pedidoId: number, monto: string, idempotencyKey: string) =>
    api
      .post(`/pagos/${pedidoId}`, { monto }, { headers: { 'Idempotency-Key': idempotencyKey } })
      .then((r) => r.data),
}
