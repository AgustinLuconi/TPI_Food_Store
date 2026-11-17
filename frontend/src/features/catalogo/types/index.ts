export interface CategoriaDelProducto {
  id: number
  nombre: string
  es_principal: boolean
}

/** Fila del listado de productos. El stock solo lo informa la API al ADMIN y al STOCK. */
export interface ProductoItem {
  id: number
  nombre: string
  descripcion: string | null
  imagen_url: string | null
  precio_base: string
  disponible: boolean
  stock_minimo: number
  categorias: CategoriaDelProducto[]
  stock_real: string | null
  stock_disponible: string | null
  deleted_at: string | null
}

export interface ProductoInput {
  nombre: string
  descripcion: string | null
  precio_base: string
  stock_minimo: number
  categoria_ids: number[]
  categoria_principal_id: number | null
}

export interface Ingrediente {
  id: number
  nombre: string
  es_alergeno: boolean
  es_elaborado: boolean
  stock_minimo: number
  stock_real: string | null
  stock_disponible: string | null
  deleted_at: string | null
}

export interface IngredienteInput {
  nombre: string
  es_alergeno: boolean
  es_elaborado: boolean
  stock_minimo: number
}

/** Una línea de receta, tanto de venta (producto) como de un elaborado: lo común para editarla. */
export interface LineaReceta {
  ingrediente_id: number
  nombre: string
  cantidad_requerida: string
  unidad_medida: string
  /** Solo la receta de venta distingue ingredientes removibles ("sin cebolla"). */
  es_removible: boolean
}

export interface CategoriaOpcion {
  id: number
  ruta: string
}

export interface FiltrosProductos {
  search: string
  estado: 'activos' | 'inactivos' | 'todos'
  page: number
  size: number
  /** Categoría (incluye sus subcategorías). */
  grupo?: string
  orden?: { campo: string; sentido: 'asc' | 'desc' }
}

/** Valores del combo de tipo de ingrediente. */
export const TIPO_INGREDIENTE = { alergeno: 'alergeno', elaborado: 'elaborado' } as const

export const UNIDADES_SUGERIDAS = ['KG', 'G', 'L', 'ML', 'UN'] as const
