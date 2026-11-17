import { describe, expect, it } from 'vitest'
import type { CategoriaNodo } from '../types'
import { aplanarArbol, idsDelSubarbol } from './arbolCategorias'

const nodo = (id: number, nombre: string, children: CategoriaNodo[] = []): CategoriaNodo => ({
  id,
  parent_id: null,
  nombre,
  descripcion: null,
  children,
})

// Empanadas › Clásicas · Pizzas › Clásicas › Muzzarella · Pizzas › Especiales
const ARBOL = [
  nodo(1, 'Empanadas', [nodo(3, 'Clásicas')]),
  nodo(2, 'Pizzas', [nodo(4, 'Clásicas', [nodo(6, 'Muzzarella')]), nodo(5, 'Especiales')]),
]

describe('aplanarArbol', () => {
  it('lista cada padre antes que sus hijas, con la ruta completa', () => {
    expect(aplanarArbol(ARBOL)).toEqual([
      { id: 1, ruta: 'Empanadas' },
      { id: 3, ruta: 'Empanadas › Clásicas' },
      { id: 2, ruta: 'Pizzas' },
      { id: 4, ruta: 'Pizzas › Clásicas' },
      { id: 6, ruta: 'Pizzas › Clásicas › Muzzarella' },
      { id: 5, ruta: 'Pizzas › Especiales' },
    ])
  })

  it('distingue subcategorías con el mismo nombre', () => {
    const rutas = aplanarArbol(ARBOL).map((o) => o.ruta)
    expect(new Set(rutas).size).toBe(rutas.length)
  })
})

describe('idsDelSubarbol', () => {
  it('incluye la categoría y todas sus descendientes, a cualquier profundidad', () => {
    expect(idsDelSubarbol(ARBOL, 2)).toEqual(new Set([2, 4, 5, 6]))
  })

  it('una hoja solo se excluye a sí misma', () => {
    expect(idsDelSubarbol(ARBOL, 6)).toEqual(new Set([6]))
  })
})
