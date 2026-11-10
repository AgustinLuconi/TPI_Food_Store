import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Usuario } from '@/shared/types/auth'
import { useAuthStore } from './authStore'
import { useCartStore } from './cartStore'
import { usePaymentStore } from './paymentStore'
import { useUiStore } from './uiStore'

const pizza = {
  productoId: 1,
  nombre: 'Pizza muzzarella',
  precio: 9500,
  exclusiones: [] as number[],
}

describe('cartStore', () => {
  beforeEach(() => {
    localStorage.clear()
    useCartStore.getState().clear()
  })

  it('el mismo producto con las mismas exclusiones suma cantidad; con otras exclusiones es otra línea', () => {
    const { addItem } = useCartStore.getState()
    addItem(pizza)
    addItem(pizza)
    addItem({ ...pizza, exclusiones: [3, 2] })
    addItem({ ...pizza, exclusiones: [2, 3] }) // mismo conjunto en otro orden: misma línea
    const { lines } = useCartStore.getState()
    expect(lines).toHaveLength(2)
    expect(lines[0]?.cantidad).toBe(2)
    expect(lines[1]?.cantidad).toBe(2)
  })

  it('calcula itemCount y subtotal; una cantidad menor a 1 quita la línea', () => {
    const { addItem } = useCartStore.getState()
    addItem({ ...pizza, cantidad: 2 })
    addItem({ productoId: 2, nombre: 'Empanada', precio: 1800, exclusiones: [] })
    expect(useCartStore.getState().itemCount()).toBe(3)
    expect(useCartStore.getState().subtotal()).toBe(2 * 9500 + 1800)

    const lineId = useCartStore.getState().lines[1]?.lineId ?? ''
    useCartStore.getState().setQuantity(lineId, 0)
    expect(useCartStore.getState().lines).toHaveLength(1)
  })

  it('persiste en localStorage solo los datos (sin funciones)', () => {
    useCartStore.getState().addItem(pizza)
    const guardado = JSON.parse(localStorage.getItem('foodstore-cart') ?? '{}') as {
      state: Record<string, unknown>
    }
    expect(Object.keys(guardado.state)).toEqual(['lines'])
  })

  it('clear vacía el carrito (se usa al cerrar sesión)', () => {
    useCartStore.getState().addItem(pizza)
    useCartStore.getState().clear()
    expect(useCartStore.getState().itemCount()).toBe(0)
  })
})

describe('paymentStore', () => {
  beforeEach(() => usePaymentStore.getState().reset())

  it('la Idempotency-Key se genera UNA vez y se reutiliza (un doble clic no duplica el pedido)', () => {
    const primera = usePaymentStore.getState().ensureIdempotencyKey()
    const segunda = usePaymentStore.getState().ensureIdempotencyKey()
    expect(primera).toBe(segunda)
    expect(primera).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('un nuevo intento (resetIdempotencyKey) obtiene una clave distinta', () => {
    const primera = usePaymentStore.getState().ensureIdempotencyKey()
    usePaymentStore.getState().resetIdempotencyKey()
    expect(usePaymentStore.getState().ensureIdempotencyKey()).not.toBe(primera)
  })

  it('no persiste: no escribe nada en localStorage', () => {
    localStorage.clear()
    usePaymentStore.getState().setFormaPago('EFECTIVO')
    expect(localStorage.length).toBe(0)
  })
})

describe('authStore', () => {
  const usuario: Usuario = {
    id: 1,
    nombre: 'Ana',
    apellido: 'Pérez',
    email: 'ana@test.com',
    telefono: null,
    disabled: false,
    roles: ['STOCK', 'CLIENT'],
    created_at: '2026-01-01T00:00:00Z',
    deleted_at: null,
  }

  beforeEach(() => {
    localStorage.clear()
    useAuthStore.getState().clear()
  })

  it('setUsuario autentica y hasRole consulta los roles', () => {
    useAuthStore.getState().setUsuario(usuario)
    const s = useAuthStore.getState()
    expect(s.isAuthenticated).toBe(true)
    expect(s.status).toBe('authenticated')
    expect(s.hasRole('STOCK')).toBe(true)
    expect(s.hasRole('ADMIN', 'PEDIDOS')).toBe(false)
  })

  it('clear deja la sesión anónima, y nunca guarda el token ni persiste el usuario', () => {
    useAuthStore.getState().setUsuario(usuario)
    expect(localStorage.length).toBe(0) // la sesión se reconstruye con GET /auth/me
    useAuthStore.getState().clear()
    expect(useAuthStore.getState().usuario).toBeNull()
    expect(useAuthStore.getState().status).toBe('anonymous')
    expect(useAuthStore.getState().hasRole('CLIENT')).toBe(false)
  })
})

describe('uiStore', () => {
  it('abre y cierra el modal de confirmación (reemplaza a window.confirm)', async () => {
    const onConfirm = vi.fn()
    useUiStore.getState().openConfirm({ titulo: 'Anular', mensaje: '¿Seguro?', onConfirm })
    const solicitud = useUiStore.getState().confirm
    expect(solicitud?.titulo).toBe('Anular')
    await solicitud?.onConfirm()
    expect(onConfirm).toHaveBeenCalledOnce()
    useUiStore.getState().closeConfirm()
    expect(useUiStore.getState().confirm).toBeNull()
  })

  it('no persiste', () => {
    localStorage.clear()
    useUiStore.getState().setSidebarOpen(true)
    expect(localStorage.length).toBe(0)
  })
})
