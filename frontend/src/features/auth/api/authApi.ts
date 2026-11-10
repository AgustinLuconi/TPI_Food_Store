import { api } from '@/shared/api/axiosInstance'
import type { Usuario } from '@/shared/types/auth'
import type { ChangePasswordPayload, RegisterPayload } from '../types'

export const authApi = {
  /** OAuth2 Password Flow: x-www-form-urlencoded con `username` (el email) y `password`. */
  login: (email: string, password: string) =>
    api
      .post<Usuario>('/auth/token', new URLSearchParams({ username: email, password }))
      .then((r) => r.data),

  register: (payload: RegisterPayload) =>
    api.post<Usuario>('/auth/register', payload).then((r) => r.data),

  /** Verificación inicial: si no hay sesión no es un error que deba expulsar al usuario. */
  me: () => api.get<Usuario>('/auth/me', { silentAuth: true }).then((r) => r.data),

  logout: () => api.post('/auth/logout').then(() => undefined),

  changePassword: (payload: ChangePasswordPayload) =>
    api.put<Usuario>('/auth/password', payload).then((r) => r.data),
}
