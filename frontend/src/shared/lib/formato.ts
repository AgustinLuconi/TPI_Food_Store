import { API_URL } from '@/shared/api/axiosInstance'

const MONEDA = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' })
const CANTIDAD = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 3 })

/** "9500.00" → "$ 9.500,00". Los montos viajan como texto para no perder decimales. */
export function formatearDinero(valor: string | number): string {
  return MONEDA.format(Number(valor)).replace(/\s/g, ' ')
}

/** "0.300" → "0,3"; "10.000" → "10". Hasta 3 decimales, sin ceros de relleno. */
export function formatearCantidad(valor: string | number): string {
  return CANTIDAD.format(Number(valor))
}

/**
 * Las imágenes se guardan como ruta relativa (/media/productos/<uuid>.jpg). Detrás de Nginx cuelgan del mismo
 * origen que la SPA; en desarrollo el backend corre en otro puerto, así que se antepone su origen.
 */
export function urlDeMedia(ruta: string | null | undefined): string | null {
  if (!ruta) return null
  if (/^https?:\/\//.test(ruta)) return ruta
  return new URL(ruta, new URL(API_URL, window.location.origin).origin).toString()
}

/** "2026-12-25T00:00:00Z" → "25/12/2026" (el día calendario, sin corrimientos de zona horaria). */
export function formatearFecha(iso: string, conHora = false): string {
  const d = new Date(iso)
  return conHora
    ? d.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })
    : d.toLocaleDateString('es-AR')
}

/** Cantidad de decimales de un texto numérico ("0.300" → 3). */
export function decimalesDe(valor: string): number {
  const [, fraccion = ''] = valor.trim().split('.')
  return fraccion.length
}
