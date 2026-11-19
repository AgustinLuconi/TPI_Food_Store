import type { ReactNode } from 'react'
import { Card } from '@/shared/ui/Card'

export function KpiCard({
  titulo,
  valor,
  ayuda,
}: {
  titulo: string
  valor: ReactNode
  ayuda?: string
}) {
  return (
    <Card className="flex flex-col gap-1">
      <p className="text-sm font-semibold text-navy-500">{titulo}</p>
      <p className="text-2xl font-extrabold text-navy-900">{valor}</p>
      {ayuda && <p className="text-xs text-navy-500">{ayuda}</p>}
    </Card>
  )
}

interface ChartCardProps {
  titulo: string
  /** Lo que muestra el gráfico, para quien no lo ve: es su nombre accesible. */
  descripcion: string
  children: ReactNode
  /** Encabezados y filas de la tabla alternativa con los mismos datos. */
  tabla: { columnas: string[]; filas: (string | number)[][] }
  vacio?: boolean
}

/** Un gráfico con su equivalente en tabla: los datos no dependen de poder ver colores ni formas. */
export function ChartCard({ titulo, descripcion, children, tabla, vacio = false }: ChartCardProps) {
  return (
    <Card className="flex flex-col gap-3">
      <h2 className="font-bold text-navy-900">{titulo}</h2>
      {vacio ? (
        <p className="py-8 text-center text-sm text-navy-500">Todavía no hay datos para mostrar.</p>
      ) : (
        <div role="img" aria-label={descripcion} className="h-64 w-full">
          {children}
        </div>
      )}
      {!vacio && (
        <details className="text-sm">
          <summary className="cursor-pointer font-semibold text-accent-700">
            Ver los datos en una tabla
          </summary>
          <div className="mt-2 max-h-56 overflow-auto">
            <table className="w-full text-left">
              <caption className="sr-only">{titulo}</caption>
              <thead className="text-xs uppercase text-navy-500">
                <tr>
                  {tabla.columnas.map((c) => (
                    <th key={c} scope="col" className="py-1 pr-3">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {tabla.filas.map((f, i) => (
                  <tr key={i}>
                    {f.map((celda, j) => (
                      <td key={j} className="py-1 pr-3">
                        {celda}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </Card>
  )
}

export function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section aria-label={titulo} className="flex flex-col gap-3">
      <h2 className="text-lg font-bold text-navy-900">{titulo}</h2>
      {children}
    </section>
  )
}

export function Cargando({ alto = 'h-64' }: { alto?: string }) {
  return (
    <div
      aria-busy="true"
      role="status"
      aria-label="Cargando"
      className={`${alto} w-full animate-pulse rounded-xl bg-surface-border`}
    />
  )
}
