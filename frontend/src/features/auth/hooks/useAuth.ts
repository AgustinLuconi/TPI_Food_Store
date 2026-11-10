import { useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { queryClient } from '@/shared/api/queryClient'
import { useAuthStore } from '@/store/authStore'
import { useCartStore } from '@/store/cartStore'
import { usePaymentStore } from '@/store/paymentStore'
import { authApi } from '../api/authApi'

export const authKeys = { me: ['auth', 'me'] as const }

/**
 * Verificación inicial de la sesión: GET /auth/me reconstruye el authStore al recargar.
 * `enabled` la limita a UNA consulta: después de un logout no se vuelve a pedir.
 */
export function useSessionBootstrap(): void {
  const status = useAuthStore((s) => s.status)
  const setUsuario = useAuthStore((s) => s.setUsuario)
  const setAnonymous = useAuthStore((s) => s.setAnonymous)

  const { data, isSuccess, isError } = useQuery({
    queryKey: authKeys.me,
    queryFn: authApi.me,
    enabled: status === 'checking',
    retry: false,
    staleTime: Infinity,
  })

  useEffect(() => {
    if (isSuccess) setUsuario(data)
    else if (isError) setAnonymous()
  }, [isSuccess, isError, data, setUsuario, setAnonymous])
}

export function useLogin() {
  const setUsuario = useAuthStore((s) => s.setUsuario)
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (usuario) => setUsuario(usuario),
  })
}

export function useRegister() {
  return useMutation({ mutationFn: authApi.register })
}

export function useChangePassword() {
  return useMutation({ mutationFn: authApi.changePassword })
}

/** Limpia TODO el estado de la sesión: store, carrito (se vacía al cerrar sesión) y caché. */
export function limpiarSesionLocal(): void {
  useAuthStore.getState().clear()
  useCartStore.getState().clear()
  usePaymentStore.getState().reset()
  queryClient.clear()
}

export function useLogout() {
  return useMutation({
    mutationFn: authApi.logout,
    // Aunque el servidor falle (sesión ya expirada), la sesión local siempre se limpia.
    onSettled: limpiarSesionLocal,
  })
}
