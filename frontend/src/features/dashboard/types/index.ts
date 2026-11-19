export interface Resumen {
  fecha: string
  ventas_del_dia: string
  pedidos_pagados_del_dia: number
  ticket_promedio: string
  pedidos_del_dia: number
  pedidos_por_estado: Record<string, number>
  pagos_por_estado: Record<string, number>
  stock_bajo: { productos: number; insumos: number }
}

export interface PuntoDeVentas {
  fecha: string
  total: string
  pedidos: number
}

export interface Ventas {
  desde: string
  hasta: string
  total: string
  pedidos: number
  serie: PuntoDeVentas[]
}

export interface TopProducto {
  producto_id: number
  nombre: string
  unidades: number
  ingresos: string
}

export interface ItemStockBajo {
  id: number
  nombre: string
  stock_minimo: number
  stock_real: string
  stock_disponible: string
}

export interface LoteQueVence {
  id: number
  codigo_lote: string
  producto_nombre: string
  fecha_vencimiento: string
  dias_restantes: number
  stock_real: string
  vencido: boolean
}

export interface StockBajo {
  productos: ItemStockBajo[]
  insumos: ItemStockBajo[]
  dias: number
  lotes_por_vencer: LoteQueVence[]
}

export interface MermaPorMotivo {
  motivo: string
  cantidad: string
  movimientos: number
}

export interface Mermas {
  desde: string
  hasta: string
  productos: MermaPorMotivo[]
  insumos: MermaPorMotivo[]
}

/** Lo mínimo de un pedido o de una orden para las colas del panel. */
export interface FilaDeCola {
  id: number
  titulo: string
  detalle: string
}
