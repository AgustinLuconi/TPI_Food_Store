import { describe, expect, it } from 'vitest'
import { evaluarLinea, hayBloqueo } from './validacion'

const ok = {
  cargando: false,
  noExiste: false,
  producto: { disponible: true, precio_base: '9500.00' },
}

describe('evaluarLinea', () => {
  it('una línea al día está ok', () => {
    expect(evaluarLinea(9500, ok)).toEqual({ estado: 'ok', precioActual: 9500 })
  })

  it('un producto dado de baja (404) o no disponible bloquea', () => {
    expect(evaluarLinea(9500, { cargando: false, noExiste: true }).estado).toBe('no_disponible')
    expect(
      evaluarLinea(9500, { ...ok, producto: { disponible: false, precio_base: '9500.00' } }).estado,
    ).toBe('no_disponible')
  })

  it('un precio distinto se avisa con el precio vigente', () => {
    expect(evaluarLinea(9000, ok)).toEqual({ estado: 'precio_cambiado', precioActual: 9500 })
  })

  it('compara en centavos: 0,1 + 0,2 no es un cambio de precio', () => {
    expect(
      evaluarLinea(0.1 + 0.2, { ...ok, producto: { disponible: true, precio_base: '0.30' } })
        .estado,
    ).toBe('ok')
  })

  it('mientras carga no bloquea ni avisa', () => {
    expect(evaluarLinea(9500, { cargando: true, noExiste: false }).estado).toBe('verificando')
  })
})

describe('hayBloqueo', () => {
  it('solo bloquea un producto no disponible: un cambio de precio solo se avisa', () => {
    expect(
      hayBloqueo([{ estado: 'ok' }, { estado: 'precio_cambiado' }, { estado: 'verificando' }]),
    ).toBe(false)
    expect(hayBloqueo([{ estado: 'ok' }, { estado: 'no_disponible' }])).toBe(true)
  })
})
