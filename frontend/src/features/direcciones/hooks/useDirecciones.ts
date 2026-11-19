import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { direccionesApi } from '../api/direccionesApi'
import type { DireccionInput } from '../types'

export const direccionesKeys = { all: ['direcciones'] as const }

export function useDirecciones() {
  return useQuery({ queryKey: direccionesKeys.all, queryFn: direccionesApi.list })
}

function useInvalidar() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: direccionesKeys.all })
}

export function useGuardarDireccion() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ id, input }: { id?: number; input: DireccionInput }) =>
      id === undefined ? direccionesApi.create(input) : direccionesApi.update(id, input),
    onSuccess: invalidar,
  })
}

export function useEliminarDireccion() {
  const invalidar = useInvalidar()
  return useMutation({ mutationFn: direccionesApi.remove, onSuccess: invalidar })
}

export function useMarcarPrincipal() {
  const invalidar = useInvalidar()
  return useMutation({ mutationFn: direccionesApi.setPrincipal, onSuccess: invalidar })
}
