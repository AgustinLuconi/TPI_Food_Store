import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { useGuardarCategoria, useOpcionesDeCategoria } from '../hooks/useCategorias'
import { idsDelSubarbol } from '../lib/arbolCategorias'
import type { Categoria } from '../types'

interface Props {
  /** null = alta; con valor = edición. */
  categoria: Categoria | null
  onClose: () => void
  onSaved: (guardada: Categoria, modo: 'create' | 'edit') => void
}

export function CategoriaFormModal({ categoria, onClose, onSaved }: Props) {
  const mode = categoria ? 'edit' : 'create'
  const [nombre, setNombre] = useState(categoria?.nombre ?? '')
  const [descripcion, setDescripcion] = useState(categoria?.descripcion ?? '')
  const [parentId, setParentId] = useState(categoria?.parent_id?.toString() ?? '')
  const [errorNombre, setErrorNombre] = useState<string | null>(null)

  const guardar = useGuardarCategoria()
  const { data } = useOpcionesDeCategoria()

  // Ni la categoría ni sus descendientes pueden ser su padre (el servidor también lo rechaza).
  const excluidas = categoria && data ? idsDelSubarbol(data.arbol, categoria.id) : new Set<number>()
  const opcionesPadre = [
    { value: '', label: 'Ninguna (categoría raíz)' },
    ...(data?.opciones ?? [])
      .filter((o) => !excluidas.has(o.id))
      .map((o) => ({ value: String(o.id), label: o.ruta })),
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
