import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { configuracionApi } from '../api/configuracionApi'
import type { DiaBloqueadoInput, HorarioInput, Local, ZonaInput } from '../types'

const KEY = ['configuracion'] as const

export const useLocal = () =>
  useQuery({ queryKey: [...KEY, 'local'], queryFn: configuracionApi.local })
export const useHorarios = () =>
  useQuery({ queryKey: [...KEY, 'horarios'], queryFn: configuracionApi.horarios })
export const useDiasBloqueados = () =>
  useQuery({ queryKey: [...KEY, 'dias'], queryFn: configuracionApi.diasBloqueados })
export const useZonas = (activo?: boolean) =>
  useQuery({ queryKey: [...KEY, 'zonas', activo], queryFn: () => configuracionApi.zonas(activo) })
export const useEstadoLocal = () =>
  useQuery({
    queryKey: [...KEY, 'estado'],
    queryFn: configuracionApi.estadoLocal,
    refetchInterval: 60_000,
  })

/** Cualquier cambio invalida la configuración entera: el estado del local depende de todo lo demás. */
function useInvalidar() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: KEY })
}

export function useGuardarLocal() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: (input: Local) => configuracionApi.saveLocal(input),
    onSuccess: invalidar,
  })
}

export function useGuardarHorarios() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: (items: HorarioInput[]) => configuracionApi.saveHorarios(items),
    onSuccess: invalidar,
  })
}

export function useCrearDiaBloqueado() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: (input: DiaBloqueadoInput) => configuracionApi.createDia(input),
    onSuccess: invalidar,
  })
}

export function useEliminarDiaBloqueado() {
  const invalidar = useInvalidar()
  return useMutation({ mutationFn: configuracionApi.removeDia, onSuccess: invalidar })
}

export function useGuardarZona() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: ({ id, input }: { id?: number; input: ZonaInput }) =>
      id === undefined
        ? configuracionApi.createZona(input)
        : configuracionApi.updateZona(id, input),
    onSuccess: invalidar,
  })
}

export function useAnularZona() {
  const invalidar = useInvalidar()
  return useMutation({ mutationFn: configuracionApi.removeZona, onSuccess: invalidar })
}

export function useReactivarZona() {
  const invalidar = useInvalidar()
  return useMutation({
    mutationFn: (id: number) => configuracionApi.updateZona(id, { activo: true }),
    onSuccess: invalidar,
  })
}
