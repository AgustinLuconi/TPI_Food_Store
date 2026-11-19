import { describe, expect, it } from 'vitest'
import { coordenadasIncompletas, leerPunto, redondear } from './coordenadas'

describe('coordenadas', () => {
  it('lee un punto válido, también con coma decimal', () => {
    expect(leerPunto('-34.6037', '-58.3816')).toEqual({ lat: -34.6037, lng: -58.3816 })
    expect(leerPunto('-34,6037', '-58,3816')).toEqual({ lat: -34.6037, lng: -58.3816 })
  })

  it('rechaza vacíos, texto y valores fuera de rango', () => {
    expect(leerPunto('', '-58')).toBeNull()
    expect(leerPunto('abc', '-58')).toBeNull()
    expect(leerPunto('91', '0')).toBeNull()
    expect(leerPunto('0', '181')).toBeNull()
  })

  it('detecta un par incompleto', () => {
    expect(coordenadasIncompletas('-34', '')).toBe(true)
    expect(coordenadasIncompletas('', '')).toBe(false)
    expect(coordenadasIncompletas('-34', '-58')).toBe(false)
  })

  it('redondea a 6 decimales', () => {
    expect(redondear(-34.60371234567)).toBe(-34.603712)
  })
})
