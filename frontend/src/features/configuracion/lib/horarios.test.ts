import { describe, expect, it } from 'vitest'
import { DIAS } from '../types'
import { agruparPorDia, aItems, validarHorarios, type Franja } from './horarios'

const franja = (apertura: string, cierre: string, activo = true): Franja => ({
  clave: 0,
  apertura,
  cierre,
  activo,
})
const semana = (lunes: Franja[]): Franja[][] => [lunes, [], [], [], [], [], []]

describe('horarios', () => {
  it('agrupa por día y vuelve a aplanar', () => {
    const dias = agruparPorDia([
      { id: 1, dia_semana: 0, hora_apertura: '12:00:00', hora_cierre: '15:00:00', activo: true },
      { id: 2, dia_semana: 0, hora_apertura: '20:00:00', hora_cierre: '23:00:00', activo: false },
      { id: 3, dia_semana: 6, hora_apertura: '10:00:00', hora_cierre: '14:00:00', activo: true },
    ])
    expect(dias[0]).toHaveLength(2)
    expect(dias[6][0].apertura).toBe('10:00')
    expect(aItems(dias)).toEqual([
      { dia_semana: 0, hora_apertura: '12:00', hora_cierre: '15:00', activo: true },
      { dia_semana: 0, hora_apertura: '20:00', hora_cierre: '23:00', activo: false },
      { dia_semana: 6, hora_apertura: '10:00', hora_cierre: '14:00', activo: true },
    ])
  })

  it('valida que el cierre sea posterior a la apertura', () => {
    expect(validarHorarios(semana([franja('12:00', '12:00')]), DIAS)).toMatch(/posterior/)
    expect(validarHorarios(semana([franja('', '12:00')]), DIAS)).toMatch(/completá/)
    expect(validarHorarios(semana([franja('11:00', '23:00')]), DIAS)).toBeNull()
  })

  it('detecta franjas activas que se solapan, pero no las pegadas ni las inactivas', () => {
    expect(
      validarHorarios(semana([franja('10:00', '14:00'), franja('13:00', '16:00')]), DIAS),
    ).toMatch(/solapan/)
    expect(
      validarHorarios(semana([franja('10:00', '14:00'), franja('14:00', '18:00')]), DIAS),
    ).toBeNull()
    expect(
      validarHorarios(semana([franja('10:00', '14:00'), franja('13:00', '16:00', false)]), DIAS),
    ).toBeNull()
  })
})
