import { DataTable, type Column } from '@/shared/components/DataTable'
import { formatearCantidad, formatearFecha } from '@/shared/lib/formato'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'
import { useLotes } from '../hooks/useInventario'
import type { ItemStock, Lote } from '../types'

const COLUMNAS: Column<Lote>[] = [
  {
    key: 'codigo',
    header: 'Lote',
    render: (l) => <span className="font-semibold">{l.codigo_lote}</span>,
  },
  {
    key: 'vence',
    header: 'Vence',
    render: (l) => (
      <span className="flex items-center gap-2">
        {formatearFecha(l.fecha_vencimiento)}
        {l.vencido && <Badge tone="danger">Vencido</Badge>}
      </span>
    ),
  },
  {
    key: 'inicial',
    header: 'Cantidad inicial',
    render: (l) => formatearCantidad(l.cantidad_inicial),
  },
  { key: 'real', header: 'Stock real', render: (l) => formatearCantidad(l.stock_real) },
  { key: 'disp', header: 'Disponible', render: (l) => formatearCantidad(l.stock_disponible) },
]

export function LotesModal({ producto, onClose }: { producto: ItemStock; onClose: () => void }) {
  const { data, isLoading } = useLotes(producto.id)
  return (
    <Modal
      open
      onClose={onClose}
      title={`Lotes de ${producto.nombre}`}
      wide
      footer={
        <Button variant="secondary" onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      <p className="mb-3 text-sm text-navy-500">
        Las ventas y reservas consumen primero el lote que vence antes (FEFO). Un lote vencido solo
        se da de baja con una merma por vencimiento.
      </p>
      <div className="overflow-hidden rounded-lg border border-surface-border">
        <DataTable
          columns={COLUMNAS}
          rows={data ?? []}
          rowKey={(l) => l.id}
          isLoading={isLoading}
          skeletonRows={3}
          emptyTitle="Sin lotes"
          emptyDescription="Las entradas sin código de lote no generan lotes."
        />
      </div>
    </Modal>
  )
}
