import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useValidacionDelCarrito } from '@/features/carrito/hooks/useValidacionDelCarrito'
import { SelectorDeDireccion } from '@/features/direcciones/components/SelectorDeDireccion'
import type { Direccion } from '@/features/direcciones/types'
import { Totales } from '@/features/pedidos/components/Totales'
import { useCotizacion, useCrearPedido, useFormasDePago } from '@/features/pedidos/hooks/usePedidos'
import { toApiError } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { useEstadoLocal } from '@/shared/hooks/useEstadoLocal'
import { useResultado } from '@/shared/hooks/useResultado'
import { formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { cn } from '@/shared/ui/cn'
import { Input } from '@/shared/ui/Input'
import { useCartStore } from '@/store/cartStore'
import { usePaymentStore, type PasoCheckout } from '@/store/paymentStore'
import { useUiStore } from '@/store/uiStore'

const PASOS: { id: PasoCheckout; titulo: string }[] = [
  { id: 'carrito', titulo: 'Tu pedido' },
  { id: 'entrega', titulo: 'Entrega' },
  { id: 'pago', titulo: 'Pago' },
  { id: 'confirmacion', titulo: 'Confirmar' },
]

type Entrega = 'retiro' | 'envio'

/**
 * Checkout en cuatro pasos. La Idempotency-Key se genera UNA vez al entrar a la confirmación (paymentStore): un doble
 * clic o un reintento reutilizan la misma clave y el backend devuelve el mismo pedido en lugar de crear otro.
 */
export default function CheckoutPage() {
  const lines = useCartStore((s) => s.lines)
  const clearCart = useCartStore((s) => s.clear)
  const updatePrices = useCartStore((s) => s.updatePrices)
  const paso = usePaymentStore((s) => s.paso)
  const setPaso = usePaymentStore((s) => s.setPaso)
  const formaPago = usePaymentStore((s) => s.formaPago)
  const setFormaPago = usePaymentStore((s) => s.setFormaPago)
  const ensureKey = usePaymentStore((s) => s.ensureIdempotencyKey)
  const resetCheckout = usePaymentStore((s) => s.reset)
  const abrirCarrito = useUiStore((s) => s.setCartOpen)
  const { exito, fallo } = useResultado()

  const [entrega, setEntrega] = useState<Entrega>('retiro')
  const [direccion, setDireccion] = useState<Direccion | null>(null)
  const [notas, setNotas] = useState('')

  const validacion = useValidacionDelCarrito()
  const { data: local } = useEstadoLocal()
  const cerrado = local !== undefined && !local.abierto
  const { data: formas = [] } = useFormasDePago()
  const crear = useCrearPedido()

  const subtotal = validacion.subtotalActual
  const punto =
    entrega === 'envio' && direccion?.lat != null && direccion?.lng != null
      ? { lat: direccion.lat, lng: direccion.lng }
      : null
  const cotizacion = useCotizacion(punto, subtotal)
  const errorCotizacion = cotizacion.error ? toApiError(cotizacion.error) : null
  const fueraDeZona = errorCotizacion?.code === 'OUTSIDE_COVERAGE'
  const costoEnvio =
    entrega === 'retiro' ? 0 : cotizacion.data ? Number(cotizacion.data.costo_envio) : null
  const bajoElMinimo =
    entrega === 'envio' && cotizacion.data !== undefined && !cotizacion.data.cumple_minimo

  // Al entrar al checkout se vuelve al primer paso si quedó uno a medias de otra visita.
  useEffect(() => {
    if (!PASOS.some((p) => p.id === paso)) setPaso('carrito')
  }, [paso, setPaso])

  const indice = Math.max(
    0,
    PASOS.findIndex((p) => p.id === paso),
  )

  // Qué impide avanzar desde cada paso, con el motivo a la vista (nunca un botón apagado sin explicación).
  const bloqueo: Record<PasoCheckout, string | null> = {
    carrito: validacion.bloqueado
      ? 'Quitá del carrito los productos que ya no están disponibles.'
      : null,
    entrega:
      entrega === 'envio'
        ? direccion === null
          ? 'Elegí una dirección o cambiá a retiro en el local.'
          : punto === null
            ? 'Esa dirección no tiene ubicación en el mapa. Editala desde «Mis direcciones» o elegí otra.'
            : fueraDeZona
              ? 'Esa dirección está fuera de nuestras zonas de reparto. Elegí otra o retirá en el local.'
              : bajoElMinimo
                ? `El pedido mínimo para esa zona es ${formatearDinero(cotizacion.data!.zona.pedido_minimo)}. Agregá algo más o retirá en el local.`
                : cotizacion.isError
                  ? 'No pudimos calcular el envío. Probá de nuevo en un momento.'
                  : cotizacion.isLoading
                    ? 'Calculando el envío…'
                    : null
        : null,
    pago: formaPago === null ? 'Elegí cómo vas a pagar.' : null,
    confirmacion: cerrado ? 'El local está cerrado.' : null,
  }

  if (lines.length === 0) {
    return (
      <div className="rounded-xl border border-surface-border bg-white">
        <EstadoVacio
          titulo="Tu carrito está vacío"
          descripcion="Agregá productos de la carta para armar tu pedido."
          accion={
            <Link to={RUTAS.inicio} className="font-semibold text-accent-700 underline">
              Ir a la carta
            </Link>
          }
        />
      </div>
    )
  }

  function confirmar() {
    const clave = ensureKey()
    crear.mutate(
      {
        clave,
        body: {
          items: lines.map((l) => ({
            producto_id: l.productoId,
            cantidad: l.cantidad,
            exclusiones: l.exclusiones,
          })),
          forma_pago_codigo: formaPago as string,
          direccion_id: entrega === 'envio' ? (direccion?.id ?? null) : null,
          notas: notas.trim() || null,
        },
      },
      {
        onSuccess: (pedido) => {
          clearCart()
          resetCheckout()
          exito({
            titulo: 'Pedido creado',
            mensaje: `Tu pedido #${pedido.id} quedó registrado. El local lo confirma cuando recibe el pago; podés seguirlo desde «Mis pedidos».`,
            volverA: RUTAS.pedido(pedido.id),
            volverLabel: 'Ver mi pedido',
          })
        },
        // El pedido NO se creó (stock, local cerrado, cobertura…): la clave se conserva para reintentar sin duplicar.
        onError: (e) =>
          fallo({
            titulo: 'No pudimos crear el pedido',
            mensaje: toApiError(e).message,
            volverA: RUTAS.checkout,
            volverLabel: 'Volver al checkout',
          }),
      },
    )
  }

  const total = subtotal + (costoEnvio ?? 0)
  const ultimo = indice === PASOS.length - 1

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-extrabold text-navy-900">Finalizar compra</h1>

      <ol
        aria-label="Pasos del checkout"
        className="grid grid-cols-4 gap-2 text-center text-xs sm:text-sm"
      >
        {PASOS.map((p, i) => (
          <li key={p.id} aria-current={i === indice ? 'step' : undefined}>
            <span
              className={cn(
                'block h-1.5 rounded-full',
                i <= indice ? 'bg-accent-600' : 'bg-surface-border',
              )}
            />
            <span
              className={cn(
                'mt-1 block font-semibold',
                i === indice ? 'text-navy-900' : 'text-navy-500',
              )}
            >
              {i + 1}. {p.titulo}
            </span>
          </li>
        ))}
      </ol>

      {cerrado && local && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-4 py-3 text-sm font-semibold text-danger-700"
        >
          El local está cerrado y no recibe pedidos.{' '}
          {local.proxima_apertura
            ? `Vuelve a abrir el ${formatearFecha(local.proxima_apertura, true)}.`
            : 'Todavía no hay una próxima apertura.'}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card className="flex flex-col gap-4">
          {paso === 'carrito' && (
            <section aria-label="Tu pedido" className="flex flex-col gap-3">
              <h2 className="font-bold text-navy-900">Revisá tu pedido</h2>
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
                {lines.map((l) => {
                  const r = validacion.resultados[l.lineId]
                  const precio = r?.precioActual ?? l.precio
                  return (
                    <li
                      key={l.lineId}
                      className="flex items-start justify-between gap-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-semibold text-navy-900">
                          {l.cantidad} × {l.nombre}
                        </p>
                        {l.exclusionesNombres.length > 0 && (
                          <p className="text-navy-500">Sin: {l.exclusionesNombres.join(', ')}</p>
                        )}
                        {r?.estado === 'no_disponible' && (
                          <p className="font-semibold text-danger-700">
                            Ya no está disponible: quitalo para continuar.
                          </p>
                        )}
                        {r?.estado === 'precio_cambiado' && (
                          <p className="text-navy-700">
                            Precio actual {formatearDinero(precio)} (antes{' '}
                            {formatearDinero(l.precio)})
                          </p>
                        )}
                      </div>
                      <p className="font-semibold">{formatearDinero(precio * l.cantidad)}</p>
                    </li>
                  )
                })}
              </ul>
              <p className="text-sm text-navy-500">
                ¿Querés cambiar algo?{' '}
                <button
                  type="button"
                  className="font-semibold text-accent-700 underline"
                  onClick={() => abrirCarrito(true)}
                >
                  Editar el carrito
                </button>
              </p>
            </section>
          )}

          {paso === 'entrega' && (
            <section aria-label="Entrega" className="flex flex-col gap-4">
              <h2 className="font-bold text-navy-900">¿Cómo lo querés recibir?</h2>
              <fieldset className="flex flex-col gap-2">
                <legend className="sr-only">Tipo de entrega</legend>
                {(
                  [
                    ['retiro', 'Retiro en el local', 'Sin costo de envío.'],
                    ['envio', 'Envío a domicilio', 'Se calcula según la distancia y tu zona.'],
                  ] as const
                ).map(([valor, titulo, ayuda]) => (
                  <label
                    key={valor}
                    className="flex cursor-pointer items-start gap-3 rounded-lg border border-surface-border p-3 has-[:checked]:border-accent-600"
                  >
                    <input
                      type="radio"
                      name="entrega"
                      className="mt-1 accent-accent-600"
                      checked={entrega === valor}
                      onChange={() => setEntrega(valor)}
                    />
                    <span className="text-sm">
                      <span className="font-bold text-navy-900">{titulo}</span>
                      <span className="block text-navy-500">{ayuda}</span>
                    </span>
                  </label>
                ))}
              </fieldset>
              {entrega === 'envio' && (
                <>
                  <SelectorDeDireccion value={direccion?.id ?? null} onChange={setDireccion} />
                  {cotizacion.data && cotizacion.data.cumple_minimo && (
                    <p
                      role="status"
                      className="rounded-lg bg-green-50 px-3 py-2 text-sm text-navy-900"
                    >
                      Zona {cotizacion.data.zona.nombre} · a {cotizacion.data.distancia_km} km ·
                      envío {formatearDinero(cotizacion.data.costo_envio)}
                    </p>
                  )}
                </>
              )}
              <Input
                label="Notas para el local (opcional)"
                maxLength={500}
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
              />
            </section>
          )}

          {paso === 'pago' && (
            <section aria-label="Pago" className="flex flex-col gap-3">
              <h2 className="font-bold text-navy-900">¿Cómo vas a pagar?</h2>
              <fieldset className="flex flex-col gap-2">
                <legend className="sr-only">Forma de pago</legend>
                {formas.map((f) => (
                  <label
                    key={f.codigo}
                    className="flex cursor-pointer items-center gap-3 rounded-lg border border-surface-border p-3 has-[:checked]:border-accent-600"
                  >
                    <input
                      type="radio"
                      name="pago"
                      className="accent-accent-600"
                      checked={formaPago === f.codigo}
                      onChange={() => setFormaPago(f.codigo)}
                    />
                    <span className="font-bold text-navy-900">{f.nombre}</span>
                  </label>
                ))}
              </fieldset>
              <p className="text-sm text-navy-500">
                Efectivo y transferencia los confirma el local cuando recibe el pago; recién ahí tu
                pedido pasa a «Confirmado».
              </p>
            </section>
          )}

          {paso === 'confirmacion' && (
            <section aria-label="Confirmación" className="flex flex-col gap-3 text-sm">
              <h2 className="font-bold text-navy-900">Revisá y confirmá</h2>
              <p>
                <span className="font-semibold">Entrega:</span>{' '}
                {entrega === 'retiro'
                  ? 'Retiro en el local'
                  : direccion
                    ? `${direccion.linea1}${direccion.ciudad ? `, ${direccion.ciudad}` : ''}`
                    : '—'}
              </p>
              <p>
                <span className="font-semibold">Pago:</span>{' '}
                {formas.find((f) => f.codigo === formaPago)?.nombre ?? formaPago}
              </p>
              {notas.trim() && (
                <p>
                  <span className="font-semibold">Notas:</span> {notas.trim()}
                </p>
              )}
              <p className="text-navy-500">
                Al confirmar se reserva el stock. Si algo falta o el local cerró, te avisamos y no
                se crea el pedido.
              </p>
            </section>
          )}

          {bloqueo[paso] && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
              {bloqueo[paso]}
            </p>
          )}

          <div className="flex justify-between gap-3 border-t border-surface-border pt-4">
            <Button
              variant="secondary"
              disabled={indice === 0 || crear.isPending}
              onClick={() => setPaso(PASOS[indice - 1].id)}
            >
              Atrás
            </Button>
            {ultimo ? (
              <Button
                onClick={confirmar}
                loading={crear.isPending}
                disabled={bloqueo.confirmacion !== null || formaPago === null}
              >
                Confirmar pedido
              </Button>
            ) : (
              <Button
                disabled={bloqueo[paso] !== null}
                onClick={() => setPaso(PASOS[indice + 1].id)}
              >
                Continuar
              </Button>
            )}
          </div>
        </Card>

        <aside aria-label="Resumen" className="h-fit">
          <Card className="flex flex-col gap-3">
            <h2 className="font-bold text-navy-900">Resumen</h2>
            <Totales
              subtotal={subtotal}
              costoEnvio={entrega === 'retiro' ? 0 : costoEnvio}
              total={total}
              cotizando={entrega === 'envio' && punto !== null && cotizacion.isLoading}
            />
          </Card>
        </aside>
      </div>
    </div>
  )
}
