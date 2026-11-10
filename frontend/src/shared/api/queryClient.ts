import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './errors'

/** Instancia única de TanStack Query (estado del servidor: caché e invalidación). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Los errores 4xx son definitivos (permisos, validación): reintentar no los arregla.
      retry: (cantidad, error) =>
        cantidad < 2 && !(error instanceof ApiError && error.status >= 400 && error.status < 500),
    },
    mutations: { retry: false },
  },
})
