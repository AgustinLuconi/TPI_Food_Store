import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { formatearDinero } from '@/shared/lib/formato'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Select } from '@/shared/ui/Select'
import { useUiStore } from '@/store/uiStore'
import { useAnularZona, useReactivarZona, useZonas } from '../hooks/useConfiguracion'
import type { Zona } from '../types'
import { ZonaFormModal } from './ZonaFormModal'

interface Props {
  onSaved: (titulo: string, mensaje: string) => void
  onFailed: (titulo: string, mensaje: string) => void
}

export function ZonasPanel({ onSaved, onFailed }: Props) {
  const [filtro, setFiltro] = useState<'activas' | 'inactivas' | 'todas'>('activas')
  const { data, isLoading, isError, error } = useZonas(
    filtro === 'todas' ? undefined : filtro === 'activas',
  )
  const [modal, setModal] = useState<{ zona: Zona | null; clave: number } | null>(null)
  const anular = useAnularZona()
  const reactivar = useReactivarZona()
  const openConfirm = useUiStore((s) => s.openConfirm)

  const columnas: Column<Zona>[] = [
    {
      key: 'nombre',
      header: 'Zona',
      render: (z) => <span className="font-semibold">{z.nombre}</span>,
    },
    { key: 'base', header: 'Tarifa base', render: (z) => formatearDinero(z.tarifa_base) },
    { key: 'km', header: 'Por km', render: (z) => formatearDinero(z.tarifa_por_km) },
    { key: 'min', header: 'Pedido mínimo', render: (z) => formatearDinero(z.pedido_minimo) },
    { key: 'vertices', header: 'Vértices', render: (z) => z.poligono.length },
  ]

  function pedirAnulacion(z: Zona) {
    openConfirm({
      titulo: 'Anular zona',
      mensaje: `¿Anular la zona "${z.nombre}"? Las direcciones dentro de ella dejarán de tener cobertura. Podés reactivarla después.`,
      confirmLabel: 'Anular',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await anular.mutateAsync(z.id)
          onSaved('Zona anulada', `"${z.nombre}" se anuló correctamente.`)
        } catch (e) {
          onFailed('No se pudo anular la zona', getErrorMessage(e))
        }
      },
    })
  }

  async function reactivarZona(z: Zona) {
    try {
      await reactivar.mutateAsync(z.id)
      onSaved('Zona reactivada', `"${z.nombre}" volvió a estar activa.`)
    } catch (e) {
      onFailed('No se pudo reactivar la zona', getErrorMessage(e))
    }
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-col gap-4 border-b border-surface-border p-4 sm:flex-row sm:items-end">
        <div className="sm:w-56">
          <Select
            label="Estado"
            value={filtro}
            options={[
              { value: 'activas', label: 'Activas' },
              { value: 'inactivas', label: 'Inactivas' },
              { value: 'todas', label: 'Todas' },
            ]}
            onChange={(e) => setFiltro(e.target.value as typeof filtro)}
          />
        </div>
        <div className="sm:ml-auto">
          <Button onClick={() => setModal({ zona: null, clave: Date.now() })}>+ Agregar</Button>
        </div>
      </div>
      {isError ? (
        <p role="alert" className="p-6 text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : (
        <DataTable
          columns={columnas}
          rows={data ?? []}
          rowKey={(z) => z.id}
          isLoading={isLoading}
          isInactive={(z) => !z.activo}
          emptyTitle="No hay zonas"
          emptyDescription="Sin zonas de cobertura no se pueden cotizar envíos a domicilio."
          actions={(z) =>
            z.activo ? (
              <>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setModal({ zona: z, clave: Date.now() })}
                >
                  Modificar
                </Button>
                <Button size="sm" variant="danger" onClick={() => pedirAnulacion(z)}>
                  Anular
                </Button>
              </>
            ) : (
              <Button size="sm" variant="secondary" onClick={() => reactivarZona(z)}>
                Reactivar
              </Button>
            )
          }
        />
      )}
      {modal && (
        <ZonaFormModal
          key={modal.clave}
          zona={modal.zona}
          onClose={() => setModal(null)}
          onSaved={(guardada, modo) => {
            setModal(null)
            onSaved(
              modo === 'create' ? 'Zona creada' : 'Zona actualizada',
              `"${guardada.nombre}" se guardó correctamente.`,
            )
          }}
        />
      )}
    </Card>
  )
}
