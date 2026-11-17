import { describe, expect, it } from 'vitest'
import { decimalesDe, formatearCantidad, formatearDinero, urlDeMedia } from './formato'

describe('formato', () => {
  it('da formato de moneda argentina', () => {
    expect(formatearDinero('9500.00')).toBe('$ 9.500,00')
    expect(formatearDinero(0)).toBe('$ 0,00')
  })

  it('muestra cantidades sin ceros de relleno', () => {
    expect(formatearCantidad('0.300')).toBe('0,3')
    expect(formatearCantidad('10.000')).toBe('10')
    expect(formatearCantidad('2.5')).toBe('2,5')
  })

  it('antepone el origen del backend a las rutas de media', () => {
    expect(urlDeMedia('/media/productos/a.jpg')).toBe('http://localhost:8000/media/productos/a.jpg')
    expect(urlDeMedia('https://cdn.test/a.jpg')).toBe('https://cdn.test/a.jpg')
    expect(urlDeMedia(null)).toBeNull()
    expect(urlDeMedia('')).toBeNull()
  })

  it('cuenta decimales', () => {
    expect(decimalesDe('0.300')).toBe(3)
    expect(decimalesDe('12')).toBe(0)
  })
})
