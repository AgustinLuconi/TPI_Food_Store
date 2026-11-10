import { create } from 'zustand'
import type { Rol, Usuario } from '@/shared/types/auth'

/** checking: verificación inicial en curso (GET /auth/me al cargar la app). */
export type AuthStatus = 'checking' | 'authenticated' | 'anonymous'

interface AuthState {
  usuario: Usuario | null
  isAuthenticated: boolean
  status: AuthStatus
  setUsuario: (usuario: Usuario) => void
  setAnonymous: () => void
  clear: () => void
  hasRole: (...roles: Rol[]) => boolean
}

/**
 * Sesión del usuario. NO persiste y NO guarda el token (vive en la cookie HttpOnly):
 * GET /auth/me reconstruye la sesión al recargar. Los guards solo ocultan opciones;
 * la autorización real es la del backend.
 */
export const useAuthStore = create<AuthState>()((set, get) => ({
  usuario: null,
  isAuthenticated: false,
  status: 'checking',
  setUsuario: (usuario) => set({ usuario, isAuthenticated: true, status: 'authenticated' }),
  setAnonymous: () => set({ usuario: null, isAuthenticated: false, status: 'anonymous' }),
  clear: () => set({ usuario: null, isAuthenticated: false, status: 'anonymous' }),
  hasRole: (...roles) => {
    const usuario = get().usuario
    return usuario !== null && usuario.roles.some((rol) => roles.includes(rol))
  },
}))
