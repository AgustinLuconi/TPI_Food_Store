import { describe, expect, it } from 'vitest'
import { aplanarCategorias } from './categorias'

describe('aplanarCategorias', () => {
  it('arma la ruta completa de cada categoría', () => {
    const arbol = [
      { id: 1, nombre: 'Comidas', children: [{ id: 2, nombre: 'Pizzas', children: [] }] },
      { id: 3, nombre: 'Bebidas', children: [] },
    ]
    expect(aplanarCategorias(arbol)).toEqual([
      { id: 1, ruta: 'Comidas' },
      { id: 2, ruta: 'Comidas › Pizzas' },
      { id: 3, ruta: 'Bebidas' },
    ])
  })
})
