import { api } from '@/shared/api/axiosInstance'
import type { Paginated } from '@/shared/types/common'
import type { NodoCategoria } from '../lib/categorias'
import {
  TIPO_INGREDIENTE,
  type FiltrosProductos,
  type Ingrediente,
  type IngredienteInput,
  type LineaReceta,
  type ProductoInput,
  type ProductoDetalle,
  type ProductoItem,
} from '../types'

interface FiltrosIngredientes extends Omit<FiltrosProductos, 'grupo'> {
  /** "alergeno" o "elaborado" (combo de agrupación). */
  grupo?: string
}

/** El backend nombra distinto a los ingredientes del producto (ingrediente_id) y de un elaborado (componente_id). */
interface LineaProductoApi {
  ingrediente_id: number
  nombre: string
  cantidad_requerida: string
  unidad_medida: string
  es_removible: boolean
}
interface LineaElaboradoApi {
  componente_id: number
  nombre: string
  cantidad_requerida: string
  unidad_medida: string
}

export const productosApi = {
  list: ({ search, estado, page, size, grupo, orden }: FiltrosProductos) =>
    api
      .get<Paginated<ProductoItem>>('/productos', {
        params: {
          search: search || undefined,
          estado,
          page,
          size,
          categoria_id: grupo ? Number(grupo) : undefined,
          orden: orden?.campo,
          sentido: orden?.sentido,
        },
      })
      .then((r) => r.data),

  /** Detalle con categorías, receta y alérgenos (público). */
  get: (id: number) => api.get<ProductoDetalle>(`/productos/${id}`).then((r) => r.data),

  create: (input: ProductoInput) => api.post<ProductoItem>('/productos', input).then((r) => r.data),

  update: (id: number, input: ProductoInput) =>
    api.put<ProductoItem>(`/productos/${id}`, input).then((r) => r.data),

  remove: (id: number) => api.delete(`/productos/${id}`).then(() => undefined),

  restore: (id: number) =>
    api.patch<ProductoItem>(`/productos/${id}/reactivar`).then((r) => r.data),

  setDisponible: (id: number, disponible: boolean) =>
    api.patch<ProductoItem>(`/productos/${id}/disponibilidad`, { disponible }).then((r) => r.data),

  /** El tipo se valida en el servidor por el contenido del archivo, no por su extensión. */
  uploadImagen: (id: number, archivo: File) => {
    const datos = new FormData()
    datos.append('archivo', archivo)
    return api.post<ProductoItem>(`/productos/${id}/imagen`, datos).then((r) => r.data)
  },

  receta: (id: number): Promise<LineaReceta[]> =>
    api.get<LineaProductoApi[]>(`/productos/${id}/ingredientes`).then((r) => r.data),

  saveReceta: (id: number, lineas: LineaReceta[]): Promise<LineaReceta[]> =>
    api
      .put<LineaProductoApi[]>(`/productos/${id}/ingredientes`, {
        items: lineas.map((l) => ({
          ingrediente_id: l.ingrediente_id,
          cantidad_requerida: l.cantidad_requerida,
          unidad_medida: l.unidad_medida,
          es_removible: l.es_removible,
        })),
      })
      .then((r) => r.data),
}

export const ingredientesApi = {
  list: ({ search, estado, page, size, grupo, orden }: FiltrosIngredientes) =>
    api
      .get<Paginated<Ingrediente>>('/ingredientes', {
        params: {
          search: search || undefined,
          estado,
          page,
          size,
          es_alergeno: grupo === TIPO_INGREDIENTE.alergeno || undefined,
          es_elaborado: grupo === TIPO_INGREDIENTE.elaborado || undefined,
          orden: orden?.campo,
          sentido: orden?.sentido,
        },
      })
      .then((r) => r.data),

  /** Todos los activos (hasta 100) para los combos de las recetas. */
  opciones: () =>
    api
      .get<Paginated<Ingrediente>>('/ingredientes', { params: { estado: 'activos', size: 100 } })
      .then((r) => r.data.items),

  create: (input: IngredienteInput) =>
    api.post<Ingrediente>('/ingredientes', input).then((r) => r.data),

  update: (id: number, input: IngredienteInput) =>
    api.put<Ingrediente>(`/ingredientes/${id}`, input).then((r) => r.data),

  remove: (id: number) => api.delete(`/ingredientes/${id}`).then(() => undefined),

  restore: (id: number) =>
    api.patch<Ingrediente>(`/ingredientes/${id}/reactivar`).then((r) => r.data),

  receta: (id: number): Promise<LineaReceta[]> =>
    api.get<LineaElaboradoApi[]>(`/ingredientes/${id}/receta`).then((r) =>
      r.data.map((l) => ({
        ingrediente_id: l.componente_id,
        nombre: l.nombre,
        cantidad_requerida: l.cantidad_requerida,
        unidad_medida: l.unidad_medida,
        es_removible: false,
      })),
    ),

  saveReceta: (id: number, lineas: LineaReceta[]) =>
    api
      .put(`/ingredientes/${id}/receta`, {
        items: lineas.map((l) => ({
          componente_id: l.ingrediente_id,
          cantidad_requerida: l.cantidad_requerida,
          unidad_medida: l.unidad_medida,
        })),
      })
      .then(() => undefined),
}

export const categoriasCatalogoApi = {
  /** Árbol público de categorías activas. */
  arbol: () => api.get<NodoCategoria[]>('/categorias').then((r) => r.data),
}
