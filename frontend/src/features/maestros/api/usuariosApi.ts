import { api } from '@/shared/api/axiosInstance'
import type { Rol, Usuario } from '@/shared/types/auth'
import type { Paginated } from '@/shared/types/common'
import type { ListParams, UsuarioCreateInput, UsuarioUpdateInput } from '../types'

export const usuariosApi = {
  list: ({ search, estado, page, size, rol }: ListParams) =>
    api
      .get<Paginated<Usuario>>('/usuarios', {
        params: { search: search || undefined, rol: rol || undefined, estado, page, size },
      })
      .then((r) => r.data),

  create: (input: UsuarioCreateInput) => api.post<Usuario>('/usuarios', input).then((r) => r.data),

  update: (id: number, input: UsuarioUpdateInput) =>
    api.put<Usuario>(`/usuarios/${id}`, input).then((r) => r.data),

  /** Reemplaza los roles y registra quién los asignó. */
  setRoles: (id: number, roles: Rol[]) =>
    api.put<Usuario>(`/usuarios/${id}/roles`, { roles }).then((r) => r.data),

  /** Bloquea o desbloquea (disabled). Es independiente de la baja lógica. */
  setEstado: (id: number, disabled: boolean) =>
    api.patch<Usuario>(`/usuarios/${id}/estado`, { disabled }).then((r) => r.data),

  remove: (id: number) => api.delete(`/usuarios/${id}`).then(() => undefined),

  restore: (id: number) => api.patch<Usuario>(`/usuarios/${id}/reactivar`).then((r) => r.data),
}
