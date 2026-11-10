import { Suspense } from 'react'
import { Outlet, useNavigate } from 'react-router'
import { useLogout } from '@/features/auth/hooks/useAuth'
import { ConfirmHost } from '@/shared/components/ConfirmHost'
import { AdminLayout } from '@/shared/layout/AdminLayout'
import { PublicLayout } from '@/shared/layout/PublicLayout'
import { RUTAS } from '@/shared/lib/rutas'
import { Spinner } from '@/shared/ui/Spinner'

/**
 * Raíz de todas las rutas: un único Suspense para las páginas cargadas con lazy, y el único
 * lugar donde se monta el modal de confirmación del uiStore.
 */
export function RootShell() {
  return (
    <>
      <Suspense fallback={<Spinner />}>
        <Outlet />
      </Suspense>
      <ConfirmHost />
    </>
  )
}

// Los layouts de shared/ no conocen las features: estos envoltorios les inyectan el cierre de sesión.
export function PublicShell() {
  const navigate = useNavigate()
  const logout = useLogout()
  return (
    <PublicLayout
      loggingOut={logout.isPending}
      onLogout={() => logout.mutate(undefined, { onSettled: () => navigate(RUTAS.inicio) })}
    />
  )
}

export function AdminShell() {
  const navigate = useNavigate()
  const logout = useLogout()
  return (
    <AdminLayout
      onLogout={() => logout.mutate(undefined, { onSettled: () => navigate(RUTAS.login) })}
    />
  )
}

export { Outlet }
