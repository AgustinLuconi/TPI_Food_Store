import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Rol, Usuario } from '@/shared/types/auth'
import { usuariosApi } from '../api/usuariosApi'
import type { ListParams, UsuarioCreateInput, UsuarioUpdateInput } from '../types'

export const usuariosKeys = {
  all: ['usuarios'] as const,
  list: (params: ListParams) => ['usuarios', 'lista', params] as const,
}

export function useUsuarios(params: ListParams) {
  return useQuery({
    queryKey: usuariosKeys.list(params),
    queryFn: () => usuariosApi.list(params),
    placeholderData: keepPreviousData,
  })
}

function useInvalidarUsuarios() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: usuariosKeys.all })
}

interface GuardarUsuarioArgs {
  /** Sin id: alta. Con id: edición de datos y, si cambiaron, de roles. */
  usuario?: Usuario
  datos: UsuarioUpdateInput
  roles: Rol[]
  password?: string
}

export function useGuardarUsuario() {
  const invalidar = useInvalidarUsuarios()
  return useMutation({
    mutationFn: async ({ usuario, datos, roles, password }: GuardarUsuarioArgs) => {
      if (!usuario) {
        const alta: UsuarioCreateInput = { ...datos, password: password ?? '', roles }
        return usuariosApi.create(alta)
      }
      let actualizado = await usuariosApi.update(usuario.id, datos)
      const mismosRoles =
        roles.length === usuario.roles.length && roles.every((r) => usuario.roles.includes(r))
      if (!mismosRoles) actualizado = await usuariosApi.setRoles(usuario.id, roles)
      return actualizado
    },
    onSuccess: invalidar,
  })
}

export function useBloquearUsuario() {
  const invalidar = useInvalidarUsuarios()
  return useMutation({
    mutationFn: ({ id, disabled }: { id: number; disabled: boolean }) =>
      usuariosApi.setEstado(id, disabled),
    onSuccess: invalidar,
  })
}

export function useAnularUsuario() {
  const invalidar = useInvalidarUsuarios()
  return useMutation({ mutationFn: usuariosApi.remove, onSuccess: invalidar })
}

export function useReactivarUsuario() {
  const invalidar = useInvalidarUsuarios()
  return useMutation({ mutationFn: usuariosApi.restore, onSuccess: invalidar })
}
