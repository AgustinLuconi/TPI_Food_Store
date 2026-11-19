import { api } from '@/shared/api/axiosInstance'

/** Lo mínimo del producto que el carrito necesita para revalidar una línea. */
export interface ProductoDelCarrito {
  id: number
  nombre: string
  precio_base: string
  disponible: boolean
}

export const carritoApi = {
  producto: (id: number) => api.get<ProductoDelCarrito>(`/productos/${id}`).then((r) => r.data),
}
