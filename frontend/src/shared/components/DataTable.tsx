import type { ReactNode } from 'react'
import type { Orden } from '@/shared/types/common'
import { Badge } from '@/shared/ui/Badge'
import { cn } from '@/shared/ui/cn'
import { EstadoVacio } from './EstadoVacio'
import { Skeleton } from './Skeleton'

export interface Column<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  className?: string
  /** Si se indica, el encabezado permite ordenar por este campo (el servidor aplica el orden). */
  sortKey?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string | number
  isLoading?: boolean
  /** Filas "inactivas" (dadas de baja): se muestran atenuadas con el badge "Inactivo". */
  isInactive?: (row: T) => boolean
  /** Acciones por fila (Modificar, Anular, Reactivar). */
  actions?: (row: T) => ReactNode
  emptyTitle?: string
  emptyDescription?: string
  skeletonRows?: number
  /** Orden actual y cambio de orden: la grilla no ordena en el cliente, lo pide al servidor. */
  orden?: Orden
  onOrdenChange?: (campo: string) => void
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  isInactive,
  actions,
  emptyTitle = 'No hay resultados',
  emptyDescription = 'Probá con otros filtros o agregá un registro nuevo.',
  skeletonRows = 5,
  orden,
  onOrdenChange,
}: DataTableProps<T>) {
  const colSpan = columns.length + (actions ? 1 : 0)

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-left text-sm">
        <thead className="bg-surface-muted text-xs uppercase tracking-wide text-navy-500">
          <tr>
            {columns.map((c) => (
              <EncabezadoDeColumna
                key={c.key}
                columna={c}
                orden={orden}
                onOrdenChange={onOrdenChange}
              />
            ))}
            {actions && (
              <th scope="col" className="px-4 py-3 text-right font-semibold">
                Acciones
              </th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {isLoading &&
            Array.from({ length: skeletonRows }, (_, i) => (
              <tr key={`sk-${i}`}>
                <td colSpan={colSpan} className="px-4 py-3">
                  <Skeleton className="h-5 w-full" />
                </td>
              </tr>
            ))}
          {!isLoading && rows.length === 0 && (
            <tr>
              <td colSpan={colSpan}>
                <EstadoVacio titulo={emptyTitle} descripcion={emptyDescription} />
              </td>
            </tr>
          )}
          {!isLoading &&
            rows.map((row) => {
              const inactivo = isInactive?.(row) ?? false
              return (
                <tr key={rowKey(row)} className={cn(inactivo && 'bg-surface-muted opacity-60')}>
                  {columns.map((c, i) => (
                    <td key={c.key} className={cn('px-4 py-3 align-middle', c.className)}>
                      {c.render(row)}
                      {i === 0 && inactivo && (
                        <span className="ml-2">
                          <Badge>Inactivo</Badge>
                        </span>
                      )}
                    </td>
                  ))}
                  {actions && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-2">{actions(row)}</div>
                    </td>
                  )}
                </tr>
              )
            })}
        </tbody>
      </table>
    </div>
  )
}

interface EncabezadoProps<T> {
  columna: Column<T>
  orden?: Orden
  onOrdenChange?: (campo: string) => void
}

/** Encabezado accesible: si la columna es ordenable es un botón, y el <th> informa aria-sort. */
function EncabezadoDeColumna<T>({ columna, orden, onOrdenChange }: EncabezadoProps<T>) {
  const { sortKey } = columna
  if (sortKey === undefined || onOrdenChange === undefined) {
    return (
      <th scope="col" className={cn('px-4 py-3 font-semibold', columna.className)}>
        {columna.header}
      </th>
    )
  }

  const activo = orden?.campo === sortKey
  const descendente = activo && orden.sentido === 'desc'
  return (
    <th
      scope="col"
      aria-sort={activo ? (descendente ? 'descending' : 'ascending') : 'none'}
      className={cn('px-4 py-3 font-semibold', columna.className)}
    >
      <button
        type="button"
        onClick={() => onOrdenChange(sortKey)}
        className={cn(
          'inline-flex items-center gap-1 uppercase tracking-wide hover:text-navy-900',
          activo && 'text-navy-900',
        )}
      >
        {columna.header}
        <span aria-hidden="true" className={cn(!activo && 'opacity-40')}>
          {descendente ? '▼' : '▲'}
        </span>
      </button>
    </th>
  )
}
