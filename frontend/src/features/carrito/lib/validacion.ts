/**
 * Casos de la sección 11.2: el precio y la disponibilidad del carrito son referenciales; antes de confirmar se
 * comparan con el catálogo actual. Funciones puras, fáciles de probar.
 */

export type EstadoLinea = 'verificando' | 'ok' | 'no_disponible' | 'precio_cambiado'

export interface ConsultaDeProducto {
  cargando: boolean
  /** El producto ya no existe o está dado de baja (404). */
  noExiste: boolean
  producto?: { disponible: boolean; precio_base: string }
}

export interface ResultadoDeLinea {
  estado: EstadoLinea
  /** Precio vigente en el catálogo, si se pudo consultar. */
  precioActual?: number
}

export function evaluarLinea(
  precioDelCarrito: number,
  consulta: ConsultaDeProducto,
): ResultadoDeLinea {
  if (consulta.noExiste) return { estado: 'no_disponible' }
  if (consulta.cargando || !consulta.producto) return { estado: 'verificando' }
  const precioActual = Number(consulta.producto.precio_base)
  if (!consulta.producto.disponible) return { estado: 'no_disponible', precioActual }
  // Se compara en centavos: evita falsos cambios por redondeo de coma flotante.
  if (Math.round(precioActual * 100) !== Math.round(precioDelCarrito * 100))
    return { estado: 'precio_cambiado', precioActual }
  return { estado: 'ok', precioActual }
}

/** El checkout se bloquea mientras haya una línea de un producto dado de baja o no disponible. */
export function hayBloqueo(resultados: ResultadoDeLinea[]): boolean {
  return resultados.some((r) => r.estado === 'no_disponible')
}
