import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { useGuardarIngrediente } from '../hooks/useCatalogo'
import { UNIDADES_SUGERIDAS, type Ingrediente } from '../types'

interface Props {
  ingrediente: Ingrediente | null
  onClose: () => void
  onSaved: (guardado: Ingrediente, modo: 'create' | 'edit') => void
}

export function IngredienteFormModal({ ingrediente, onClose, onSaved }: Props) {
  const mode = ingrediente ? 'edit' : 'create'
  const [nombre, setNombre] = useState(ingrediente?.nombre ?? '')
  const [unidad, setUnidad] = useState(ingrediente?.unidad_medida ?? '')
  const [esAlergeno, setEsAlergeno] = useState(ingrediente?.es_alergeno ?? false)
  const [esElaborado, setEsElaborado] = useState(ingrediente?.es_elaborado ?? false)
  const [stockMinimo, setStockMinimo] = useState(String(ingrediente?.stock_minimo ?? 0))
  const [errores, setErrores] = useState<Record<string, string>>({})
  const guardar = useGuardarIngrediente()

  function enviar() {
    const nuevos: Record<string, string> = {}
    if (!nombre.trim()) nuevos.nombre = 'Ingresá un nombre'
    if (!unidad.trim()) nuevos.unidad = 'Indicá la unidad en la que se mide'
    if (!/^\d+$/.test(stockMinimo)) nuevos.stockMinimo = 'Ingresá un número entero (0 o más)'
    setErrores(nuevos)
    if (Object.keys(nuevos).length > 0) return
    guardar.mutate(
      {
        id: ingrediente?.id,
        input: {
          nombre: nombre.trim(),
          unidad_medida: unidad.trim().toUpperCase(),
          es_alergeno: esAlergeno,
          es_elaborado: esElaborado,
          stock_minimo: Number(stockMinimo),
        },
      },
      { onSuccess: (guardado) => onSaved(guardado, mode) },
    )
  }

  const error = guardar.error ? toApiError(guardar.error) : null
  const deCampo = (campo: string) => (error?.field === campo ? error.message : undefined)

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="ingrediente"
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
        error={errores.nombre ?? deCampo('nombre')}
      />
      <datalist id="unidades-sugeridas">
        {UNIDADES_SUGERIDAS.map((u) => (
          <option key={u} value={u} />
        ))}
      </datalist>
      <Input
        label="Unidad de medida"
        required
        list="unidades-sugeridas"
        maxLength={10}
        placeholder="KG, G, L, ML, UN…"
        hint="Se usa siempre: en las recetas y en el stock. No se puede cambiar si ya está en una receta o tiene stock."
        value={unidad}
        onChange={(e) => setUnidad(e.target.value)}
        error={errores.unidad ?? deCampo('unidad_medida')}
      />
      <Input
        label="Stock mínimo"
        inputMode="numeric"
        value={stockMinimo}
        onChange={(e) => setStockMinimo(e.target.value)}
        error={errores.stockMinimo ?? deCampo('stock_minimo')}
      />
      <Checkbox
        label="Es alérgeno"
        hint="Se informa a los clientes en los productos que lo usan."
        checked={esAlergeno}
        onChange={(e) => setEsAlergeno(e.target.checked)}
      />
      <Checkbox
        label="Es elaborado"
        hint="Sub-ensamble con receta propia (por ejemplo, la salsa base). Se produce con una orden de producción."
        checked={esElaborado}
        onChange={(e) => setEsElaborado(e.target.checked)}
      />
      {deCampo('es_elaborado') && (
        <p className="text-sm text-danger-700">{deCampo('es_elaborado')}</p>
      )}
    </EntityFormModal>
  )
}
