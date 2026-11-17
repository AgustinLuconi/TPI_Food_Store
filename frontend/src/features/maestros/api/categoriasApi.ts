import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import {
  GRUPO_RAIZ,
  type Categoria,
  type CategoriaInput,
  type CategoriaNodo,
  type ListParams,
} from '../types'

export const categoriasApi = {
  /** Listado plano y paginado del ABM. El combo de agrupación es la categoría padre (o solo raíces). */
  list: ({ search, estado, page, size, grupo, orden }: ListParams) =>
    api
      .get<Paginated<Categoria>>('/categorias/lista', {
        params: {
          search: search || undefined,
          estado,
          page,
          size,
          raiz: grupo === GRUPO_RAIZ || undefined,
          parent_id: grupo && grupo !== GRUPO_RAIZ ? Number(grupo) : undefined,
          orden: orden?.campo,
          sentido: orden?.sentido,
        },
      })
      .then((r) => r.data),

  /** Árbol completo de categorías activas (público, sin paginar): alimenta los combos. */
  arbol: () => api.get<CategoriaNodo[]>('/categorias').then((r) => r.data),

  create: (input: CategoriaInput) => api.post<Categoria>('/categorias', input).then((r) => r.data),

  update: (id: number, input: CategoriaInput) =>
    api.put<Categoria>(`/categorias/${id}`, input).then((r) => r.data),

  /** Baja lógica: falla con 409 si tiene productos o subcategorías activos. */
  remove: (id: number) => api.delete(`/categorias/${id}`).then(() => undefined),

  restore: (id: number) => api.patch<Categoria>(`/categorias/${id}/reactivar`).then((r) => r.data),
}
