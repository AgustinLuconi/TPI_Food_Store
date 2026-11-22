import { formatearCantidad } from '@/shared/lib/formato'
import type { MermaPorMotivo } from '../types'

/** "ROTURA" para los productos; "ROTURA (KG)" para los insumos, donde kilos y unidades no se suman (RN-10). */
export function etiquetaDeMerma(m: MermaPorMotivo): string {
  return m.unidad_medida ? `${m.motivo} (${m.unidad_medida})` : m.motivo
}

/** "2,5 KG" para un insumo; "3" para un producto, que se cuenta en unidades. */
export function cantidadConUnidad(cantidad: string | number, unidad?: string | null): string {
  const numero = formatearCantidad(cantidad)
  return unidad ? `${numero} ${unidad}` : numero
}

/** Qué insumos (o productos) componen el total y cuánto aportó cada uno: "Cebolla 3 KG · Harina 3 KG". */
export function textoDelDetalle(m: MermaPorMotivo): string {
  return (m.detalle ?? [])
    .map((d) => `${d.nombre} ${cantidadConUnidad(d.cantidad, m.unidad_medida)}`)
    .join(' · ')
}
