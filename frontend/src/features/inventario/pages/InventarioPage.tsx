import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { FilterBar } from '@/shared/components/FilterBar'
import { Paginacion } from '@/shared/components/Paginacion'
import { useMaestroFilters } from '@/shared/hooks/useMaestroFilters'
import { formatearCantidad, formatearFecha } from '@/shared/lib/formato'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Input } from '@/shared/ui/Input'
import { Tabs } from '@/shared/ui/Tabs'
import { LotesModal } from '../components/LotesModal'
import { MovimientosModal } from '../components/MovimientosModal'
import { useItemsStock, usePorVencer } from '../hooks/useInventario'
import type { ItemStock, LotePorVencer, TipoItem } from '../types'

export default function InventarioPage() {
  const [pestana, setPestana] = useState('productos')
  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Inventario</h1>
      <Tabs
        etiqueta="Secciones del inventario"
        activa={pestana}
        onChange={setPestana}
        pestanas={[
          { id: 'productos', label: 'Productos', contenido: <TablaStock tipo="producto" /> },
          { id: 'insumos', label: 'Insumos', contenido: <TablaStock tipo="ingrediente" /> },
          { id: 'por-vencer', label: 'Por vencer', contenido: <PorVencer /> },
        ]}
      />
    </div>
  )
}

function TablaStock({ tipo }: { tipo: TipoItem }) {
  const filtros = useMaestroFilters()
  const { data, isLoading, isError, error } = useItemsStock(tipo, filtros.params)
  const [movimientos, setMovimientos] = useState<ItemStock | null>(null)
  const [lotes, setLotes] = useState<ItemStock | null>(null)
  const nombre = tipo === 'producto' ? 'producto' : 'insumo'

  const columnas: Column<ItemStock>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      sortKey: 'nombre',
      render: (i) => <span className="font-semibold">{i.nombre}</span>,
    },
    { key: 'real', header: 'Stock real', render: (i) => formatearCantidad(i.stock_real ?? 0) },
    {
      key: 'disp',
      header: 'Disponible',
      render: (i) => formatearCantidad(i.stock_disponible ?? 0),
    },
    { key: 'min', header: 'Mínimo', render: (i) => i.stock_minimo },
    {
      key: 'alerta',
      header: 'Estado',
      render: (i) =>
        Number(i.stock_disponible ?? 0) <= i.stock_minimo ? (
          <Badge tone="danger">Bajo mínimo</Badge>
        ) : (
          <Badge tone="success">Normal</Badge>
        ),
    },
  ]

  return (
    <Card className="overflow-hidden p-0">
      <FilterBar
        search={filtros.search}
        onSearchChange={filtros.setSearch}
        searchLabel={`Buscar ${nombre}`}
        estado={filtros.estado}
        onEstadoChange={filtros.setEstado}
      />
      {isError ? (
        <p role="alert" className="p-6 text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : (
        <DataTable
          columns={columnas}
          rows={data?.items ?? []}
          rowKey={(i) => i.id}
          isLoading={isLoading}
          isInactive={(i) => i.deleted_at !== null}
          orden={filtros.orden}
          onOrdenChange={filtros.ordenarPor}
          emptyTitle={`No hay ${tipo === 'producto' ? 'productos' : 'insumos'}`}
          actions={(i) => (
            <>
              <Button size="sm" variant="secondary" onClick={() => setMovimientos(i)}>
                Movimientos
              </Button>
              {tipo === 'producto' && (
                <Button size="sm" variant="secondary" onClick={() => setLotes(i)}>
                  Lotes
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
          onPageChange={filtros.setPage}
        />
      )}
      {movimientos && (
        <MovimientosModal tipo={tipo} item={movimientos} onClose={() => setMovimientos(null)} />
      )}
      {lotes && <LotesModal producto={lotes} onClose={() => setLotes(null)} />}
    </Card>
  )
}

function PorVencer() {
  const [dias, setDias] = useState('7')
  const diasValidos = /^\d+$/.test(dias) && Number(dias) <= 365 ? Number(dias) : 7
  const { data, isLoading, isError, error } = usePorVencer(diasValidos)
  const [movimientos, setMovimientos] = useState<ItemStock | null>(null)

  const columnas: Column<LotePorVencer>[] = [
    {
      key: 'producto',
      header: 'Producto',
      render: (l) => <span className="font-semibold">{l.producto_nombre}</span>,
    },
    { key: 'lote', header: 'Lote', render: (l) => l.codigo_lote },
    { key: 'vence', header: 'Vence', render: (l) => formatearFecha(l.fecha_vencimiento) },
    {
      key: 'dias',
      header: 'Días',
      render: (l) =>
        l.vencido ? (
          <Badge tone="danger">Vencido</Badge>
        ) : (
          <Badge tone={l.dias_restantes <= 2 ? 'accent' : 'neutral'}>{l.dias_restantes}</Badge>
        ),
    },
    { key: 'stock', header: 'Stock del lote', render: (l) => formatearCantidad(l.stock_real) },
  ]

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-col gap-2 border-b border-surface-border p-4 sm:max-w-xs">
        <Input
          label="Vencen en los próximos (días)"
          inputMode="numeric"
          value={dias}
          onChange={(e) => setDias(e.target.value)}
          hint="Incluye los lotes ya vencidos con stock: se dan de baja con una merma por vencimiento."
        />
      </div>
      {isError ? (
        <p role="alert" className="p-6 text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : (
        <DataTable
          columns={columnas}
          rows={data ?? []}
          rowKey={(l) => l.id}
          isLoading={isLoading}
          emptyTitle="Nada por vencer"
          emptyDescription="No hay lotes con stock que venzan en ese plazo."
          actions={(l) => (
            <Button
              size="sm"
              variant="secondary"
              onClick={() =>
                setMovimientos({
                  id: l.producto_id,
                  nombre: l.producto_nombre,
                  stock_minimo: 0,
                  stock_real: l.stock_real,
                  stock_disponible: l.stock_disponible,
                  deleted_at: null,
                })
              }
            >
              Dar de baja
            </Button>
          )}
        />
      )}
      {movimientos && (
        <MovimientosModal tipo="producto" item={movimientos} onClose={() => setMovimientos(null)} />
      )}
    </Card>
  )
}
