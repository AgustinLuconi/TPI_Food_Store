import { Link, useLocation } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { esResultadoState } from '@/shared/types/resultado'
import { Card } from '@/shared/ui/Card'

interface ResultadoPageProps {
  tipo: 'exito' | 'error'
}

/**
 * Página de resultado (/success y /error). El contexto llega en `location.state`; si el usuario
 * entra directo por la URL (sin contexto) se muestra un mensaje genérico.
 */
export function ResultadoPage({ tipo }: ResultadoPageProps) {
  const { state } = useLocation()
  const ok = tipo === 'exito'
  const resultado = esResultadoState(state) ? state : null

  const titulo = resultado?.titulo ?? (ok ? 'Operación exitosa' : 'Ocurrió un error')
  const mensaje =
    resultado?.mensaje ??
    (ok
      ? 'La acción se completó correctamente.'
      : 'No pudimos completar la acción. Intentá de nuevo.')

  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <Card className="flex w-full max-w-md flex-col items-center gap-4 p-8 text-center">
        <span
          aria-hidden="true"
          className={`flex size-14 items-center justify-center rounded-full text-3xl font-bold text-white ${
            ok ? 'bg-success-600' : 'bg-danger-600'
          }`}
        >
          {ok ? '✓' : '!'}
        </span>
        {/* role=alert para que los lectores de pantalla anuncien el resultado al llegar. */}
        <div role={ok ? 'status' : 'alert'}>
          <h1 className="text-xl font-bold text-navy-900">{titulo}</h1>
          <p className="mt-2 text-sm text-navy-700">{mensaje}</p>
        </div>
        <Link
          to={resultado?.volverA ?? RUTAS.inicio}
          className="rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-accent-700"
        >
          {resultado?.volverLabel ?? 'Volver al inicio'}
        </Link>
      </Card>
    </div>
  )
}

export function SuccessPage() {
  return <ResultadoPage tipo="exito" />
}

export function ErrorPage() {
  return <ResultadoPage tipo="error" />
}
