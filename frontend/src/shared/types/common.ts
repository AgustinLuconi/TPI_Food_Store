/** Paginación estándar de la API: ?page=1&size=20 → { items, total, page, size, pages }. */
export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

/** Formato de error estándar de la API. */
export interface ApiErrorBody {
  detail: string
  code: string
  field?: string | null
}

/** Filtro de estado de las pantallas de maestros: Activos (por defecto), Inactivos o Todos. */
export type EstadoFiltro = 'activos' | 'inactivos' | 'todos'
