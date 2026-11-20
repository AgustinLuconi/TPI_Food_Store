/** Textos para el cliente según el `mp_status_detail` de MercadoPago (Anexo B.4). */

const DETALLES: Record<string, string> = {
  accredited: 'El pago se acreditó.',
  cc_rejected_insufficient_amount: 'La tarjeta no tiene fondos suficientes.',
  cc_rejected_bad_filled_security_code: 'El código de seguridad es inválido.',
  cc_rejected_bad_filled_date: 'La fecha de vencimiento es inválida.',
  cc_rejected_bad_filled_card_number: 'El número de la tarjeta es inválido.',
  cc_rejected_bad_filled_other: 'Revisá los datos de la tarjeta.',
  cc_rejected_call_for_authorize: 'Tenés que autorizar el pago con tu banco.',
  cc_rejected_card_disabled: 'La tarjeta está inactiva. Activala o usá otra.',
  cc_rejected_duplicated_payment: 'Ya hiciste un pago por ese importe.',
  cc_rejected_high_risk: 'El pago fue rechazado por seguridad. Probá con otra tarjeta.',
  cc_rejected_max_attempts: 'Superaste el máximo de intentos. Probá con otra tarjeta.',
  cc_rejected_other_reason: 'La tarjeta rechazó el pago. Probá con otra.',
  pending_contingency: 'Estamos procesando el pago.',
  pending_review_manual: 'Estamos revisando el pago.',
}

/** Detalle legible; si MercadoPago manda un código nuevo, se muestra uno genérico y no el código crudo. */
export function describirDetalle(detalle: string | null | undefined): string {
  if (!detalle) return 'El pago no pudo completarse.'
  return DETALLES[detalle] ?? 'El pago no pudo completarse. Probá con otra tarjeta.'
}

export type SituacionDelPago = 'sin_pago' | 'aprobado' | 'en_proceso' | 'reintentable'

/** Qué puede hacer el cliente según el último pago registrado (B.4). */
export function situacionDelPago(mpStatus: string | null | undefined): SituacionDelPago {
  if (!mpStatus) return 'sin_pago'
  if (mpStatus === 'approved' || mpStatus === 'authorized') return 'aprobado'
  if (mpStatus === 'pending' || mpStatus === 'in_process' || mpStatus === 'in_mediation')
    return 'en_proceso'
  return 'reintentable' // rejected, cancelled…: puede intentar con otra tarjeta
}
