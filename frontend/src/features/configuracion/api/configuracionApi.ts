import { api } from '@/shared/api/axiosInstance'
import type {
  DiaBloqueado,
  DiaBloqueadoInput,
  EstadoLocal,
  Horario,
  HorarioInput,
  Local,
  Zona,
  ZonaInput,
} from '../types'

export const configuracionApi = {
  estadoLocal: () => api.get<EstadoLocal>('/config/estado-local').then((r) => r.data),

  local: () => api.get<Local>('/config/local').then((r) => r.data),
  saveLocal: (input: Local) => api.put<Local>('/config/local', input).then((r) => r.data),

  horarios: () => api.get<Horario[]>('/config/horarios').then((r) => r.data),
  /** Reemplaza TODAS las franjas. */
  saveHorarios: (items: HorarioInput[]) =>
    api.put<Horario[]>('/config/horarios', { items }).then((r) => r.data),

  diasBloqueados: () => api.get<DiaBloqueado[]>('/config/dias-bloqueados').then((r) => r.data),
  createDia: (input: DiaBloqueadoInput) =>
    api.post<DiaBloqueado>('/config/dias-bloqueados', input).then((r) => r.data),
  removeDia: (id: number) => api.delete(`/config/dias-bloqueados/${id}`).then(() => undefined),

  zonas: (activo?: boolean) =>
    api.get<Zona[]>('/config/zonas', { params: { activo } }).then((r) => r.data),
  createZona: (input: ZonaInput) => api.post<Zona>('/config/zonas', input).then((r) => r.data),
  updateZona: (id: number, input: Partial<ZonaInput>) =>
    api.put<Zona>(`/config/zonas/${id}`, input).then((r) => r.data),
  /** Baja: activo = false. Se reactiva con updateZona({ activo: true }). */
  removeZona: (id: number) => api.delete(`/config/zonas/${id}`).then(() => undefined),
}
