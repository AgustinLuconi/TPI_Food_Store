import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/Button'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { Modal } from '@/shared/ui/Modal'
import { Select } from '@/shared/ui/Select'
import { Spinner } from '@/shared/ui/Spinner'
import {
  useGuardarReceta,
  useOpcionesDeIngrediente,
  useReceta,
  type TipoReceta,
} from '../hooks/useCatalogo'
import { UNIDADES_SUGERIDAS, type LineaReceta } from '../types'

interface Props {
  tipo: TipoReceta
  /** Producto o ingrediente elaborado dueño de la receta. */
  id: number
  nombre: string
  onClose: () => void
  onSaved: () => void
}

interface Fila {
  clave: number
  ingredienteId: string
  cantidad: string
  unidad: string
  removible: boolean
}

let contador = 0
const filaVacia = (): Fila => ({
  clave: ++contador,
  ingredienteId: '',
  cantidad: '',
  unidad: 'KG',
  removible: false,
})

/**
 * Editor de recetas, para el producto (con "removible") y para un ingrediente elaborado. Reemplaza la receta
 * completa. La unidad de cada ingrediente es única en todo el sistema (RN-10): el servidor rechaza una distinta.
 */
export function RecetaModal({ tipo, id, nombre, onClose, onSaved }: Props) {
  const { data: guardada, isLoading, isError } = useReceta(tipo, id)
  return (
    <Modal open onClose={onClose} title={`Receta de ${nombre}`} footer={undefined}>
      {isLoading && (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      )}
      {isError && (
        <p role="alert" className="text-sm text-danger-700">
          No se pudo cargar la receta.
        </p>
      )}
      {guardada && (
        <Editor tipo={tipo} id={id} inicial={guardada} onClose={onClose} onSaved={onSaved} />
      )}
    </Modal>
  )
}

function Editor({
  tipo,
  id,
  inicial,
  onClose,
  onSaved,
}: Pick<Props, 'tipo' | 'id' | 'onClose' | 'onSaved'> & { inicial: LineaReceta[] }) {
  const [filas, setFilas] = useState<Fila[]>(
    inicial.length > 0
      ? inicial.map((l) => ({
          clave: ++contador,
          ingredienteId: String(l.ingrediente_id),
          cantidad: l.cantidad_requerida,
          unidad: l.unidad_medida,
          removible: l.es_removible,
        }))
      : [filaVacia()],
  )
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const { data: ingredientes = [] } = useOpcionesDeIngrediente()
  const guardar = useGuardarReceta(tipo, id)

  // Un elaborado no puede ser componente de sí mismo (el servidor también lo rechaza).
  const opciones = [
    { value: '', label: 'Elegí un ingrediente…' },
    ...ingredientes
      .filter((i) => tipo === 'producto' || i.id !== id)
      .map((i) => ({ value: String(i.id), label: i.nombre })),
  ]

  function cambiar(clave: number, cambios: Partial<Fila>) {
    setFilas((actuales) => actuales.map((f) => (f.clave === clave ? { ...f, ...cambios } : f)))
  }

  function enviar() {
    const completas = filas.filter((f) => f.ingredienteId || f.cantidad.trim())
    const ids = completas.map((f) => f.ingredienteId)
    if (completas.some((f) => !f.ingredienteId))
      return setErrorLocal('Elegí el ingrediente de cada fila.')
    if (
      completas.some((f) => !/^\d+(\.\d{1,3})?$/.test(f.cantidad.trim()) || Number(f.cantidad) <= 0)
    )
      return setErrorLocal('La cantidad debe ser mayor que 0, con hasta 3 decimales.')
    if (completas.some((f) => !f.unidad.trim()))
      return setErrorLocal('Indicá la unidad de cada fila.')
    if (new Set(ids).size !== ids.length)
      return setErrorLocal('Un ingrediente no puede repetirse en la receta.')
    setErrorLocal(null)
    guardar.mutate(
      completas.map((f) => ({
        ingrediente_id: Number(f.ingredienteId),
        nombre: '',
        cantidad_requerida: f.cantidad.trim(),
        unidad_medida: f.unidad.trim().toUpperCase(),
        es_removible: f.removible,
      })),
      { onSuccess: onSaved },
    )
  }

  const errorServidor = guardar.error ? toApiError(guardar.error).message : null

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        enviar()
      }}
      className="flex flex-col gap-4"
    >
      <datalist id="unidades-sugeridas">
        {UNIDADES_SUGERIDAS.map((u) => (
          <option key={u} value={u} />
        ))}
      </datalist>
      <p className="text-sm text-navy-500">
        {tipo === 'producto'
          ? 'Lo que consume cada unidad vendida. Los ingredientes removibles permiten pedir el producto "sin" ese ingrediente.'
          : 'Lo que consume cada unidad producida de este ingrediente elaborado.'}
      </p>
      {filas.map((f, i) => (
        <fieldset key={f.clave} className="grid gap-3 rounded-lg border border-surface-border p-3">
          <legend className="px-1 text-xs font-semibold uppercase text-navy-500">
            Ingrediente {i + 1}
          </legend>
          <Select
            label="Ingrediente"
            value={f.ingredienteId}
            options={opciones}
            onChange={(e) => cambiar(f.clave, { ingredienteId: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Cantidad"
              inputMode="decimal"
              value={f.cantidad}
              onChange={(e) => cambiar(f.clave, { cantidad: e.target.value })}
            />
            <Input
              label="Unidad"
              list="unidades-sugeridas"
              maxLength={10}
              value={f.unidad}
              onChange={(e) => cambiar(f.clave, { unidad: e.target.value })}
            />
          </div>
          <div className="flex items-center justify-between">
            {tipo === 'producto' ? (
              <Checkbox
                label="Removible"
                checked={f.removible}
                onChange={(e) => cambiar(f.clave, { removible: e.target.checked })}
              />
            ) : (
              <span />
            )}
            {filas.length > 1 && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setFilas((a) => a.filter((x) => x.clave !== f.clave))}
              >
                Quitar
              </Button>
            )}
          </div>
        </fieldset>
      ))}
      <div>
        <Button variant="secondary" size="sm" onClick={() => setFilas((a) => [...a, filaVacia()])}>
          + Agregar ingrediente
        </Button>
      </div>
      {(errorLocal ?? errorServidor) && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
          {errorLocal ?? errorServidor}
        </p>
      )}
      <div className="flex justify-end gap-3 border-t border-surface-border pt-4">
        <Button variant="secondary" onClick={onClose} disabled={guardar.isPending}>
          Cancelar
        </Button>
        <Button type="submit" loading={guardar.isPending}>
          Guardar receta
        </Button>
      </div>
    </form>
  )
}
