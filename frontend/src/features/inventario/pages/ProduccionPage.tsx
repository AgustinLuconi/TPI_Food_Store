import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { Paginacion } from '@/shared/components/Paginacion'
import { useResultado } from '@/shared/hooks/useResultado'
import { formatearCantidad, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Select } from '@/shared/ui/Select'
import {
  CancelarOrdenModal,
  CompletarModal,
  DetalleOrdenModal,
  OrdenFormModal,
  TONO_ESTADO,
} from '../components/OrdenModales'
import { useIniciarOrden, useOrdenes } from '../hooks/useInventario'
import { ESTADOS_ORDEN, type Orden } from '../types'

const VOLVER = { volverA: RUTAS.adminProduccion, volverLabel: 'Volver a producción' }

type Dialogo =
  | { tipo: 'nueva' }
  | { tipo: 'detalle'; orden: Orden }
  | { tipo: 'completar'; orden: Orden }
  | { tipo: 'cancelar'; orden: Orden }

export default function ProduccionPage() {
  const [estado, setEstado] = useState('')
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, error } = useOrdenes(estado, page)
  const [dialogo, setDialogo] = useState<Dialogo | null>(null)
  const iniciar = useIniciarOrden()
  const { exito, fallo } = useResultado()

  const columnas: Column<Orden>[] = [
    { key: 'id', header: 'Orden', render: (o) => `#${o.id}` },
    {
      key: 'nombre',
      header: 'Produce',
      render: (o) => <span className="font-semibold">{o.nombre}</span>,
    },
    { key: 'tipo', header: 'Tipo', render: (o) => (o.producto_id ? 'Producto' : 'Elaborado') },
    {
      key: 'cantidad',
      header: 'Cantidad',
      render: (o) => formatearCantidad(o.cantidad_a_producir),
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (o) => <Badge tone={TONO_ESTADO[o.estado]}>{o.estado}</Badge>,
    },
    { key: 'fecha', header: 'Creada', render: (o) => formatearFecha(o.created_at, true) },
  ]

  async function iniciarOrden(o: Orden) {
    try {
      await iniciar.mutateAsync(o.id)
      exito({
        titulo: 'Orden iniciada',
        mensaje: `La orden #${o.id} (${o.nombre}) está en proceso.`,
        ...VOLVER,
      })
    } catch (e) {
      fallo({ titulo: 'No se pudo iniciar la orden', mensaje: getErrorMessage(e), ...VOLVER })
    }
  }

  const cerrar = () => setDialogo(null)
  const terminar = (titulo: string, mensaje: (o: Orden) => string) => (o: Orden) => {
    cerrar()
    exito({ titulo, mensaje: mensaje(o), ...VOLVER })
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Producción</h1>
      <Card className="overflow-hidden p-0">
        <div className="flex flex-col gap-4 border-b border-surface-border p-4 sm:flex-row sm:items-end">
          <div className="sm:w-64">
            <Select
              label="Estado"
              value={estado}
              options={[
                { value: '', label: 'Todos' },
                ...ESTADOS_ORDEN.map((e) => ({ value: e, label: e })),
              ]}
              onChange={(e) => {
                setEstado(e.target.value)
                setPage(1)
              }}
            />
          </div>
          <div className="sm:ml-auto">
            <Button onClick={() => setDialogo({ tipo: 'nueva' })}>+ Planificar orden</Button>
          </div>
        </div>
        {isError ? (
          <p role="alert" className="p-6 text-sm text-danger-700">
            {getErrorMessage(error)}
          </p>
        ) : (
          <DataTable
            columns={columnas}
            rows={data?.items ?? []}
            rowKey={(o) => o.id}
            isLoading={isLoading}
            emptyTitle="No hay órdenes de producción"
            emptyDescription="Planificá una orden para producir un producto o un elaborado."
            actions={(o) => (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setDialogo({ tipo: 'detalle', orden: o })}
                >
                  Detalle
                </Button>
                {o.estado === 'PLANIFICADA' && (
                  <Button size="sm" variant="secondary" onClick={() => iniciarOrden(o)}>
                    Iniciar
                  </Button>
                )}
                {o.estado === 'EN_PROCESO' && (
                  <Button size="sm" onClick={() => setDialogo({ tipo: 'completar', orden: o })}>
                    Completar
                  </Button>
                )}
                {(o.estado === 'PLANIFICADA' || o.estado === 'EN_PROCESO') && (
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => setDialogo({ tipo: 'cancelar', orden: o })}
                  >
                    Cancelar
                  </Button>
                )}
              </>
            )}
          />
        )}
        {data && (
          <Paginacion
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={setPage}
          />
        )}
      </Card>

      {dialogo?.tipo === 'nueva' && (
        <OrdenFormModal
          onClose={cerrar}
          onDone={terminar(
            'Orden planificada',
            (o) => `La orden #${o.id} reservó los insumos de "${o.nombre}".`,
          )}
        />
      )}
      {dialogo?.tipo === 'detalle' && <DetalleOrdenModal id={dialogo.orden.id} onClose={cerrar} />}
      {dialogo?.tipo === 'completar' && (
        <CompletarModal
          orden={dialogo.orden}
          onClose={cerrar}
          onDone={terminar(
            'Orden completada',
            (o) => `La orden #${o.id} se completó: "${o.nombre}" ya está en el stock.`,
          )}
        />
      )}
      {dialogo?.tipo === 'cancelar' && (
        <CancelarOrdenModal
          orden={dialogo.orden}
          onClose={cerrar}
          onDone={terminar(
            'Orden cancelada',
            (o) => `La orden #${o.id} se canceló y liberó sus reservas.`,
          )}
        />
      )}
    </div>
  )
}
