import { create } from 'zustand'

/** Solicitud de confirmación: reemplaza a window.confirm() (prohibido por la sección 11.4). */
export interface ConfirmRequest {
  titulo: string
  mensaje: string
  confirmLabel?: string
  tono?: 'danger' | 'primary'
  onConfirm: () => void | Promise<void>
}

interface UiState {
  sidebarOpen: boolean
  cartOpen: boolean
  confirm: ConfirmRequest | null
  toggleSidebar: () => void
  setSidebarOpen: (abierto: boolean) => void
  setCartOpen: (abierto: boolean) => void
  openConfirm: (solicitud: ConfirmRequest) => void
  closeConfirm: () => void
}

/** Sidebar, carrito abierto y modal de confirmación. No persiste. */
export const useUiStore = create<UiState>()((set) => ({
  sidebarOpen: false,
  cartOpen: false,
  confirm: null,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setCartOpen: (cartOpen) => set({ cartOpen }),
  openConfirm: (confirm) => set({ confirm }),
  closeConfirm: () => set({ confirm: null }),
}))
