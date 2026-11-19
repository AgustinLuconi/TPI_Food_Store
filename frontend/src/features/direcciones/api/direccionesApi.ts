import { api } from '@/shared/api/axiosInstance'
import type { Direccion, DireccionInput } from '../types'

export const direccionesApi = {
  list: () => api.get<Direccion[]>('/direcciones').then((r) => r.data),
  create: (input: DireccionInput) => api.post<Direccion>('/direcciones', input).then((r) => r.data),
  update: (id: number, input: Partial<DireccionInput>) =>
    api.put<Direccion>(`/direcciones/${id}`, input).then((r) => r.data),
  /** Baja lógica. */
  remove: (id: number) => api.delete(`/direcciones/${id}`).then(() => undefined),
  setPrincipal: (id: number) =>
    api.patch<Direccion>(`/direcciones/${id}/principal`).then((r) => r.data),
}
