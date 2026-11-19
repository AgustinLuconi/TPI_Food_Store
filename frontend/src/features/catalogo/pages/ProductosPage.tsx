import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { FilterBar } from '@/shared/components/FilterBar'
import { Paginacion } from '@/shared/components/Paginacion'
import { useMaestroFilters } from '@/shared/hooks/useMaestroFilters'
import { useResultado } from '@/shared/hooks/useResultado'
import { formatearCantidad, formatearDinero, urlDeMedia } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import { ProductoFormModal } from '../components/ProductoFormModal'
import { RecetaModal } from '../components/RecetaModal'
import {
  useAnularProducto,
  useCambiarDisponibilidad,
  useOpcionesDeCategoria,
  useProductos,
  useReactivarProducto,
} from '../hooks/useCatalogo'
import type { ProductoItem } from '../types'

const VOLVER = { volverA: RUTAS.adminProductos, volverLabel: 'Volver a productos' }

export default function ProductosPage() {
  const filtros = useMaestroFilters()
  const { data, isLoading, isError, error } = useProductos(filtros.params)
  const { data: categorias = [] } = useOpcionesDeCategoria()
  const [modal, setModal] = useState<{ producto: ProductoItem | null; clave: number } | null>(null)
  const [receta, setReceta] = useState<ProductoItem | null>(null)

  const anular = useAnularProducto()
  const reactivar = useReactivarProducto()
  const disponibilidad = useCambiarDisponibilidad()
  const openConfirm = useUiStore((s) => s.openConfirm)
  // Ocultan acciones; la autorización real es la del backend.
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN'))
  const { exito, fallo } = useResultado()

  const opcionesGrupo = [
    { value: '', label: 'Todas las categorías' },
    ...categorias.map((c) => ({ value: String(c.id), label: c.ruta })),
  ]

  const columnas: Column<ProductoItem>[] = [
    {
      key: 'imagen',
      header: 'Imagen',
      render: (p) => {
        const src = urlDeMedia(p.imagen_url)
        return src ? (
          <img src={src} alt="" className="size-12 rounded-lg object-cover" />
        ) : (
          <span className="flex size-12 items-center justify-center rounded-lg bg-surface-border text-xs text-navy-700">
            Sin foto
          </span>
        )
      },
    },
    {
      key: 'nombre',
      header: 'Nombre',
      sortKey: 'nombre',
      render: (p) => <span className="font-semibold">{p.nombre}</span>,
    },
    {
      key: 'categorias',
      header: 'Categorías',
      render: (p) => (p.categorias.length ? p.categorias.map((c) => c.nombre).join(', ') : '—'),
    },
    {
      key: 'precio',
      header: 'Precio',
      sortKey: 'precio',
      render: (p) => formatearDinero(p.precio_base),
    },
    {
      key: 'stock',
      header: 'Stock real / disp.',
      render: (p) =>
        p.stock_real === null ? (
          '—'
        ) : (
          <span
            className={
              Number(p.stock_disponible) <= p.stock_minimo
                ? 'font-semibold text-danger-700'
                : undefined
            }
          >
            {formatearCantidad(p.stock_real)} / {formatearCantidad(p.stock_disponible ?? 0)}
          </span>
        ),
    },
    {
      key: 'disponible',
      header: 'Venta',
      render: (p) => (
        <Badge tone={p.disponible ? 'success' : 'neutral'}>
          {p.disponible ? 'Disponible' : 'No disponible'}
        </Badge>
      ),
    },
  ]

  async function alternarDisponibilidad(p: ProductoItem) {
    try {
      await disponibilidad.mutateAsync({ id: p.id, disponible: !p.disponible })
    } catch (e) {
      fallo({
        titulo: 'No se pudo cambiar la disponibilidad',
        mensaje: getErrorMessage(e),
        ...VOLVER,
      })
    }
  }

  function pedirAnulacion(p: ProductoItem) {
    openConfirm({
      titulo: 'Anular producto',
      mensaje: `¿Anular "${p.nombre}"? Dejará de mostrarse y de poder pedirse. Podés reactivarlo después.`,
      confirmLabel: 'Anular',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await anular.mutateAsync(p.id)
          exito({
            titulo: 'Producto anulado',
            mensaje: `"${p.nombre}" se anuló correctamente.`,
            ...VOLVER,
          })
        } catch (e) {
          fallo({ titulo: 'No se pudo anular el producto', mensaje: getErrorMessage(e), ...VOLVER })
        }
      },
    })
  }

  async function reactivarProducto(p: ProductoItem) {
    try {
      await reactivar.mutateAsync(p.id)
      exito({
        titulo: 'Producto reactivado',
        mensaje: `"${p.nombre}" volvió a estar activo. Queda como no disponible hasta que lo habilites.`,
        ...VOLVER,
      })
    } catch (e) {
      fallo({ titulo: 'No se pudo reactivar el producto', mensaje: getErrorMessage(e), ...VOLVER })
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Productos</h1>
      <Card className="overflow-hidden p-0">
        <FilterBar
          search={filtros.search}
          onSearchChange={filtros.setSearch}
          group={{
            label: 'Agrupar por categoría',
            value: filtros.grupo,
            options: opcionesGrupo,
            onChange: filtros.setGrupo,
          }}
          estado={filtros.estado}
          onEstadoChange={filtros.setEstado}
          action={
            esAdmin && (
              <Button onClick={() => setModal({ producto: null, clave: Date.now() })}>
                + Agregar
              </Button>
            )
          }
        />
        {isError ? (
          <p role="alert" className="p-6 text-sm text-danger-700">
            {getErrorMessage(error)}
          </p>
        ) : (
          <DataTable
            columns={columnas}
            rows={data?.items ?? []}
            rowKey={(p) => p.id}
            isLoading={isLoading}
            isInactive={(p) => p.deleted_at !== null}
            orden={filtros.orden}
            onOrdenChange={filtros.ordenarPor}
            emptyTitle="No hay productos"
            emptyDescription="Probá con otros filtros o agregá un producto nuevo."
            actions={(p) =>
              p.deleted_at ? (
                esAdmin && (
                  <Button size="sm" variant="secondary" onClick={() => reactivarProducto(p)}>
                    Reactivar
                  </Button>
                )
              ) : (
                <>
                  <Button size="sm" variant="secondary" onClick={() => alternarDisponibilidad(p)}>
                    {p.disponible ? 'Pausar venta' : 'Habilitar venta'}
                  </Button>
                  {esAdmin && (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => setReceta(p)}>
                        Receta
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setModal({ producto: p, clave: Date.now() })}
                      >
                        Modificar
                      </Button>
                      <Button size="sm" variant="danger" onClick={() => pedirAnulacion(p)}>
                        Anular
                      </Button>
                    </>
                  )}
                </>
              )
            }
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
      </Card>

      {modal && (
        <ProductoFormModal
          key={modal.clave}
          producto={modal.producto}
          onClose={() => setModal(null)}
          onSaved={(guardado, modo) => {
            setModal(null)
            exito({
              titulo: modo === 'create' ? 'Producto creado' : 'Producto actualizado',
              mensaje: `"${guardado.nombre}" se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
      {receta && (
        <RecetaModal
          tipo="producto"
          id={receta.id}
          nombre={receta.nombre}
          onClose={() => setReceta(null)}
          onSaved={() => {
            setReceta(null)
            exito({
              titulo: 'Receta guardada',
              mensaje: `La receta de "${receta.nombre}" se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
    </div>
  )
}
