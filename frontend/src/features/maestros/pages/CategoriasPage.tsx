import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { FilterBar } from '@/shared/components/FilterBar'
import { Paginacion } from '@/shared/components/Paginacion'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import { CategoriaFormModal } from '../components/CategoriaFormModal'
import { useAnularCategoria, useCategorias, useReactivarCategoria } from '../hooks/useCategorias'
import { useMaestroFilters } from '../hooks/useMaestroFilters'
import type { Categoria } from '../types'

const VOLVER = { volverA: RUTAS.adminCategorias, volverLabel: 'Volver a categorías' }

export default function CategoriasPage() {
  const filtros = useMaestroFilters()
  const { data, isLoading, isError, error } = useCategorias(filtros.params)
  const [modal, setModal] = useState<{ categoria: Categoria | null; clave: number } | null>(null)

  const anular = useAnularCategoria()
  const reactivar = useReactivarCategoria()
  const openConfirm = useUiStore((s) => s.openConfirm)
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN')) // oculta acciones; la autorización real es la del backend
  const { exito, fallo } = useResultado()

  const columnas: Column<Categoria>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      render: (c) => <span className="font-semibold">{c.nombre}</span>,
    },
    { key: 'descripcion', header: 'Descripción', render: (c) => c.descripcion ?? '—' },
    {
      key: 'padre',
      header: 'Categoría padre',
      render: (c) => (c.parent_id === null ? 'Raíz' : (c.parent_nombre ?? `#${c.parent_id}`)),
    },
  ]

  function pedirAnulacion(c: Categoria) {
    openConfirm({
      titulo: 'Anular categoría',
      mensaje: `¿Anular la categoría "${c.nombre}"? Dejará de mostrarse en el catálogo. Podés reactivarla después.`,
      confirmLabel: 'Anular',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await anular.mutateAsync(c.id)
          exito({
            titulo: 'Categoría anulada',
            mensaje: `"${c.nombre}" se anuló correctamente.`,
            ...VOLVER,
          })
        } catch (e) {
          fallo({
            titulo: 'No se pudo anular la categoría',
            mensaje: getErrorMessage(e),
            ...VOLVER,
          })
        }
      },
    })
  }

  async function reactivarCategoria(c: Categoria) {
    try {
      await reactivar.mutateAsync(c.id)
      exito({
        titulo: 'Categoría reactivada',
        mensaje: `"${c.nombre}" volvió a estar activa.`,
        ...VOLVER,
      })
    } catch (e) {
      fallo({ titulo: 'No se pudo reactivar la categoría', mensaje: getErrorMessage(e), ...VOLVER })
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Categorías</h1>
      <Card className="overflow-hidden p-0">
        <FilterBar
          search={filtros.search}
          onSearchChange={filtros.setSearch}
          estado={filtros.estado}
          onEstadoChange={filtros.setEstado}
          action={
            esAdmin && (
              <Button onClick={() => setModal({ categoria: null, clave: Date.now() })}>
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
            rowKey={(c) => c.id}
            isLoading={isLoading}
            isInactive={(c) => c.deleted_at !== null}
            emptyTitle="No hay categorías"
            emptyDescription="Probá con otros filtros o agregá una categoría nueva."
            actions={
              esAdmin
                ? (c) =>
                    c.deleted_at ? (
                      <Button size="sm" variant="secondary" onClick={() => reactivarCategoria(c)}>
                        Reactivar
                      </Button>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setModal({ categoria: c, clave: Date.now() })}
                        >
                          Modificar
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => pedirAnulacion(c)}>
                          Anular
                        </Button>
                      </>
                    )
                : undefined
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
        <CategoriaFormModal
          key={modal.clave}
          categoria={modal.categoria}
          onClose={() => setModal(null)}
          onSaved={(guardada, modo) => {
            setModal(null)
            exito({
              titulo: modo === 'create' ? 'Categoría creada' : 'Categoría actualizada',
              mensaje: `"${guardada.nombre}" se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
    </div>
  )
}
