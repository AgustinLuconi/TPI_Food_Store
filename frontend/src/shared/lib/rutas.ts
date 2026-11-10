import { ROLES_PERSONAL, type Rol } from '@/shared/types/auth'

export const RUTAS = {
  inicio: '/',
  login: '/login',
  registro: '/registro',
  perfil: '/perfil',
  admin: '/admin',
  adminCategorias: '/admin/categorias',
  adminUsuarios: '/admin/usuarios',
  exito: '/success',
  error: '/error',
  noAutorizado: '/unauthorized',
} as const

/** El personal entra al panel; el cliente, a la tienda. */
export function homePorRoles(roles: readonly Rol[]): string {
  return roles.some((r) => ROLES_PERSONAL.includes(r)) ? RUTAS.admin : RUTAS.inicio
}
