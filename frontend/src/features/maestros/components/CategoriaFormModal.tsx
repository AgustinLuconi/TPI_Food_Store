import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { useCategorias, useGuardarCategoria } from '../hooks/useCategorias'
import type { Categoria } from '../types'

interface Props {
  /** null = alta; con valor = edición. */
  categoria: Categoria | null
  onClose: () => void
  onSaved: (guardada: Categoria, modo: 'create' | 'edit') => void
}

const TODAS_ACTIVAS = { search: '', estado: 'activos', page: 1, size: 100 } as const

export function CategoriaFormModal({ categoria, onClose, onSaved }: Props) {
  const mode = categoria ? 'edit' : 'create'
  const [nombre, setNombre] = useState(categoria?.nombre ?? '')
  const [descripcion, setDescripcion] = useState(categoria?.descripcion ?? '')
  const [parentId, setParentId] = useState(categoria?.parent_id?.toString() ?? '')
  const [errorNombre, setErrorNombre] = useState<string | null>(null)

  const guardar = useGuardarCategoria()
  const { data: candidatas } = useCategorias(TODAS_ACTIVAS)

  // Una categoría no puede ser su propio padre; los ciclos más profundos los rechaza el servidor.
  const opcionesPadre = [
    { value: '', label: 'Ninguna (categoría raíz)' },
    ...(candidatas?.items ?? [])
      .filter((c) => c.id !== categoria?.id)
      .map((c) => ({ value: String(c.id), label: c.nombre })),
  ]

  function enviar() {
    if (!nombre.trim()) return setErrorNombre('Ingresá un nombre')
    setErrorNombre(null)
    guardar.mutate(
      {
        id: categoria?.id,
        input: {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          parent_id: parentId ? Number(parentId) : null,
        },
      },
      { onSuccess: (guardada) => onSaved(guardada, mode) },
    )
  }

  const error = guardar.error ? toApiError(guardar.error) : null
  const deCampo = (campo: string) => (error?.field === campo ? error.message : undefined)

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="categoría"
      onClose={onClose}
      onSubmit={enviar}
      isSubmitting={guardar.isPending}
      error={error && !error.field ? error.message : null}
    >
      <Input
        label="Nombre"
        required
        maxLength={100}
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        error={errorNombre ?? deCampo('nombre')}
      />
      <Input
        label="Descripción"
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
      />
      <Select
        label="Categoría padre"
        value={parentId}
        options={opcionesPadre}
        onChange={(e) => setParentId(e.target.value)}
        error={deCampo('parent_id')}
      />
    </EntityFormModal>
  )
}
