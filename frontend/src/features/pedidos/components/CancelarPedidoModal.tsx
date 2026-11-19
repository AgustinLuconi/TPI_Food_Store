import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { Modal } from '@/shared/ui/Modal'
import { useCancelarPedido } from '../hooks/usePedidos'
import type { Pedido } from '../types'

/** RN-05: cancelar un pedido exige un motivo, que queda en el historial. */
export function CancelarPedidoModal({
  pedidoId,
  onClose,
  onDone,
}: {
  pedidoId: number
  onClose: () => void
  onDone: (pedido: Pedido) => void
}) {
  const [motivo, setMotivo] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const cancelar = useCancelarPedido()

  function enviar() {
    if (!motivo.trim()) return setErrorLocal('Contanos el motivo de la cancelación.')
    setErrorLocal(null)
    cancelar.mutate({ id: pedidoId, motivo: motivo.trim() }, { onSuccess: onDone })
  }
  const errorServidor = cancelar.error ? toApiError(cancelar.error).message : null

  return (
    <Modal
      open
      onClose={onClose}
      title={`Cancelar el pedido #${pedidoId}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={cancelar.isPending}>
            Volver
          </Button>
          <Button
            type="submit"
            form="form-cancelar-pedido"
            variant="danger"
            loading={cancelar.isPending}
          >
            Cancelar pedido
          </Button>
        </>
      }
    >
      <form
        id="form-cancelar-pedido"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="flex flex-col gap-4"
      >
        <p className="text-sm text-navy-700">Al cancelar, el stock reservado se libera.</p>
        <Input
          label="Motivo"
          required
          maxLength={500}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        {(errorLocal ?? errorServidor) && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorLocal ?? errorServidor}
          </p>
        )}
      </form>
    </Modal>
  )
}
