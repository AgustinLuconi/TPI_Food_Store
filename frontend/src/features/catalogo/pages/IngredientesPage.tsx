import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { FilterBar } from '@/shared/components/FilterBar'
import { Paginacion } from '@/shared/components/Paginacion'
import { useMaestroFilters } from '@/shared/hooks/useMaestroFilters'
import { useResultado } from '@/shared/hooks/useResultado'
import { formatearCantidad } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import { IngredienteFormModal } from '../components/IngredienteFormModal'
import { RecetaModal } from '../components/RecetaModal'
import {
  useAnularIngrediente,
  useIngredientes,
  useReactivarIngrediente,
} from '../hooks/useCatalogo'
import { TIPO_INGREDIENTE, type Ingrediente } from '../types'

const VOLVER = { volverA: RUTAS.adminIngredientes, volverLabel: 'Volver a ingredientes' }

const OPCIONES_TIPO = [
  { value: '', label: 'Todos los ingredientes' },
  { value: TIPO_INGREDIENTE.alergeno, label: 'Solo alérgenos' },
  { value: TIPO_INGREDIENTE.elaborado, label: 'Solo elaborados' },
]

export default function IngredientesPage() {
  const filtros = useMaestroFilters()
  const { data, isLoading, isError, error } = useIngredientes(filtros.params)
  const [modal, setModal] = useState<{ ingrediente: Ingrediente | null; clave: number } | null>(
    null,
  )
  const [receta, setReceta] = useState<Ingrediente | null>(null)

  const anular = useAnularIngrediente()
  const reactivar = useReactivarIngrediente()
  const openConfirm = useUiStore((s) => s.openConfirm)
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN'))
  const { exito, fallo } = useResultado()

  const columnas: Column<Ingrediente>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      sortKey: 'nombre',
      render: (i) => <span className="font-semibold">{i.nombre}</span>,
    },
    {
      key: 'tipo',
      header: 'Tipo',
      render: (i) => (
        <span className="flex flex-wrap gap-1">
          {i.es_alergeno && <Badge tone="danger">Alérgeno</Badge>}
          {i.es_elaborado && <Badge tone="accent">Elaborado</Badge>}
          {!i.es_alergeno && !i.es_elaborado && '—'}
        </span>
      ),
    },
    {
      key: 'stock',
      header: 'Stock real / disp.',
      render: (i) =>
        i.stock_real === null ? (
          '—'
        ) : (
          <span
            className={
              Number(i.stock_disponible) <= i.stock_minimo
                ? 'font-semibold text-danger-700'
                : undefined
            }
          >
            {formatearCantidad(i.stock_real)} / {formatearCantidad(i.stock_disponible ?? 0)}
          </span>
        ),
    },
    { key: 'minimo', header: 'Mínimo', render: (i) => i.stock_minimo },
  ]

  function pedirAnulacion(i: Ingrediente) {
    openConfirm({
      titulo: 'Anular ingrediente',
      mensaje: `¿Anular "${i.nombre}"? No se puede si lo usa alguna receta de un producto o elaborado activo.`,
      confirmLabel: 'Anular',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await anular.mutateAsync(i.id)
          exito({
            titulo: 'Ingrediente anulado',
            mensaje: `"${i.nombre}" se anuló correctamente.`,
            ...VOLVER,
          })
        } catch (e) {
          fallo({
            titulo: 'No se pudo anular el ingrediente',
            mensaje: getErrorMessage(e),
            ...VOLVER,
          })
        }
      },
    })
  }

  async function reactivarIngrediente(i: Ingrediente) {
    try {
      await reactivar.mutateAsync(i.id)
      exito({
        titulo: 'Ingrediente reactivado',
        mensaje: `"${i.nombre}" volvió a estar activo.`,
        ...VOLVER,
      })
    } catch (e) {
      fallo({
        titulo: 'No se pudo reactivar el ingrediente',
        mensaje: getErrorMessage(e),
        ...VOLVER,
      })
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Ingredientes</h1>
      <Card className="overflow-hidden p-0">
        <FilterBar
          search={filtros.search}
          onSearchChange={filtros.setSearch}
          group={{
            label: 'Tipo',
            value: filtros.grupo,
            options: OPCIONES_TIPO,
            onChange: filtros.setGrupo,
          }}
          estado={filtros.estado}
          onEstadoChange={filtros.setEstado}
          action={
            esAdmin && (
              <Button onClick={() => setModal({ ingrediente: null, clave: Date.now() })}>
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
            rowKey={(i) => i.id}
            isLoading={isLoading}
            isInactive={(i) => i.deleted_at !== null}
            orden={filtros.orden}
            onOrdenChange={filtros.ordenarPor}
            emptyTitle="No hay ingredientes"
            emptyDescription="Probá con otros filtros o agregá un ingrediente nuevo."
            actions={
              esAdmin
                ? (i) =>
                    i.deleted_at ? (
                      <Button size="sm" variant="secondary" onClick={() => reactivarIngrediente(i)}>
                        Reactivar
                      </Button>
                    ) : (
                      <>
                        {i.es_elaborado && (
                          <Button size="sm" variant="secondary" onClick={() => setReceta(i)}>
                            Receta
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setModal({ ingrediente: i, clave: Date.now() })}
                        >
                          Modificar
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => pedirAnulacion(i)}>
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
        <IngredienteFormModal
          key={modal.clave}
          ingrediente={modal.ingrediente}
          onClose={() => setModal(null)}
          onSaved={(guardado, modo) => {
            setModal(null)
            exito({
              titulo: modo === 'create' ? 'Ingrediente creado' : 'Ingrediente actualizado',
              mensaje: `"${guardado.nombre}" se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
      {receta && (
        <RecetaModal
          tipo="ingrediente"
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
