import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Skeleton } from '@/shared/components/Skeleton'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { useUiStore } from '@/store/uiStore'
import { DireccionFormModal } from '../components/DireccionFormModal'
import { ListaDeDirecciones, textoDeDireccion } from '../components/ListaDeDirecciones'
import { useDirecciones, useEliminarDireccion, useMarcarPrincipal } from '../hooks/useDirecciones'
import type { Direccion } from '../types'

const VOLVER = { volverA: RUTAS.direcciones, volverLabel: 'Volver a mis direcciones' }

/** Mis direcciones de entrega, con el punto marcado en un mapa. */
export default function DireccionesPage() {
  const { data, isLoading, isError, error } = useDirecciones()
  const [modal, setModal] = useState<{ direccion: Direccion | null; clave: number } | null>(null)
  const eliminar = useEliminarDireccion()
  const principal = useMarcarPrincipal()
  const openConfirm = useUiStore((s) => s.openConfirm)
  const { exito, fallo } = useResultado()

  function pedirEliminar(d: Direccion) {
    openConfirm({
      titulo: 'Eliminar dirección',
      mensaje: `¿Eliminar "${textoDeDireccion(d)}"? Tus pedidos anteriores no se modifican.`,
      confirmLabel: 'Eliminar',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await eliminar.mutateAsync(d.id)
          exito({
            titulo: 'Dirección eliminada',
            mensaje: 'La dirección se eliminó correctamente.',
            ...VOLVER,
          })
        } catch (e) {
          fallo({
            titulo: 'No se pudo eliminar la dirección',
            mensaje: getErrorMessage(e),
            ...VOLVER,
          })
        }
      },
    })
  }

  async function hacerPrincipal(d: Direccion) {
    try {
      await principal.mutateAsync(d.id)
    } catch (e) {
      fallo({
        titulo: 'No se pudo cambiar la dirección principal',
        mensaje: getErrorMessage(e),
        ...VOLVER,
      })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-extrabold text-navy-900">Mis direcciones</h1>
        <Button onClick={() => setModal({ direccion: null, clave: Date.now() })}>+ Agregar</Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : isError ? (
        <p role="alert" className="text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : data && data.length > 0 ? (
        <ListaDeDirecciones
          direcciones={data}
          onEditar={(d) => setModal({ direccion: d, clave: Date.now() })}
          onEliminar={pedirEliminar}
          onPrincipal={hacerPrincipal}
        />
      ) : (
        <div className="rounded-xl border border-surface-border bg-white">
          <EstadoVacio
            titulo="Todavía no tenés direcciones"
            descripcion="Agregá una para pedir con envío a domicilio."
          />
        </div>
      )}
      {modal && (
        <DireccionFormModal
          key={modal.clave}
          direccion={modal.direccion}
          onClose={() => setModal(null)}
          onSaved={(guardada, modo) => {
            setModal(null)
            exito({
              titulo: modo === 'create' ? 'Dirección agregada' : 'Dirección actualizada',
              mensaje: `"${textoDeDireccion(guardada)}" se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
    </div>
  )
}
