import { describe, expect, it } from 'vitest'
import { nombreDeEstado, puedeCancelar, siguienteEstado } from './estados'

describe('estados del pedido', () => {
  it('el dueño cancela solo en PENDIENTE o CONFIRMADO; el personal en cualquier estado no terminal', () => {
    expect(puedeCancelar('PENDIENTE', false)).toBe(true)
    expect(puedeCancelar('CONFIRMADO', false)).toBe(true)
    expect(puedeCancelar('EN_PREPARACION', false)).toBe(false)
    expect(puedeCancelar('EN_PREPARACION', true)).toBe(true)
    expect(puedeCancelar('EN_CAMINO', true)).toBe(true)
    expect(puedeCancelar('ENTREGADO', true)).toBe(false)
    expect(puedeCancelar('CANCELADO', true)).toBe(false)
  })

  it('el siguiente estado sigue el camino y PENDIENTE solo avanza con el pago', () => {
    expect(siguienteEstado('PENDIENTE')).toBeNull()
    expect(siguienteEstado('CONFIRMADO')).toBe('EN_PREPARACION')
    expect(siguienteEstado('EN_PREPARACION')).toBe('EN_CAMINO')
    expect(siguienteEstado('EN_CAMINO')).toBe('ENTREGADO')
    expect(siguienteEstado('ENTREGADO')).toBeNull()
    expect(siguienteEstado('CANCELADO')).toBeNull()
  })

  it('en retiro, EN_CAMINO se muestra como "Listo para retirar"', () => {
    expect(nombreDeEstado('EN_CAMINO', false)).toBe('Listo para retirar')
    expect(nombreDeEstado('EN_CAMINO', true)).toBe('En camino')
  })
})
