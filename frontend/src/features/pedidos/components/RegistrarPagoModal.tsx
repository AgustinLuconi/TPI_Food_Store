import { useRef } from 'react'
import { toApiError } from '@/shared/api/errors'
import { formatearDinero } from '@/shared/lib/formato'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'
import { useRegistrarPago } from '../hooks/usePedidos'
import type { Pedido } from '../types'

/**
 * Registra el cobro en efectivo o por transferencia una vez verificado. El monto tiene que coincidir con el total.
 * La Idempotency-Key se genera UNA vez al abrir el modal: un doble clic o un reintento devuelven el mismo pago.
 */
export function RegistrarPagoModal({
  pedido,
  onClose,
  onDone,
}: {
  pedido: Pedido
  onClose: () => void
  onDone: () => void
}) {
  const clave = useRef(crypto.randomUUID())
  const registrar = useRegistrarPago()
  const error = registrar.error ? toApiError(registrar.error).message : null

  return (
    <Modal
      open
      onClose={onClose}
      title={`Registrar el pago del pedido #${pedido.id}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={registrar.isPending}>
            Cancelar
          </Button>
          <Button
            loading={registrar.isPending}
            onClick={() =>
              registrar.mutate(
                { pedidoId: pedido.id, monto: pedido.total, clave: clave.current },
                { onSuccess: onDone },
              )
            }
          >
            Registrar pago
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3 text-sm">
        <p>
          Cliente: <strong>{pedido.cliente_nombre}</strong>
        </p>
        <p>
          Forma de pago:{' '}
          <strong>{pedido.forma_pago_codigo === 'EFECTIVO' ? 'Efectivo' : 'Transferencia'}</strong>
        </p>
        <p className="text-lg">
          Monto a cobrar: <strong>{formatearDinero(pedido.total)}</strong>
        </p>
        <p className="text-navy-500">
          Verificá el cobro o el comprobante antes de registrarlo. Al registrarlo, el pedido pasa a
          «Confirmado».
        </p>
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-danger-700">
            {error}
          </p>
        )}
      </div>
    </Modal>
  )
}
