import { Link } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { ROLES_PERSONAL } from '@/shared/types/auth'
import { Button } from '@/shared/ui/Button'
import { useAuthStore } from '@/store/authStore'

interface HeaderProps {
  onLogout: () => void
  loggingOut?: boolean
}

export function Header({ onLogout, loggingOut = false }: HeaderProps) {
  // Suscripción por selector: el header no se re-renderiza por cambios ajenos del store.
  const usuario = useAuthStore((s) => s.usuario)
  const esPersonal = usuario?.roles.some((r) => ROLES_PERSONAL.includes(r)) ?? false

  return (
    <header className="border-b border-surface-border bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <Link to={RUTAS.inicio} className="text-xl font-extrabold text-navy-900">
          Food<span className="text-accent-700">Store</span>
        </Link>
        <nav aria-label="Principal" className="flex items-center gap-2">
          {usuario ? (
            <>
              {esPersonal && (
                <Link
                  to={RUTAS.admin}
                  className="rounded-lg px-3 py-2 text-sm font-semibold text-navy-700 hover:bg-surface-muted"
                >
                  Panel
                </Link>
              )}
              <Link
                to={RUTAS.perfil}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-navy-700 hover:bg-surface-muted"
              >
                {usuario.nombre}
              </Link>
              <Button variant="secondary" size="sm" onClick={onLogout} loading={loggingOut}>
                Salir
              </Button>
            </>
          ) : (
            <>
              <Link
                to={RUTAS.login}
                className="rounded-lg px-3 py-2 text-sm font-semibold text-navy-700 hover:bg-surface-muted"
              >
                Ingresar
              </Link>
              <Link
                to={RUTAS.registro}
                className="rounded-lg bg-accent-600 px-4 py-2 text-sm font-bold text-white hover:bg-accent-700"
              >
                Registrarme
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
