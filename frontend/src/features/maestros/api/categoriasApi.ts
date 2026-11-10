import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import type { Categoria, CategoriaInput, ListParams } from '../types'

export const categoriasApi = {
  /** Listado plano y paginado del ABM (el árbol público es GET /categorias). */
  list: ({ search, estado, page, size }: ListParams) =>
    api
      .get<Paginated<Categoria>>('/categorias/lista', {
        params: { search: search || undefined, estado, page, size },
      })
      .then((r) => r.data),

  create: (input: CategoriaInput) => api.post<Categoria>('/categorias', input).then((r) => r.data),

  update: (id: number, input: CategoriaInput) =>
    api.put<Categoria>(`/categorias/${id}`, input).then((r) => r.data),

  /** Baja lógica: falla con 409 si tiene productos o subcategorías activos. */
  remove: (id: number) => api.delete(`/categorias/${id}`).then(() => undefined),

  restore: (id: number) => api.patch<Categoria>(`/categorias/${id}/reactivar`).then((r) => r.data),
}
