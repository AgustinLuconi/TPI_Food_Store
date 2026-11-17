import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from './cn'

export interface Pestana {
  id: string
  label: string
  contenido: ReactNode
}

interface TabsProps {
  pestanas: Pestana[]
  activa: string
  onChange: (id: string) => void
  etiqueta: string
}

/** Pestañas accesibles (patrón WAI-ARIA): flechas para moverse, solo la activa entra en el orden de tabulación. */
export function Tabs({ pestanas, activa, onChange, etiqueta }: TabsProps) {
  const base = useId()
  const botones = useRef<Record<string, HTMLButtonElement | null>>({})

  function alPulsar(e: KeyboardEvent, indice: number) {
    const mover = { ArrowRight: 1, ArrowLeft: -1 }[e.key]
    if (mover === undefined) return
    e.preventDefault()
    const siguiente = pestanas[(indice + mover + pestanas.length) % pestanas.length]
    onChange(siguiente.id)
    botones.current[siguiente.id]?.focus()
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label={etiqueta}
        className="flex flex-wrap gap-1 border-b border-surface-border"
      >
        {pestanas.map((p, i) => (
          <button
            key={p.id}
            ref={(el) => {
              botones.current[p.id] = el
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${p.id}`}
            aria-selected={activa === p.id}
            aria-controls={`${base}-panel-${p.id}`}
            tabIndex={activa === p.id ? 0 : -1}
            onClick={() => onChange(p.id)}
            onKeyDown={(e) => alPulsar(e, i)}
            className={cn(
              '-mb-px rounded-t-lg border-b-2 px-4 py-2.5 text-sm font-semibold transition-colors',
              activa === p.id
                ? 'border-accent-600 text-navy-900'
                : 'border-transparent text-navy-500 hover:text-navy-900',
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      {pestanas.map(
        (p) =>
          activa === p.id && (
            <div
              key={p.id}
              role="tabpanel"
              id={`${base}-panel-${p.id}`}
              aria-labelledby={`${base}-tab-${p.id}`}
            >
              {p.contenido}
            </div>
          ),
      )}
    </div>
  )
}
