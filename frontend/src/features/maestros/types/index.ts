import type { Rol } from '@/shared/types/auth'
import type { EstadoFiltro } from '@/shared/types/common'

export interface ListParams {
  search: string
  estado: EstadoFiltro
  page: number
  size: number
  rol?: string
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
