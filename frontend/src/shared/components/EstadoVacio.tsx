import type { ReactNode } from 'react'

interface EstadoVacioProps {
  titulo: string
  descripcion?: string
  accion?: ReactNode
}

/** Estado vacío explícito: nunca una grilla en blanco sin explicación. */
export function EstadoVacio({ titulo, descripcion, accion }: EstadoVacioProps) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <p className="text-base font-bold text-navy-900">{titulo}</p>
      {descripcion && <p className="max-w-md text-sm text-navy-500">{descripcion}</p>}
      {accion && <div className="mt-2">{accion}</div>}
    </div>
  )
}
