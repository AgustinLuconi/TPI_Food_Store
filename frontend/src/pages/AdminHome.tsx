import { Link } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'

/** Inicio del panel. Las métricas con gráficos (recharts) llegan en la Fase 3. */
export default function AdminHome() {
  const usuario = useAuthStore((s) => s.usuario)
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN'))

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Panel de administración</h1>
      <p className="text-navy-700">Bienvenido, {usuario?.nombre}.</p>
      {esAdmin && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Link to={RUTAS.adminCategorias}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <h2 className="font-bold text-navy-900">Categorías</h2>
              <p className="mt-1 text-sm text-navy-500">
                Administrá el árbol de categorías del catálogo.
              </p>
            </Card>
          </Link>
          <Link to={RUTAS.adminUsuarios}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <h2 className="font-bold text-navy-900">Usuarios</h2>
              <p className="mt-1 text-sm text-navy-500">
                Altas, roles, bloqueos y bajas de usuarios.
              </p>
            </Card>
          </Link>
        </div>
      )}
    </div>
  )
}
