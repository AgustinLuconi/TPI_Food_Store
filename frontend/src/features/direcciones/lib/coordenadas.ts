import type { Punto } from '../types'

/** Redondea a 6 decimales (~10 cm): suficiente para una dirección y evita números larguísimos en los campos. */
export const redondear = (n: number) => Math.round(n * 1e6) / 1e6

/** Lee un par de campos de texto como un punto válido; null si falta alguno o está fuera de rango. */
export function leerPunto(lat: string, lng: string): Punto | null {
  if (!lat.trim() || !lng.trim()) return null
  const la = Number(lat.replace(',', '.'))
  const lo = Number(lng.replace(',', '.'))
  if (Number.isNaN(la) || Number.isNaN(lo)) return null
  if (Math.abs(la) > 90 || Math.abs(lo) > 180) return null
  return { lat: la, lng: lo }
}

/** Un solo campo completo es un error: la API exige latitud y longitud juntas. */
export function coordenadasIncompletas(lat: string, lng: string): boolean {
  return !!lat.trim() !== !!lng.trim()
}
