import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { toApiError } from './errors'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** Si el refresh falla, no dispara el cierre de sesión (p. ej. la verificación inicial en /auth/me). */
    silentAuth?: boolean
  }
}

export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** El JWT viaja en una cookie HttpOnly: withCredentials la adjunta; el header Authorization no se usa. */
export const api = axios.create({ baseURL: API_URL, withCredentials: true })

// Endpoints donde un 401 significa "credenciales/sesión inválidas" y NO debe intentar refrescar.
const SIN_REFRESH = ['/auth/token', '/auth/refresh', '/auth/register']

type Reintentable = InternalAxiosRequestConfig & { _reintentado?: boolean }

/**
 * Refresh compartido: con la rotación del refresh token, un segundo refresh usaría un token ya
 * revocado. Por eso varios 401 simultáneos esperan UNA sola promesa.
 */
let refreshEnCurso: Promise<void> | null = null

function refrescarSesion(): Promise<void> {
  refreshEnCurso ??= api
    .post('/auth/refresh')
    .then(() => undefined)
    .finally(() => {
      refreshEnCurso = null
    })
  return refreshEnCurso
}

// La capa de API no conoce los stores ni el router: quien arranca la app registra qué hacer
// cuando la sesión no se puede recuperar (limpiar el store y redirigir a /login).
let alExpirarSesion: () => void = () => {}

export function setSessionExpiredHandler(handler: () => void): void {
  alExpirarSesion = handler
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as Reintentable | undefined
    const esperaRefresh =
      error.response?.status === 401 &&
      original !== undefined &&
      !original._reintentado &&
      !SIN_REFRESH.some((ruta) => original.url?.includes(ruta))

    // Un 403 (sin el rol requerido) NUNCA cierra la sesión: se propaga como cualquier otro error.
    if (!esperaRefresh) throw toApiError(error)

    original._reintentado = true
    try {
      await refrescarSesion()
    } catch {
      if (!original.silentAuth) alExpirarSesion()
      throw toApiError(error)
    }
    return api(original) // reintenta UNA vez
  },
)
