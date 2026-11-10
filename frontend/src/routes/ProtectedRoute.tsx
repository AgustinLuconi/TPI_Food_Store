import { Navigate, Outlet, useLocation } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { Spinner } from '@/shared/ui/Spinner'
import { useAuthStore } from '@/store/authStore'

/**
 * Mientras se verifica la sesión muestra un indicador de carga; sin sesión redirige a /login
 * recordando a dónde quería ir el usuario.
 */
export function ProtectedRoute() {
  const status = useAuthStore((s) => s.status)
  const location = useLocation()

  if (status === 'checking') return <Spinner label="Verificando sesión…" />
  if (status === 'anonymous') {
    return (
      <Navigate to={RUTAS.login} replace state={{ from: location.pathname + location.search }} />
    )
  }
  return <Outlet />
}
