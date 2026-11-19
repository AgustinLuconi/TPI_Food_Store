import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Skeleton } from '@/shared/components/Skeleton'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { CancelarPedidoModal } from '../components/CancelarPedidoModal'
import { DetalleDelPedido } from '../components/DetalleDelPedido'
import { usePedido } from '../hooks/usePedidos'
import { puedeCancelar } from '../lib/estados'

/** Seguimiento del pedido: se actualiza solo mientras no esté entregado ni cancelado. */
export default function PedidoDetallePage() {
  const { id } = useParams()
  const pedidoId = Number(id)
  const { data, isLoading, isError, error } = usePedido(pedidoId)
  const [cancelando, setCancelando] = useState(false)
  const { exito } = useResultado()

  if (isLoading) return <Skeleton className="h-96 w-full rounded-xl" />
  if (isError || !data) {
    return (
      <div className="rounded-xl border border-surface-border bg-white">
        <EstadoVacio
          titulo={
            toApiError(error).status === 404
              ? 'No encontramos ese pedido'
              : 'No pudimos cargar el pedido'
          }
          descripcion={toApiError(error).message}
          accion={
            <Link to={RUTAS.pedidos} className="font-semibold text-accent-700 underline">
              Ver mis pedidos
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <nav aria-label="Ruta de navegación">
        <Link to={RUTAS.pedidos} className="text-sm font-semibold text-accent-700 underline">
          ← Mis pedidos
        </Link>
      </nav>
      <DetalleDelPedido
        pedido={data}
        acciones={
          puedeCancelar(data.estado_codigo, false) && (
            <Button variant="danger" onClick={() => setCancelando(true)}>
              Cancelar pedido
            </Button>
          )
        }
      />
      {cancelando && (
        <CancelarPedidoModal
          pedidoId={data.id}
          onClose={() => setCancelando(false)}
          onDone={(p) => {
            setCancelando(false)
            exito({
              titulo: 'Pedido cancelado',
              mensaje: `El pedido #${p.id} se canceló y el stock reservado se liberó.`,
              volverA: RUTAS.pedido(p.id),
              volverLabel: 'Ver el pedido',
            })
          }}
        />
      )}
    </div>
  )
}
