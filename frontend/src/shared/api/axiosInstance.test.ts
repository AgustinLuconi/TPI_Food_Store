import { AxiosError, type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api, setSessionExpiredHandler } from './axiosInstance'
import { ApiError } from './errors'

// Servidor simulado: /data exige sesión; /auth/refresh la renueva (o falla si refreshOk es false).
let autenticado = false
let refreshOk = true
let refreshes = 0
let forbidden = false

function respuesta(config: InternalAxiosRequestConfig, status: number, data: unknown = {}) {
  return { data, status, statusText: '', headers: {}, config }
}

const adaptador: AxiosAdapter = async (config) => {
  const url = config.url ?? ''
  if (url.includes('/auth/refresh')) {
    refreshes += 1
    await new Promise((r) => setTimeout(r, 20)) // los demás 401 llegan mientras el refresh está en curso
    if (!refreshOk) {
      throw new AxiosError(
        'expirada',
        'ERR_BAD_REQUEST',
        config,
        null,
        respuesta(config, 401, { detail: 'Expirada', code: 'INVALID_TOKEN' }),
      )
    }
    autenticado = true
    return respuesta(config, 200)
  }
  if (forbidden) {
    throw new AxiosError(
      'prohibido',
      'ERR_BAD_REQUEST',
      config,
      null,
      respuesta(config, 403, { detail: 'Sin permiso', code: 'INSUFFICIENT_ROLE' }),
    )
  }
  if (!autenticado) {
    throw new AxiosError(
      'no autenticado',
      'ERR_BAD_REQUEST',
      config,
      null,
      respuesta(config, 401, { detail: 'No autenticado', code: 'NOT_AUTHENTICATED' }),
    )
  }
  return respuesta(config, 200, { ok: true })
}

describe('axiosInstance: renovación de sesión ante 401', () => {
  const alExpirar = vi.fn()

  beforeEach(() => {
    autenticado = false
    refreshOk = true
    refreshes = 0
    forbidden = false
    alExpirar.mockReset()
    api.defaults.adapter = adaptador
    setSessionExpiredHandler(alExpirar)
  })

  it('varios 401 simultáneos comparten UN solo refresh y todos se reintentan', async () => {
    const respuestas = await Promise.all(Array.from({ length: 5 }, () => api.get('/data')))
    expect(respuestas.every((r) => r.status === 200)).toBe(true)
    // Con la rotación del refresh token, un segundo refresh usaría un token ya revocado.
    expect(refreshes).toBe(1)
    expect(alExpirar).not.toHaveBeenCalled()
  })

  it('si el refresh falla, avisa una vez para limpiar la sesión y propaga el 401', async () => {
    refreshOk = false
    const resultados = await Promise.allSettled([api.get('/data'), api.get('/data')])
    expect(resultados.every((r) => r.status === 'rejected')).toBe(true)
    const error = (resultados[0] as PromiseRejectedResult).reason as ApiError
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(401)
    expect(refreshes).toBe(1)
    expect(alExpirar).toHaveBeenCalled()
  })

  it('un 403 NUNCA cierra la sesión ni intenta refrescar', async () => {
    forbidden = true
    const error = await api.get('/data').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(403)
    expect((error as ApiError).code).toBe('INSUFFICIENT_ROLE')
    expect(refreshes).toBe(0)
    expect(alExpirar).not.toHaveBeenCalled()
  })

  it('el login con credenciales inválidas no dispara un refresh', async () => {
    const error = await api.post('/auth/token', {}).catch((e: unknown) => e)
    expect((error as ApiError).status).toBe(401)
    expect(refreshes).toBe(0)
  })

  it('silentAuth: si el refresh falla no expulsa al usuario (verificación inicial en /auth/me)', async () => {
    refreshOk = false
    await expect(api.get('/data', { silentAuth: true })).rejects.toBeInstanceOf(ApiError)
    expect(alExpirar).not.toHaveBeenCalled()
  })

  it('reintenta una sola vez: no entra en bucle si el servidor sigue respondiendo 401', async () => {
    // El refresh "funciona" pero el servidor sigue negando el acceso.
    api.defaults.adapter = async (config) => {
      if ((config.url ?? '').includes('/auth/refresh')) {
        refreshes += 1
        return respuesta(config, 200)
      }
      throw new AxiosError(
        'no',
        'ERR_BAD_REQUEST',
        config,
        null,
        respuesta(config, 401, { detail: 'No', code: 'X' }),
      )
    }
    await expect(api.get('/data')).rejects.toBeInstanceOf(ApiError)
    expect(refreshes).toBe(1)
  })
})
