import { describe, expect, it } from 'vitest'
import { finDelDiaIso, hoyIso } from './fechas'

describe('fechas', () => {
  it('el vencimiento cae al final del día elegido, en hora local', () => {
    const d = new Date(finDelDiaIso('2026-12-31'))
    expect([d.getFullYear(), d.getMonth() + 1, d.getDate(), d.getHours(), d.getMinutes()]).toEqual([
      2026, 12, 31, 23, 59,
    ])
  })

  it('hoy tiene formato de input date', () => {
    expect(hoyIso()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })
})
