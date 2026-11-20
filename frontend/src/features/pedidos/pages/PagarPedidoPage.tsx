import { CardPayment, initMercadoPago } from '@mercadopago/sdk-react'
import { type ComponentProps, useEffect } from 'react'
import { Link, Navigate, useParams } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Skeleton } from '@/shared/components/Skeleton'
import { useResultado } from '@/shared/hooks/useResultado'
import { formatearDinero } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Card } from '@/shared/ui/Card'
import { type IntentoMercadoPago, usePaymentStore } from '@/store/paymentStore'
import { useConfigMercadoPago, usePagarConTarjeta, usePedido } from '../hooks/usePedidos'
import { describirDetalle, situacionDelPago } from '../lib/mercadopago'

/** Lo que CardPayment entrega al confirmar: la tarjeta ya viene tokenizada por MercadoPago. */
type AlConfirmar = ComponentProps<typeof CardPayment>['onSubmit']

const ESTADOS_DE_INTENTO = new Set<IntentoMercadoPago['estado']>([
  'approved',
  'pending',
  'in_process',
  'rejected',
  'cancelled',
])

/**
 * Cobro con tarjeta de un pedido MERCADOPAGO PENDIENTE (Anexo B.3). El formulario es del SDK de MercadoPago:
 * el número, el vencimiento y el CVV los tokeniza el navegador y nunca llegan a nuestro servidor.
 */
export default function PagarPedidoPage() {
  const { id } = useParams()
  const pedidoId = Number(id)
  const { data: pedido, isLoading, isError, error } = usePedido(pedidoId)
  const config = useConfigMercadoPago()
  const pagar = usePagarConTarjeta()
  const intento = usePaymentStore((s) => s.intentoMp)
  const setIntento = usePaymentStore((s) => s.setIntentoMp)
  const { exito } = useResultado()
  const publicKey = config.data?.public_key

  useEffect(() => {
    if (publicKey) initMercadoPago(publicKey, { locale: 'es-AR' })
  }, [publicKey])
  // Un intento de otro pedido no debe verse en este.
  useEffect(() => () => setIntento(null), [pedidoId, setIntento])

  if (isLoading || config.isLoading) return <Skeleton className="h-96 w-full rounded-xl" />
  if (isError || !pedido) {
    return <Vacio titulo="No pudimos cargar el pedido" descripcion={toApiError(error).message} />
  }
  if (pedido.forma_pago_codigo !== 'MERCADOPAGO' || pedido.estado_codigo !== 'PENDIENTE') {
    return <Navigate to={RUTAS.pedido(pedido.id)} replace />
  }
  if (config.isError || !publicKey) {
    return (
      <Vacio
        titulo="El pago con tarjeta no está disponible"
        descripcion="El local todavía no habilitó MercadoPago. Escribinos para coordinar otra forma de pago."
      />
    )
  }

  const situacion = situacionDelPago(pedido.pago?.mp_status)
  if (situacion === 'en_proceso') {
    return (
      <div className="flex flex-col gap-4">
        <Card role="status" className="flex flex-col gap-2">
          <h1 className="text-xl font-extrabold text-navy-900">Estamos procesando tu pago</h1>
          <p className="text-navy-700">
            MercadoPago todavía no confirmó el cobro del pedido #{pedido.id}. Apenas lo haga, el
            pedido pasa a «Confirmado» y no tenés que hacer nada más.
          </p>
          <Link to={RUTAS.pedido(pedido.id)} className="font-semibold text-accent-700 underline">
            Seguir mi pedido
          </Link>
        </Card>
      </div>
    )
  }

  // El último rechazo (de la base o del intento en pantalla) para explicar qué pasó.
  const rechazo =
    intento?.estado === 'rejected'
      ? intento.detalle
      : situacion === 'reintentable'
        ? pedido.pago?.mp_status_detail
        : undefined

  const onSubmit: AlConfirmar = async (datos) => {
    setIntento({ estado: 'procesando', detalle: null })
    try {
      const pago = await pagar.mutateAsync({
        pedido_id: pedidoId,
        token: datos.token,
        payment_method_id: datos.payment_method_id,
        installments: datos.installments,
        issuer_id: datos.issuer_id || undefined,
        email: datos.payer.email ?? '',
        identification_type: datos.payer.identification?.type,
        identification_number: datos.payer.identification?.number,
      })
      const estadoDelPago = pago.mp_status as IntentoMercadoPago['estado']
      setIntento({
        estado: ESTADOS_DE_INTENTO.has(estadoDelPago) ? estadoDelPago : 'pending',
        detalle: pago.mp_status_detail ?? null,
      })
      if (pago.mp_status === 'approved') {
        exito({
          titulo: '¡Pago aprobado!',
          mensaje: `Recibimos el pago del pedido #${pedidoId}. Ya lo estamos preparando.`,
          volverA: RUTAS.pedido(pedidoId),
          volverLabel: 'Ver mi pedido',
        })
      }
    } catch (e) {
      setIntento({ estado: 'error', detalle: toApiError(e).message })
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
      <nav aria-label="Ruta de navegación">
        <Link
          to={RUTAS.pedido(pedido.id)}
          className="text-sm font-semibold text-accent-700 underline"
        >
          ← Pedido #{pedido.id}
        </Link>
      </nav>
      <h1 className="text-2xl font-extrabold text-navy-900">Pagar con tarjeta</h1>
      <p className="text-navy-700">
        Total a pagar: <strong>{formatearDinero(pedido.total)}</strong>. Tus datos de tarjeta los
        procesa MercadoPago; nosotros nunca los vemos.
      </p>

      {rechazo !== undefined && intento?.estado !== 'error' && (
        <p
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800"
        >
          <strong>El pago fue rechazado.</strong> {describirDetalle(rechazo)} Podés intentar con
          otra tarjeta.
        </p>
      )}
      {intento?.estado === 'error' && (
        <p
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800"
        >
          {intento.detalle ?? 'No pudimos procesar el pago.'}
        </p>
      )}
      {intento?.estado === 'pending' || intento?.estado === 'in_process' ? (
        <p
          role="status"
          className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
        >
          Tu pago quedó en proceso. Cuando MercadoPago lo confirme, el pedido se confirma solo.
        </p>
      ) : null}

      <Card>
        <CardPayment
          initialization={{ amount: Number(pedido.total) }}
          onSubmit={onSubmit}
          onError={() =>
            setIntento({ estado: 'error', detalle: 'No se pudo cargar el formulario de pago.' })
          }
        />
      </Card>
    </div>
  )
}

function Vacio({ titulo, descripcion }: { titulo: string; descripcion: string }) {
  return (
    <div className="rounded-xl border border-surface-border bg-white">
      <EstadoVacio
        titulo={titulo}
        descripcion={descripcion}
        accion={
          <Link to={RUTAS.pedidos} className="font-semibold text-accent-700 underline">
            Ver mis pedidos
          </Link>
        }
      />
    </div>
  )
}
