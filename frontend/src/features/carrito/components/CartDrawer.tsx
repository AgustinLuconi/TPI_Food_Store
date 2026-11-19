import { useNavigate } from 'react-router'
import { useEstadoLocal } from '@/shared/hooks/useEstadoLocal'
import { formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'
import { useCartStore, type CartLine } from '@/store/cartStore'
import { useUiStore } from '@/store/uiStore'
import { useValidacionDelCarrito } from '../hooks/useValidacionDelCarrito'
import type { ResultadoDeLinea } from '../lib/validacion'

/** El carrito: líneas con cantidad y exclusiones, avisos de la sección 11.2 y el paso al checkout. */
export function CartDrawer() {
  const abierto = useUiStore((s) => s.cartOpen)
  const cerrar = useUiStore((s) => s.setCartOpen)
  const lines = useCartStore((s) => s.lines)
  const setQuantity = useCartStore((s) => s.setQuantity)
  const removeItem = useCartStore((s) => s.removeItem)
  const updatePrices = useCartStore((s) => s.updatePrices)
  const navigate = useNavigate()

  const validacion = useValidacionDelCarrito(abierto && lines.length > 0)
  const { data: local } = useEstadoLocal()
  const cerrado = local !== undefined && !local.abierto

  const motivo =
    lines.length === 0
      ? null
      : validacion.bloqueado
        ? 'Quitá los productos que ya no están disponibles para continuar.'
        : cerrado
          ? 'El local está cerrado.'
          : null
  const puedeContinuar = lines.length > 0 && !validacion.bloqueado && !cerrado

  function finalizar() {
    cerrar(false)
    navigate(RUTAS.checkout)
  }

  return (
    <Modal
      open={abierto}
      onClose={() => cerrar(false)}
      title="Tu carrito"
      footer={
        lines.length > 0 ? (
          <>
            <Button variant="secondary" onClick={() => cerrar(false)}>
              Seguir comprando
            </Button>
            <Button onClick={finalizar} disabled={!puedeContinuar}>
              Finalizar compra
            </Button>
          </>
        ) : (
          <Button variant="secondary" onClick={() => cerrar(false)}>
            Cerrar
          </Button>
        )
      }
    >
      {lines.length === 0 ? (
        <p className="py-6 text-center text-navy-700">
          Tu carrito está vacío. Agregá algo de la carta.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {validacion.hayPreciosCambiados && (
            <div
              role="status"
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-accent-100 px-3 py-2 text-sm text-navy-900"
            >
              <span>Algunos precios cambiaron desde que los agregaste.</span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => updatePrices(validacion.preciosCambiados)}
              >
                Actualizar precios
              </Button>
            </div>
          )}
          <ul className="flex flex-col divide-y divide-surface-border">
            {lines.map((l) => (
              <Linea
                key={l.lineId}
                linea={l}
                resultado={validacion.resultados[l.lineId]}
                onCantidad={(n) => setQuantity(l.lineId, n)}
                onQuitar={() => removeItem(l.lineId)}
              />
            ))}
          </ul>
          <p className="flex items-center justify-between text-lg font-extrabold text-navy-900">
            <span>Subtotal</span>
            <span>{formatearDinero(validacion.subtotalActual)}</span>
          </p>
          <p className="text-xs text-navy-500">
            El envío se calcula en el siguiente paso. Los precios son referenciales hasta confirmar.
          </p>
          {cerrado && local && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
              El local está cerrado.{' '}
              {local.proxima_apertura
                ? `Vuelve a abrir el ${formatearFecha(local.proxima_apertura, true)}.`
                : 'Todavía no hay una próxima apertura.'}
            </p>
          )}
          {motivo && !cerrado && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
              {motivo}
            </p>
          )}
        </div>
      )}
    </Modal>
  )
}

function Linea({
  linea,
  resultado,
  onCantidad,
  onQuitar,
}: {
  linea: CartLine
  resultado?: ResultadoDeLinea
  onCantidad: (n: number) => void
  onQuitar: () => void
}) {
  const noDisponible = resultado?.estado === 'no_disponible'
  const precio = resultado?.precioActual ?? linea.precio
  return (
    <li className="flex flex-col gap-2 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-bold text-navy-900">{linea.nombre}</p>
          {linea.exclusionesNombres.length > 0 && (
            <p className="text-sm text-navy-500">Sin: {linea.exclusionesNombres.join(', ')}</p>
          )}
          {noDisponible && (
            <p className="mt-1">
              <Badge tone="danger">No disponible</Badge>
            </p>
          )}
          {resultado?.estado === 'precio_cambiado' && (
            <p className="mt-1 text-sm text-navy-700">
              Precio actual {formatearDinero(precio)}{' '}
              <span className="text-navy-500">(antes {formatearDinero(linea.precio)})</span>
            </p>
          )}
        </div>
        <p className="font-bold text-navy-900">{formatearDinero(precio * linea.cantidad)}</p>
      </div>
      <div className="flex items-center justify-between">
        <div
          role="group"
          aria-label={`Cantidad de ${linea.nombre}`}
          className="inline-flex items-center rounded-lg border border-surface-border"
        >
          <Button
            variant="ghost"
            size="sm"
            aria-label={`Quitar una unidad de ${linea.nombre}`}
            onClick={() => onCantidad(linea.cantidad - 1)}
          >
            −
          </Button>
          <span aria-live="polite" className="min-w-8 text-center font-bold">
            {linea.cantidad}
          </span>
          <Button
            variant="ghost"
            size="sm"
            aria-label={`Agregar una unidad de ${linea.nombre}`}
            disabled={linea.cantidad >= 99}
            onClick={() => onCantidad(linea.cantidad + 1)}
          >
            +
          </Button>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onQuitar}
          aria-label={`Quitar ${linea.nombre} del carrito`}
        >
          Quitar
        </Button>
      </div>
    </li>
  )
}
