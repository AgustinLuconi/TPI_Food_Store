import { create } from 'zustand'

export type PasoCheckout = 'carrito' | 'entrega' | 'pago' | 'confirmacion'

interface PaymentState {
  /** Código de FormaPago elegido (EFECTIVO, TRANSFERENCIA, MERCADOPAGO). */
  formaPago: string | null
  paso: PasoCheckout
  /** Idempotency-Key del intento de pedido; ver ensureIdempotencyKey. */
  idempotencyKey: string | null
  setFormaPago: (codigo: string | null) => void
  setPaso: (paso: PasoCheckout) => void
  ensureIdempotencyKey: () => string
  resetIdempotencyKey: () => void
  reset: () => void
}

/** Forma de pago elegida y paso del checkout. No persiste. */
export const usePaymentStore = create<PaymentState>()((set, get) => ({
  formaPago: null,
  paso: 'carrito',
  idempotencyKey: null,
  setFormaPago: (formaPago) => set({ formaPago }),
  setPaso: (paso) => set({ paso }),
  /**
   * Se genera UNA vez al entrar a la confirmación: un doble clic o un reintento reutilizan la misma
   * clave y el backend devuelve el mismo pedido en lugar de crear otro.
   */
  ensureIdempotencyKey: () => {
    const existente = get().idempotencyKey
    if (existente) return existente
    const nueva = crypto.randomUUID()
    set({ idempotencyKey: nueva })
    return nueva
  },
  resetIdempotencyKey: () => set({ idempotencyKey: null }),
  reset: () => set({ formaPago: null, paso: 'carrito', idempotencyKey: null }),
}))
