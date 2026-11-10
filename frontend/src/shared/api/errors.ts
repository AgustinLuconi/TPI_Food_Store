import { isAxiosError } from 'axios'
import type { ApiErrorBody } from '@/shared/types/common'

/** Error normalizado de la API: status HTTP + código de negocio + campo opcional. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly field: string | null

  constructor(message: string, status: number, code: string, field: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.field = field
  }
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (isAxiosError<Partial<ApiErrorBody>>(error)) {
    if (!error.response) {
      return new ApiError('No se pudo conectar con el servidor', 0, 'NETWORK_ERROR')
    }
    const { status, data } = error.response
    return new ApiError(
      data?.detail ?? 'Ocurrió un error inesperado',
      status,
      data?.code ?? 'HTTP_ERROR',
      data?.field ?? null,
    )
  }
  return new ApiError(error instanceof Error ? error.message : 'Error desconocido', 0, 'UNKNOWN')
}

export function getErrorMessage(error: unknown): string {
  return toApiError(error).message
}
