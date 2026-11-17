export interface Local {
  nombre: string
  zona_horaria: string
  direccion_origen: string | null
  lat_origen: number | null
  lng_origen: number | null
}

export interface Horario {
  id: number
  dia_semana: number
  hora_apertura: string
  hora_cierre: string
  activo: boolean
}

export interface HorarioInput {
  dia_semana: number
  hora_apertura: string
  hora_cierre: string
  activo: boolean
}

export interface DiaBloqueado {
  id: number
  fecha: string
  motivo: string | null
  todo_el_dia: boolean
  hora_desde: string | null
  hora_hasta: string | null
}

export interface DiaBloqueadoInput {
  fecha: string
  motivo: string | null
  todo_el_dia: boolean
  hora_desde: string | null
  hora_hasta: string | null
}

/** Un vértice del polígono: [latitud, longitud]. */
export type Vertice = [number, number]

export interface Zona {
  id: number
  nombre: string
  poligono: Vertice[]
  tarifa_base: string
  tarifa_por_km: string
  pedido_minimo: string
  activo: boolean
}

export interface ZonaInput {
  nombre: string
  poligono: Vertice[]
  tarifa_base: string
  tarifa_por_km: string
  pedido_minimo: string
  activo?: boolean
}

export interface EstadoLocal {
  abierto: boolean
  proxima_apertura: string | null
  zona_horaria: string
}

export const DIAS = [
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
] as const
