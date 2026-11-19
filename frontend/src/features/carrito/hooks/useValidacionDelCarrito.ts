import { useQueries } from '@tanstack/react-query'
import { toApiError } from '@/shared/api/errors'
import { useCartStore } from '@/store/cartStore'
import { carritoApi } from '../api/carritoApi'
import { evaluarLinea, hayBloqueo, type ResultadoDeLinea } from '../lib/validacion'

/**
 * Revalida cada línea del carrito contra el catálogo actual (precio y disponibilidad). El carrito no reserva
 * stock: la validación autoritativa ocurre al crear el pedido (409 si falta).
 */
export function useValidacionDelCarrito(activa = true) {
  const lines = useCartStore((s) => s.lines)
  const productoIds = [...new Set(lines.map((l) => l.productoId))]

  const consultas = useQueries({
    queries: productoIds.map((id) => ({
      queryKey: ['carrito', 'producto', id],
      queryFn: () => carritoApi.producto(id),
      enabled: activa,
      staleTime: 15_000,
      retry: false, // un 404 (producto dado de baja) es una respuesta, no un fallo a reintentar
    })),
  })
  const porProducto = new Map(productoIds.map((id, i) => [id, consultas[i]]))

  const resultados: Record<string, ResultadoDeLinea> = {}
  for (const l of lines) {
    const q = porProducto.get(l.productoId)
    resultados[l.lineId] = evaluarLinea(l.precio, {
      cargando: q?.isLoading ?? true,
      noExiste: q?.isError === true && toApiError(q.error).status === 404,
      producto: q?.data,
    })
  }

  const lista = Object.values(resultados)
  const subtotalActual = lines.reduce(
    (t, l) => t + (resultados[l.lineId]?.precioActual ?? l.precio) * l.cantidad,
    0,
  )
  const preciosCambiados = Object.fromEntries(
    lines
      .filter((l) => resultados[l.lineId]?.estado === 'precio_cambiado')
      .map((l) => [l.productoId, resultados[l.lineId].precioActual as number]),
  )

  return {
    resultados,
    bloqueado: hayBloqueo(lista),
    hayPreciosCambiados: Object.keys(preciosCambiados).length > 0,
    preciosCambiados,
    subtotalActual,
  }
}
