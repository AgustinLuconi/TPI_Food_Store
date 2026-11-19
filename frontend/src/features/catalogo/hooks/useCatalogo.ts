import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { categoriasCatalogoApi, ingredientesApi, productosApi } from '../api/catalogoApi'
import { aplanarCategorias } from '../lib/categorias'
import type { FiltrosProductos, IngredienteInput, LineaReceta, ProductoInput } from '../types'

export const catalogoKeys = {
  productos: ['productos'] as const,
  ingredientes: ['ingredientes'] as const,
}

export function useProductos(filtros: FiltrosProductos) {
  return useQuery({
    queryKey: [...catalogoKeys.productos, 'lista', filtros],
    queryFn: () => productosApi.list(filtros),
    placeholderData: keepPreviousData,
  })
}

export function useIngredientes(filtros: FiltrosProductos) {
  return useQuery({
    queryKey: [...catalogoKeys.ingredientes, 'lista', filtros],
    queryFn: () => ingredientesApi.list(filtros),
    placeholderData: keepPreviousData,
  })
}

/** Ingredientes activos para armar recetas. */
export function useOpcionesDeIngrediente() {
  return useQuery({
    queryKey: [...catalogoKeys.ingredientes, 'opciones'],
    queryFn: ingredientesApi.opciones,
  })
}

export function useOpcionesDeCategoria() {
  return useQuery({
    queryKey: ['categorias', 'arbol-catalogo'],
    queryFn: categoriasCatalogoApi.arbol,
    select: aplanarCategorias,
  })
}

/** Un cambio de producto o ingrediente invalida ambos listados (el stock y las recetas se cruzan). */
function useInvalidarCatalogo() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: catalogoKeys.productos }),
      queryClient.invalidateQueries({ queryKey: catalogoKeys.ingredientes }),
    ])
}

export function useGuardarProducto() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({
    mutationFn: async ({
      id,
      input,
      imagen,
    }: {
      id?: number
      input: ProductoInput
      imagen?: File | null
    }) => {
      const guardado =
        id === undefined ? await productosApi.create(input) : await productosApi.update(id, input)
      return imagen ? productosApi.uploadImagen(guardado.id, imagen) : guardado
    },
    onSuccess: invalidar,
  })
}

export function useAnularProducto() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({ mutationFn: productosApi.remove, onSuccess: invalidar })
}

export function useReactivarProducto() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({ mutationFn: productosApi.restore, onSuccess: invalidar })
}

export function useCambiarDisponibilidad() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({
    mutationFn: ({ id, disponible }: { id: number; disponible: boolean }) =>
      productosApi.setDisponible(id, disponible),
    onSuccess: invalidar,
  })
}

export function useGuardarIngrediente() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({
    mutationFn: ({ id, input }: { id?: number; input: IngredienteInput }) =>
      id === undefined ? ingredientesApi.create(input) : ingredientesApi.update(id, input),
    onSuccess: invalidar,
  })
}

export function useAnularIngrediente() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({ mutationFn: ingredientesApi.remove, onSuccess: invalidar })
}

export function useReactivarIngrediente() {
  const invalidar = useInvalidarCatalogo()
  return useMutation({ mutationFn: ingredientesApi.restore, onSuccess: invalidar })
}

export type TipoReceta = 'producto' | 'ingrediente'

/** Receta guardada de un producto (venta) o de un ingrediente elaborado. */
export function useReceta(tipo: TipoReceta, id: number) {
  return useQuery({
    queryKey: [tipo === 'producto' ? 'productos' : 'ingredientes', 'receta', id],
    queryFn: () => (tipo === 'producto' ? productosApi.receta(id) : ingredientesApi.receta(id)),
  })
}

export function useGuardarReceta(tipo: TipoReceta, id: number) {
  const invalidar = useInvalidarCatalogo()
  return useMutation({
    mutationFn: (lineas: LineaReceta[]) =>
      tipo === 'producto'
        ? productosApi.saveReceta(id, lineas)
        : ingredientesApi.saveReceta(id, lineas),
    onSuccess: invalidar,
  })
}

/** Detalle de un producto para la tienda. Un 404 es un resultado normal (producto dado de baja): sin reintentos. */
export function useProductoDetalle(id: number) {
  return useQuery({
    queryKey: [...catalogoKeys.productos, 'detalle', id],
    queryFn: () => productosApi.get(id),
    retry: false,
  })
}
