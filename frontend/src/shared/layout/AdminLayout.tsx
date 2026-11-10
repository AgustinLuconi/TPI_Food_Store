import { Link, Outlet } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import { Sidebar } from './Sidebar'

export function AdminLayout({ onLogout }: { onLogout: () => void }) {
  const usuario = useAuthStore((s) => s.usuario)
  const toggleSidebar = useUiStore((s) => s.toggleSidebar)

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-surface-border bg-white px-4 py-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSidebar}
            className="lg:hidden"
            aria-label="Abrir menú"
          >
            ☰ Menú
          </Button>
          <div className="ml-auto flex items-center gap-3">
            <Link to={RUTAS.perfil} className="text-sm font-semibold text-navy-700 hover:underline">
              {usuario?.nombre} {usuario?.apellido}
            </Link>
            <Button variant="secondary" size="sm" onClick={onLogout}>
              Salir
            </Button>
          </div>
        </header>
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
