import type { CategoriaOpcion } from '../types'

export interface NodoCategoria {
  id: number
  nombre: string
  children: NodoCategoria[]
}

/** Aplana el árbol a una lista con la ruta completa ("Comidas › Pizzas") para los combos. */
export function aplanarCategorias(arbol: NodoCategoria[], prefijo = ''): CategoriaOpcion[] {
  return arbol.flatMap((nodo) => {
    const ruta = prefijo ? `${prefijo} › ${nodo.nombre}` : nodo.nombre
    return [{ id: nodo.id, ruta }, ...aplanarCategorias(nodo.children, ruta)]
  })
}
