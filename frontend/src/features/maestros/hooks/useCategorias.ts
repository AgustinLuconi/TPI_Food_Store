import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { categoriasApi } from '../api/categoriasApi'
import type { CategoriaInput, ListParams } from '../types'

export const categoriasKeys = {
  all: ['categorias'] as const,
  list: (params: ListParams) => ['categorias', 'lista', params] as const,
}

export function useCategorias(params: ListParams, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: categoriasKeys.list(params),
    queryFn: () => categoriasApi.list(params),
    placeholderData: keepPreviousData, // evita parpadeos al paginar o filtrar
    enabled: options.enabled ?? true,
  })
}

/** Toda mutación invalida las consultas de categorías (listado y selectores). */
function useInvalidarCategorias() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: categoriasKeys.all })
}

export function useGuardarCategoria() {
  const invalidar = useInvalidarCategorias()
  return useMutation({
    mutationFn: ({ id, input }: { id?: number; input: CategoriaInput }) =>
      id === undefined ? categoriasApi.create(input) : categoriasApi.update(id, input),
    onSuccess: invalidar,
  })
}

export function useAnularCategoria() {
  const invalidar = useInvalidarCategorias()
  return useMutation({ mutationFn: categoriasApi.remove, onSuccess: invalidar })
}

export function useReactivarCategoria() {
  const invalidar = useInvalidarCategorias()
  return useMutation({ mutationFn: categoriasApi.restore, onSuccess: invalidar })
}
