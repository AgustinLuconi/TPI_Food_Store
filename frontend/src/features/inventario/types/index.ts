export type TipoMovimiento =
  | 'ENTRADA'
  | 'SALIDA'
  | 'RESERVA'
  | 'LIBERACION_RESERVA'
  | 'MERMA'
  | 'AJUSTE_POSITIVO'
  | 'AJUSTE_NEGATIVO'

/** Los únicos tipos que se cargan a mano (RN-07); el resto los genera el sistema. */
export const TIPOS_MANUALES = ['ENTRADA', 'MERMA', 'AJUSTE_POSITIVO', 'AJUSTE_NEGATIVO'] as const
export type TipoManual = (typeof TIPOS_MANUALES)[number]

export const NOMBRE_TIPO: Record<TipoMovimiento, string> = {
  ENTRADA: 'Entrada',
  SALIDA: 'Salida',
  RESERVA: 'Reserva',
  LIBERACION_RESERVA: 'Liberación de reserva',
  MERMA: 'Merma',
  AJUSTE_POSITIVO: 'Ajuste positivo',
  AJUSTE_NEGATIVO: 'Ajuste negativo',
}

/** RN-08: la merma exige uno de estos motivos. */
export const MOTIVOS_MERMA = [
  'VENCIMIENTO',
  'ROTURA',
  'CONSUMO_INTERNO',
  'ERROR_PRODUCCION',
] as const

export const NOMBRE_MOTIVO: Record<(typeof MOTIVOS_MERMA)[number], string> = {
  VENCIMIENTO: 'Vencimiento',
  ROTURA: 'Rotura',
  CONSUMO_INTERNO: 'Consumo interno',
  ERROR_PRODUCCION: 'Error de producción',
}

export type TipoItem = 'producto' | 'ingrediente'

export interface ItemStock {
  id: number
  nombre: string
  stock_minimo: number
  stock_real: string | null
  stock_disponible: string | null
  deleted_at: string | null
}

export interface Movimiento {
  id: number
  tipo_movimiento: TipoMovimiento
  cantidad: string
  motivo: string | null
  fecha_registro: string
  lote_id: number | null
  pedido_id: number | null
  orden_produccion_id: number | null
}

export interface MovimientoInput {
  tipo_movimiento: TipoManual
  cantidad: string
  motivo: string | null
  codigo_lote?: string | null
  fecha_vencimiento?: string | null
}

export interface Lote {
  id: number
  codigo_lote: string
  fecha_vencimiento: string
  fecha_ingreso: string
  cantidad_inicial: string
  stock_real: string
  stock_disponible: string
  vencido: boolean
}

export interface LotePorVencer extends Lote {
  producto_id: number
  producto_nombre: string
  dias_restantes: number
}

export type EstadoOrden = 'PLANIFICADA' | 'EN_PROCESO' | 'COMPLETADA' | 'CANCELADA'

export const ESTADOS_ORDEN: EstadoOrden[] = ['PLANIFICADA', 'EN_PROCESO', 'COMPLETADA', 'CANCELADA']

export interface ComponenteOrden {
  ingrediente_id: number
  nombre: string
  cantidad: string
  unidad_medida: string | null
}

export interface Orden {
  id: number
  producto_id: number | null
  ingrediente_id: number | null
  nombre: string
  cantidad_a_producir: string
  estado: EstadoOrden
  motivo_cancelacion: string | null
  created_at: string
  updated_at: string
  componentes: ComponenteOrden[]
}

export interface OrdenInput {
  producto_id?: number
  ingrediente_id?: number
  cantidad_a_producir: string
}

export interface FiltrosStock {
  search: string
  estado: 'activos' | 'inactivos' | 'todos'
  page: number
  size: number
  orden?: { campo: string; sentido: 'asc' | 'desc' }
}
