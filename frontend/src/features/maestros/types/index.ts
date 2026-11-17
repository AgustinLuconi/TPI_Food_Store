import type { Rol } from '@/shared/types/auth'
import type { EstadoFiltro, Orden } from '@/shared/types/common'

export interface ListParams {
  search: string
  estado: EstadoFiltro
  page: number
  size: number
  /** Valor del combo de agrupación: un rol en usuarios; una categoría padre (o "raiz") en categorías. */
  grupo?: string
  orden?: Orden
}

/** Valor del combo de agrupación de categorías que pide solo las raíces. */
export const GRUPO_RAIZ = 'raiz'

/** Nodo del árbol público de categorías (GET /categorias). */
export interface CategoriaNodo {
  id: number
  parent_id: number | null
  nombre: string
  descripcion: string | null
  children: CategoriaNodo[]
}

export interface Categoria {
  id: number
  parent_id: number | null
  nombre: string
  descripcion: string | null
  created_at: string
  deleted_at: string | null
  /** El servidor lo completa en los listados: el padre puede estar en otra página. */
  parent_nombre: string | null
}

export interface CategoriaInput {
  nombre: string
  descripcion: string | null
  parent_id: number | null
}

export interface UsuarioCreateInput {
  nombre: string
  apellido: string
  email: string
  telefono: string | null
  password: string
  roles: Rol[]
}

export interface UsuarioUpdateInput {
  nombre: string
  apellido: string
  email: string
  telefono: string | null
}
