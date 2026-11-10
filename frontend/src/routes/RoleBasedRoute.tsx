import { Navigate, Outlet } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import type { Rol } from '@/shared/types/auth'
import { useAuthStore } from '@/store/authStore'

/**
 * Compara `allowedRoles` con los roles del usuario; sin el rol, redirige a /unauthorized.
 * Es solo una ayuda de interfaz: la autorización real la hace el backend en cada request.
 */
export function RoleBasedRoute({ allowedRoles }: { allowedRoles: readonly Rol[] }) {
  const permitido = useAuthStore((s) => s.hasRole(...allowedRoles))
  return permitido ? <Outlet /> : <Navigate to={RUTAS.noAutorizado} replace />
}
