import { Link } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { Card } from '@/shared/ui/Card'

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Card className="flex w-full max-w-md flex-col items-center gap-4 p-8 text-center">
        <p className="text-5xl font-extrabold text-accent-700" aria-hidden="true">
          404
        </p>
        <h1 className="text-xl font-bold text-navy-900">Página no encontrada</h1>
        <p className="text-sm text-navy-700">La dirección que buscás no existe o fue movida.</p>
        <Link
          to={RUTAS.inicio}
          className="rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-accent-700"
        >
          Ir al inicio
        </Link>
      </Card>
    </div>
  )
}
