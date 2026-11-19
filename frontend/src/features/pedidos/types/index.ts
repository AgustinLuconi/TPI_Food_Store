export type EstadoPedido =
  'PENDIENTE' | 'CONFIRMADO' | 'EN_PREPARACION' | 'EN_CAMINO' | 'ENTREGADO' | 'CANCELADO'

export const ESTADOS_PEDIDO: EstadoPedido[] = [
  'PENDIENTE',
  'CONFIRMADO',
  'EN_PREPARACION',
  'EN_CAMINO',
  'ENTREGADO',
  'CANCELADO',
]

export interface PedidoItem {
  id: number
  usuario_id: number
  cliente_nombre: string
  estado_codigo: EstadoPedido
  forma_pago_codigo: string
  total: string
  con_envio: boolean
  created_at: string
}

export interface LineaDePedido {
  id: number
  producto_id: number
  nombre_snapshot: string
  precio_snapshot: string
  cantidad: number
  subtotal: string
  exclusiones: { ingrediente_id: number; nombre: string }[]
}

export interface HistorialItem {
  id: number
  estado_desde: EstadoPedido | null
  estado_hasta: EstadoPedido
  usuario_id: number | null
  motivo: string | null
  created_at: string
}

export interface PagoDelPedido {
  id: number
  forma_pago_codigo: string
  monto: string
  mp_status: string
  created_at: string
}

export interface Pedido {
  id: number
  usuario_id: number
  cliente_nombre: string
  estado_codigo: EstadoPedido
  forma_pago_codigo: string
  direccion_id: number | null
  direccion: {
    linea1: string
    linea2: string | null
    ciudad: string | null
    provincia: string | null
  } | null
  subtotal: string
  descuento: string
  costo_envio: string
  total: string
  notas: string | null
  external_reference: string
  created_at: string
  updated_at: string
  lineas: LineaDePedido[]
  pago: PagoDelPedido | null
  historial: HistorialItem[]
}

export interface PedidoNuevo {
  items: { producto_id: number; cantidad: number; exclusiones: number[] }[]
  forma_pago_codigo: string
  direccion_id: number | null
  notas: string | null
}

export interface Cotizacion {
  dentro_de_cobertura: boolean
  zona: { id: number; nombre: string; pedido_minimo: string }
  distancia_km: number
  costo_envio: string
  cumple_minimo: boolean
}

export interface FormaDePago {
  codigo: string
  nombre: string
}

export interface FiltrosPedidos {
  estado: EstadoPedido | ''
  page: number
  size: number
}
