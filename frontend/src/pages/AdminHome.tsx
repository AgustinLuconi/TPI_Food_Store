import { Link } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import type { Rol } from '@/shared/types/auth'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'

interface Acceso {
  to: string
  titulo: string
  descripcion: string
  roles: Rol[]
}

const ACCESOS: Acceso[] = [
  {
    to: RUTAS.adminProductos,
    titulo: 'Productos',
    descripcion: 'Catálogo, precios, recetas e imágenes.',
    roles: ['ADMIN', 'STOCK'],
  },
  {
    to: RUTAS.adminIngredientes,
    titulo: 'Ingredientes',
    descripcion: 'Insumos, alérgenos y elaborados.',
    roles: ['ADMIN', 'STOCK'],
  },
  {
    to: RUTAS.adminInventario,
    titulo: 'Inventario',
    descripcion: 'Stock, movimientos, lotes y vencimientos.',
    roles: ['ADMIN', 'STOCK'],
  },
  {
    to: RUTAS.adminProduccion,
    titulo: 'Producción',
    descripcion: 'Órdenes de producción de productos y elaborados.',
    roles: ['ADMIN', 'STOCK'],
  },
  {
    to: RUTAS.adminCategorias,
    titulo: 'Categorías',
    descripcion: 'Administrá el árbol de categorías del catálogo.',
    roles: ['ADMIN'],
  },
  {
    to: RUTAS.adminUsuarios,
    titulo: 'Usuarios',
    descripcion: 'Altas, roles, bloqueos y bajas de usuarios.',
    roles: ['ADMIN'],
  },
  {
    to: RUTAS.adminConfiguracion,
    titulo: 'Configuración',
    descripcion: 'Local, horarios, días bloqueados y zonas de cobertura.',
    roles: ['ADMIN'],
  },
]

/** Inicio del panel: accesos según el rol. Las métricas con gráficos (recharts) llegan en la Fase 3. */
export default function AdminHome() {
  const usuario = useAuthStore((s) => s.usuario)

  return (
    <div className="flex flex-col gap-6 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Panel de administración</h1>
      <p className="text-navy-700">Bienvenido, {usuario?.nombre}.</p>
      <div className="grid gap-4 sm:grid-cols-2">
        {ACCESOS.filter((a) => a.roles.some((r) => usuario?.roles.includes(r))).map((a) => (
          <Link key={a.to} to={a.to}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <h2 className="font-bold text-navy-900">{a.titulo}</h2>
              <p className="mt-1 text-sm text-navy-500">{a.descripcion}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
