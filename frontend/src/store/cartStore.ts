import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/** Línea del carrito: producto, cantidad y exclusiones (ingredientes quitados, "sin cebolla"). */
export interface CartLine {
  lineId: string
  productoId: number
  nombre: string
  /** Precio referencial: se recalcula y se avisa antes de confirmar el pedido. */
  precio: number
  cantidad: number
  exclusiones: number[]
}

export type NewCartLine = Omit<CartLine, 'lineId' | 'cantidad'> & { cantidad?: number }

interface CartState {
  lines: CartLine[]
  addItem: (item: NewCartLine) => void
  setQuantity: (lineId: string, cantidad: number) => void
  removeItem: (lineId: string) => void
  clear: () => void
  itemCount: () => number
  subtotal: () => number
}

const claveDeExclusiones = (ids: number[]) => [...ids].sort((a, b) => a - b).join(',')

/**
 * El carrito no es una entidad de la base: vive aquí (persiste en localStorage) y se convierte en
 * Pedido en el checkout. No reserva stock; la validación autoritativa ocurre al crear el pedido.
 * Los componentes se suscriben por selector: useCartStore((s) => s.itemCount()).
 */
export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      lines: [],
      addItem: (item) =>
        set((state) => {
          const cantidad = item.cantidad ?? 1
          const clave = claveDeExclusiones(item.exclusiones)
          // El mismo producto con las mismas exclusiones suma cantidad; con otras, es otra línea.
          const existente = state.lines.find(
            (l) => l.productoId === item.productoId && claveDeExclusiones(l.exclusiones) === clave,
          )
          if (existente) {
            return {
              lines: state.lines.map((l) =>
                l.lineId === existente.lineId ? { ...l, cantidad: l.cantidad + cantidad } : l,
              ),
            }
          }
          const lineId = crypto.randomUUID()
          return { lines: [...state.lines, { ...item, lineId, cantidad }] }
        }),
      setQuantity: (lineId, cantidad) =>
        set((state) => ({
          lines:
            cantidad < 1
              ? state.lines.filter((l) => l.lineId !== lineId)
              : state.lines.map((l) => (l.lineId === lineId ? { ...l, cantidad } : l)),
        })),
      removeItem: (lineId) =>
        set((state) => ({ lines: state.lines.filter((l) => l.lineId !== lineId) })),
      clear: () => set({ lines: [] }),
      itemCount: () => get().lines.reduce((total, l) => total + l.cantidad, 0),
      subtotal: () => get().lines.reduce((total, l) => total + l.precio * l.cantidad, 0),
    }),
    {
      name: 'foodstore-cart',
      // Solo se persisten los datos, no las funciones.
      partialize: (state) => ({ lines: state.lines }),
    },
  ),
)
