import type { Horario, HorarioInput } from '../types'

export interface Franja {
  clave: number
  apertura: string
  cierre: string
  activo: boolean
}

let contador = 0
export const nuevaFranja = (apertura = '11:00', cierre = '23:00'): Franja => ({
  clave: ++contador,
  apertura,
  cierre,
  activo: true,
})

/** "11:00:00" → "11:00" (lo que entiende <input type="time">). */
export const aHora = (h: string) => h.slice(0, 5)

/** Las franjas del servidor agrupadas por día de la semana (0 = lunes). */
export function agruparPorDia(horarios: Horario[]): Franja[][] {
  const dias: Franja[][] = Array.from({ length: 7 }, () => [])
  for (const h of horarios) {
    dias[h.dia_semana].push({
      clave: ++contador,
      apertura: aHora(h.hora_apertura),
      cierre: aHora(h.hora_cierre),
      activo: h.activo,
    })
  }
  return dias
}

export function aItems(dias: Franja[][]): HorarioInput[] {
  return dias.flatMap((franjas, dia) =>
    franjas.map((f) => ({
      dia_semana: dia,
      hora_apertura: f.apertura,
      hora_cierre: f.cierre,
      activo: f.activo,
    })),
  )
}

/** Primer problema de las franjas (mismo criterio que el servidor), o null si están bien. */
export function validarHorarios(dias: Franja[][], nombres: readonly string[]): string | null {
  for (let d = 0; d < dias.length; d++) {
    const franjas = dias[d]
    for (const f of franjas) {
      if (!f.apertura || !f.cierre)
        return `${nombres[d]}: completá la apertura y el cierre de cada franja.`
      if (f.cierre <= f.apertura)
        return `${nombres[d]}: el cierre debe ser posterior a la apertura.`
    }
    const activas = franjas
      .filter((f) => f.activo)
      .sort((a, b) => a.apertura.localeCompare(b.apertura))
    for (let i = 1; i < activas.length; i++) {
      if (activas[i].apertura < activas[i - 1].cierre)
        return `${nombres[d]}: hay franjas que se solapan.`
    }
  }
  return null
}
