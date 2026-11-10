import type { ReactNode } from 'react'
import { Input } from '@/shared/ui/Input'
import { cn } from '@/shared/ui/cn'
import { Select, type SelectOption } from '@/shared/ui/Select'
import type { EstadoFiltro } from '@/shared/types/common'

interface FilterBarProps {
  search: string
  onSearchChange: (valor: string) => void
  searchLabel?: string
  searchPlaceholder?: string
  /** Combo de agrupación opcional (categoría, rol). */
  group?: {
    label: string
    value: string
    options: SelectOption[]
    onChange: (valor: string) => void
  }
  estado: EstadoFiltro
  onEstadoChange: (estado: EstadoFiltro) => void
  /** Botón primario "Agregar", arriba a la derecha. */
  action?: ReactNode
}

const ESTADOS: { value: EstadoFiltro; label: string }[] = [
  { value: 'activos', label: 'Activos' },
  { value: 'inactivos', label: 'Inactivos' },
  { value: 'todos', label: 'Todos' },
]

/** Búsqueda parcial (el debounce lo aplica quien consulta), agrupación y estado (Activos por defecto). */
export function FilterBar({
  search,
  onSearchChange,
  searchLabel = 'Buscar',
  searchPlaceholder = 'Buscar por nombre…',
  group,
  estado,
  onEstadoChange,
  action,
}: FilterBarProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-surface-border p-4 lg:flex-row lg:items-end">
      <div className="min-w-0 flex-1 lg:max-w-xs">
        <Input
          label={searchLabel}
          type="search"
          value={search}
          placeholder={searchPlaceholder}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      {group && (
        <div className="lg:w-56">
          <Select
            label={group.label}
            value={group.value}
            options={group.options}
            onChange={(e) => group.onChange(e.target.value)}
          />
        </div>
      )}
      <fieldset className="flex flex-col gap-1">
        <legend className="mb-1 text-sm font-semibold text-navy-900">Estado</legend>
        <div className="inline-flex overflow-hidden rounded-lg border border-surface-border">
          {ESTADOS.map((e) => (
            <button
              key={e.value}
              type="button"
              aria-pressed={estado === e.value}
              onClick={() => onEstadoChange(e.value)}
              className={cn(
                'px-3 py-2 text-sm font-semibold transition-colors',
                estado === e.value
                  ? 'bg-navy-900 text-white'
                  : 'bg-white text-navy-700 hover:bg-surface-muted',
              )}
            >
              {e.label}
            </button>
          ))}
        </div>
      </fieldset>
      {action && <div className="lg:ml-auto">{action}</div>}
    </div>
  )
}
