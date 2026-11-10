import { NavLink } from 'react-router'
import { cn } from '@/shared/ui/cn'
import { RUTAS } from '@/shared/lib/rutas'
import type { Rol } from '@/shared/types/auth'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'

interface Item {
  to: string
  label: string
  roles: Rol[]
  end?: boolean
}

// Cada ítem se muestra solo a los roles con acceso. Es una ayuda visual: el backend autoriza igual.
const ITEMS: Item[] = [
  { to: RUTAS.admin, label: 'Inicio', roles: ['ADMIN', 'STOCK', 'PEDIDOS'], end: true },
  { to: RUTAS.adminCategorias, label: 'Categorías', roles: ['ADMIN'] },
  { to: RUTAS.adminUsuarios, label: 'Usuarios', roles: ['ADMIN'] },
]

export function Sidebar() {
  const hasRole = useAuthStore((s) => s.hasRole)
  const abierto = useUiStore((s) => s.sidebarOpen)
  const cerrar = useUiStore((s) => s.setSidebarOpen)

  return (
    <>
      {/* Fondo para cerrar el menú en pantallas chicas. */}
      {abierto && (
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={() => cerrar(false)}
          className="fixed inset-0 z-30 bg-navy-900/50 lg:hidden"
        />
      )}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 bg-navy-900 text-white transition-transform lg:static lg:translate-x-0',
          abierto ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="px-6 py-5 text-xl font-extrabold">
          Food<span className="text-accent-100">Store</span>
        </div>
        <nav aria-label="Panel de administración" className="flex flex-col gap-1 px-3">
          {ITEMS.filter((i) => hasRole(...i.roles)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => cerrar(false)}
              className={({ isActive }) =>
                cn(
                  'rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors',
                  isActive ? 'bg-accent-600 text-white' : 'text-slate-200 hover:bg-navy-800',
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  )
}
