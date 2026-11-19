import { describe, expect, it } from 'vitest'
import { fechaEnZona } from './useEstadoLocal'

describe('fechaEnZona', () => {
  it('la misma hora puede ser otro día según la zona del local', () => {
    // 01:00 UTC del 17/11 son las 22:00 del 16/11 en Buenos Aires y las 10:00 del 17/11 en Tokio.
    const instante = new Date('2026-11-17T01:00:00Z')
    expect(fechaEnZona(instante, 'UTC')).toBe('2026-11-17')
    expect(fechaEnZona(instante, 'America/Argentina/Buenos_Aires')).toBe('2026-11-16')
    expect(fechaEnZona(instante, 'Asia/Tokyo')).toBe('2026-11-17')
  })
})
