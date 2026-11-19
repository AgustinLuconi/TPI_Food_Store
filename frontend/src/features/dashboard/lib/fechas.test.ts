import { describe, expect, it } from 'vitest'
import { fechaCorta, restarDias } from './fechas'

describe('fechas del panel', () => {
  it('resta días de calendario, también cruzando mes y año', () => {
    expect(restarDias('2026-11-17', 6)).toBe('2026-11-11')
    expect(restarDias('2026-03-01', 1)).toBe('2026-02-28')
    expect(restarDias('2026-01-02', 5)).toBe('2025-12-28')
    expect(restarDias('2026-11-17', 0)).toBe('2026-11-17')
  })

  it('acorta la fecha para el eje', () => {
    expect(fechaCorta('2026-11-07')).toBe('07/11')
  })
})
