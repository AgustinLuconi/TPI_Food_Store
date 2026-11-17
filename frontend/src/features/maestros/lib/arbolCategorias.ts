import type { CategoriaNodo } from '../types'

export interface OpcionCategoria {
  id: number
  /** Ruta completa ("Pizzas › Clásicas"): distingue subcategorías con el mismo nombre. */
  ruta: string
}

/** Aplana el árbol en orden de recorrido (cada padre antes que sus hijas) con la ruta completa. */
export function aplanarArbol(nodos: CategoriaNodo[], prefijo = ''): OpcionCategoria[] {
  return nodos.flatMap((nodo) => {
    const ruta = prefijo ? `${prefijo} › ${nodo.nombre}` : nodo.nombre
    return [{ id: nodo.id, ruta }, ...aplanarArbol(nodo.children, ruta)]
  })
}

/** Ids de una categoría y de todas sus descendientes: ninguna puede ser su nuevo padre (ciclo). */
export function idsDelSubarbol(nodos: CategoriaNodo[], id: number): Set<number> {
  const raiz = buscar(nodos, id)
  const ids = new Set<number>([id])
  const pendientes = raiz ? [...raiz.children] : []
  for (let nodo = pendientes.pop(); nodo; nodo = pendientes.pop()) {
    ids.add(nodo.id)
    pendientes.push(...nodo.children)
  }
  return ids
}

function buscar(nodos: CategoriaNodo[], id: number): CategoriaNodo | undefined {
  for (const nodo of nodos) {
    if (nodo.id === id) return nodo
    const encontrado = buscar(nodo.children, id)
    if (encontrado) return encontrado
  }
  return undefined
}
