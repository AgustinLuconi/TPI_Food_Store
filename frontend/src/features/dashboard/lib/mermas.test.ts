import { describe, expect, it } from 'vitest'
import type { MermaPorMotivo } from '../types'
import { cantidadConUnidad, etiquetaDeMerma, textoDelDetalle } from './mermas'

const rotura: MermaPorMotivo = {
  motivo: 'ROTURA',
  unidad_medida: 'KG',
  cantidad: '6.000',
  movimientos: 3,
  detalle: [
    { ingrediente_id: 4, nombre: 'Cebolla', cantidad: '3.000', movimientos: 1 },
    { ingrediente_id: 1, nombre: 'Harina', cantidad: '2.500', movimientos: 2 },
  ],
}

describe('mermas del panel', () => {
  it('distingue la unidad en el nombre de la fila de un insumo', () => {
    expect(etiquetaDeMerma(rotura)).toBe('ROTURA (KG)')
    expect(etiquetaDeMerma({ motivo: 'ROTURA', cantidad: '2', movimientos: 1 })).toBe('ROTURA')
    expect(etiquetaDeMerma({ ...rotura, unidad_medida: null })).toBe('ROTURA')
  })

  it('muestra la cantidad con su unidad solo si la hay', () => {
    expect(cantidadConUnidad('2.500', 'KG')).toBe('2,5 KG')
    expect(cantidadConUnidad('3.000', 'UN')).toBe('3 UN')
    expect(cantidadConUnidad('4.000')).toBe('4')
  })

  it('lista cuánto aportó cada insumo', () => {
    expect(textoDelDetalle(rotura)).toBe('Cebolla 3 KG · Harina 2,5 KG')
    expect(textoDelDetalle({ motivo: 'ROTURA', cantidad: '2', movimientos: 1 })).toBe('')
  })
})
