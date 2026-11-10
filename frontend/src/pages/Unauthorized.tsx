import { Link } from 'react-router'
import { homePorRoles, RUTAS } from '@/shared/lib/rutas'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'

export default function Unauthorized() {
  const usuario = useAuthStore((s) => s.usuario)
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Card className="flex w-full max-w-md flex-col items-center gap-4 p-8 text-center">
        <p className="text-5xl font-extrabold text-accent-700" aria-hidden="true">
          403
        </p>
        <h1 className="text-xl font-bold text-navy-900">No tenés acceso a esta sección</h1>
        <p className="text-sm text-navy-700">
          Tu cuenta no tiene el rol necesario para ver esta página.
        </p>
        <Link
          to={usuario ? homePorRoles(usuario.roles) : RUTAS.inicio}
          className="rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-accent-700"
        >
          Volver al inicio
        </Link>
      </Card>
    </div>
  )
}
