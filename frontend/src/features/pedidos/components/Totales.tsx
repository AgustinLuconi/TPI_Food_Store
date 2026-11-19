import { formatearDinero } from '@/shared/lib/formato'

interface Props {
  subtotal: string | number
  costoEnvio: string | number | null
  total: string | number
  /** Mientras el envío se está cotizando. */
  cotizando?: boolean
}

export function Totales({ subtotal, costoEnvio, total, cotizando = false }: Props) {
  return (
    <dl className="flex flex-col gap-1 text-sm">
      <div className="flex justify-between">
        <dt className="text-navy-700">Subtotal</dt>
        <dd className="font-semibold">{formatearDinero(subtotal)}</dd>
      </div>
      <div className="flex justify-between">
        <dt className="text-navy-700">Envío</dt>
        <dd className="font-semibold">
          {cotizando
            ? 'Calculando…'
            : costoEnvio === null
              ? 'A cotizar'
              : formatearDinero(costoEnvio)}
        </dd>
      </div>
      <div className="mt-1 flex justify-between border-t border-surface-border pt-2 text-base">
        <dt className="font-bold text-navy-900">Total</dt>
        <dd className="font-extrabold text-navy-900">{formatearDinero(total)}</dd>
      </div>
    </dl>
  )
}
