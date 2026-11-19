import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { getErrorMessage, toApiError } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Skeleton } from '@/shared/components/Skeleton'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { useUiStore } from '@/store/uiStore'
import { CancelarPedidoModal } from '../components/CancelarPedidoModal'
import { DetalleDelPedido } from '../components/DetalleDelPedido'
import { RegistrarPagoModal } from '../components/RegistrarPagoModal'
import { useCambiarEstado, usePedido } from '../hooks/usePedidos'
import { ETIQUETA_SIGUIENTE, NOMBRE_ESTADO, puedeCancelar, siguienteEstado } from '../lib/estados'

/** Un pedido desde el panel: registrar el pago, avanzar el estado y cancelar. La autorización real es la del backend. */
export default function GestionDePedidoPage() {
  const pedidoId = Number(useParams().id)
  const { data, isLoading, isError, error } = usePedido(pedidoId)
  const [modal, setModal] = useState<'pago' | 'cancelar' | null>(null)
  const avanzar = useCambiarEstado()
  const openConfirm = useUiStore((s) => s.openConfirm)
  const { exito, fallo } = useResultado()
  const volver = { volverA: RUTAS.adminPedido(pedidoId), volverLabel: 'Volver al pedido' }

  if (isLoading) return <Skeleton className="m-8 h-96 rounded-xl" />
  if (isError || !data) {
    return (
      <div className="m-8 rounded-xl border border-surface-border bg-white">
        <EstadoVacio
          titulo="No encontramos ese pedido"
          descripcion={toApiError(error).message}
          accion={
            <Link to={RUTAS.adminPedidos} className="font-semibold text-accent-700 underline">
              Volver a pedidos
            </Link>
          }
        />
      </div>
    )
  }

  const siguiente = siguienteEstado(data.estado_codigo)
  const pagoManual =
    data.forma_pago_codigo === 'EFECTIVO' || data.forma_pago_codigo === 'TRANSFERENCIA'

  function pedirAvance() {
    if (!siguiente) return
    openConfirm({
      titulo: ETIQUETA_SIGUIENTE[data!.estado_codigo] ?? 'Avanzar el pedido',
      mensaje:
        siguiente === 'EN_PREPARACION'
          ? `El pedido #${data!.id} pasa a «${NOMBRE_ESTADO[siguiente]}»: se consume el stock reservado.`
          : `El pedido #${data!.id} pasa a «${NOMBRE_ESTADO[siguiente]}».`,
      confirmLabel: 'Confirmar',
      onConfirm: async () => {
        try {
          await avanzar.mutateAsync({ id: data!.id, estado: siguiente })
          exito({
            titulo: 'Estado actualizado',
            mensaje: `El pedido #${data!.id} ahora está «${NOMBRE_ESTADO[siguiente]}».`,
            ...volver,
          })
        } catch (e) {
          fallo({ titulo: 'No se pudo cambiar el estado', mensaje: getErrorMessage(e), ...volver })
        }
      },
    })
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <nav aria-label="Ruta de navegación">
        <Link to={RUTAS.adminPedidos} className="text-sm font-semibold text-accent-700 underline">
          ← Pedidos
        </Link>
      </nav>
      <DetalleDelPedido
        pedido={data}
        mostrarCliente
        acciones={
          <>
            {data.estado_codigo === 'PENDIENTE' &&
              (pagoManual ? (
                <Button onClick={() => setModal('pago')}>Registrar pago</Button>
              ) : (
                <p className="rounded-lg bg-surface-border px-3 py-2 text-sm">
                  Este pedido se paga con MercadoPago y se confirma solo.
                </p>
              ))}
            {siguiente && (
              <Button onClick={pedirAvance}>{ETIQUETA_SIGUIENTE[data.estado_codigo]}</Button>
            )}
            {puedeCancelar(data.estado_codigo, true) && (
              <Button variant="danger" onClick={() => setModal('cancelar')}>
                Cancelar pedido
              </Button>
            )}
          </>
        }
      />
      {modal === 'pago' && (
        <RegistrarPagoModal
          pedido={data}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null)
            exito({
              titulo: 'Pago registrado',
              mensaje: `El pedido #${data.id} quedó confirmado.`,
              ...volver,
            })
          }}
        />
      )}
      {modal === 'cancelar' && (
        <CancelarPedidoModal
          pedidoId={data.id}
          onClose={() => setModal(null)}
          onDone={() => {
            setModal(null)
            exito({
              titulo: 'Pedido cancelado',
              mensaje: `El pedido #${data.id} se canceló.`,
              ...volver,
            })
          }}
        />
      )}
    </div>
  )
}
