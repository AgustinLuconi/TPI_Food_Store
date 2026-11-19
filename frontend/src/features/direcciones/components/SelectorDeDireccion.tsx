import { useState } from 'react'
import { Button } from '@/shared/ui/Button'
import { useDirecciones } from '../hooks/useDirecciones'
import type { Direccion } from '../types'
import { DireccionFormModal } from './DireccionFormModal'
import { textoDeDireccion } from './ListaDeDirecciones'

interface Props {
  value: number | null
  onChange: (direccion: Direccion) => void
}

/** Elegir la dirección de entrega en el checkout, o agregar una nueva sin salir de la compra. */
export function SelectorDeDireccion({ value, onChange }: Props) {
  const { data = [], isLoading } = useDirecciones()
  const [agregando, setAgregando] = useState<number | null>(null)

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="mb-1 text-sm font-semibold text-navy-900">Dirección de entrega</legend>
      {isLoading && <p className="text-sm text-navy-500">Cargando tus direcciones…</p>}
      {!isLoading && data.length === 0 && (
        <p className="text-sm text-navy-700">Todavía no tenés direcciones guardadas.</p>
      )}
      {data.map((d) => (
        <label
          key={d.id}
          className="flex cursor-pointer items-start gap-3 rounded-lg border border-surface-border bg-white p-3 has-[:checked]:border-accent-600"
        >
          <input
            type="radio"
            name="direccion"
            className="mt-1 accent-accent-600"
            checked={value === d.id}
            onChange={() => onChange(d)}
          />
          <span className="text-sm">
            <span className="font-bold text-navy-900">{d.alias ?? 'Dirección'}</span>
            {d.es_principal && (
              <span className="ml-2 text-xs font-semibold text-accent-700">Principal</span>
            )}
            <span className="block text-navy-700">{textoDeDireccion(d)}</span>
            {d.lat === null && (
              <span className="block text-danger-700">
                Sin ubicación en el mapa: editala para poder calcular el envío.
              </span>
            )}
          </span>
        </label>
      ))}
      <div>
        <Button variant="secondary" size="sm" onClick={() => setAgregando(Date.now())}>
          + Agregar una dirección
        </Button>
      </div>
      {agregando !== null && (
        <DireccionFormModal
          key={agregando}
          direccion={null}
          onClose={() => setAgregando(null)}
          onSaved={(nueva) => {
            setAgregando(null)
            onChange(nueva)
          }}
        />
      )}
    </fieldset>
  )
}
