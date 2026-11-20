import { describe, expect, it } from 'vitest'
import { describirDetalle, situacionDelPago } from './mercadopago'

describe('situacionDelPago (B.4)', () => {
  it('sin pago registrado', () => expect(situacionDelPago(null)).toBe('sin_pago'))
  it('approved confirma', () => expect(situacionDelPago('approved')).toBe('aprobado'))
  it('pending e in_process esperan la notificación', () => {
    expect(situacionDelPago('pending')).toBe('en_proceso')
    expect(situacionDelPago('in_process')).toBe('en_proceso')
  })
  it('rejected y cancelled permiten reintentar', () => {
    expect(situacionDelPago('rejected')).toBe('reintentable')
    expect(situacionDelPago('cancelled')).toBe('reintentable')
  })
})

describe('describirDetalle', () => {
  it('traduce los códigos conocidos', () =>
    expect(describirDetalle('cc_rejected_insufficient_amount')).toMatch(/fondos/))
  it('no muestra un código desconocido', () => {
    const t = describirDetalle('cc_rejected_algo_nuevo')
    expect(t).not.toMatch(/cc_rejected/)
    expect(t.length).toBeGreaterThan(10)
  })
  it('sin detalle da un texto genérico', () => expect(describirDetalle(null)).toMatch(/no pudo/))
})
