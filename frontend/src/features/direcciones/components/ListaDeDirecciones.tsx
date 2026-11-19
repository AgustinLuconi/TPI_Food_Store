import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import type { Direccion } from '../types'

export function textoDeDireccion(d: Direccion): string {
  return [d.linea1, d.linea2, d.ciudad, d.provincia].filter(Boolean).join(', ')
}

interface Props {
  direcciones: Direccion[]
  onEditar: (d: Direccion) => void
  onEliminar: (d: Direccion) => void
  onPrincipal: (d: Direccion) => void
}

export function ListaDeDirecciones({ direcciones, onEditar, onEliminar, onPrincipal }: Props) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {direcciones.map((d) => (
        <li
          key={d.id}
          className="flex flex-col gap-3 rounded-xl border border-surface-border bg-white p-4"
        >
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-navy-900">{d.alias ?? 'Dirección'}</h3>
            {d.es_principal && <Badge tone="accent">Principal</Badge>}
            {d.lat === null && <Badge tone="danger">Sin ubicación</Badge>}
          </div>
          <p className="text-sm text-navy-700">{textoDeDireccion(d)}</p>
          <div className="mt-auto flex flex-wrap gap-2">
            {!d.es_principal && (
              <Button size="sm" variant="secondary" onClick={() => onPrincipal(d)}>
                Hacer principal
              </Button>
            )}
            <Button size="sm" variant="secondary" onClick={() => onEditar(d)}>
              Modificar
            </Button>
            <Button size="sm" variant="danger" onClick={() => onEliminar(d)}>
              Eliminar
            </Button>
          </div>
        </li>
      ))}
    </ul>
  )
}
